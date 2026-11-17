"""Transport — CDP "browser oracle".

WHY THIS EXISTS (revised 2026-10-16 against audit/antibot_probe.md)
--------------------------------------------------------------------
Ozon's entrypoint is challenge-gated for a **cold** client. The correct
classification is Hybrid / challenge-handling Method 4, not "tier 6,
non-portable clearance".

What that probe measured, with the browser and curl_cffi on the same
egress IP:

    curl_cffi impersonate=chrome146, Chrome headers, no cookies
        -> 403 + `ozon-antibot: 1` + a JSON challenge descriptor (variant B)
    the same request plus the 9 CDP cookies
        -> 200, same payload class as an in-page fetch (variant C)

B and C differed only in the cookie jar. Cookie replay DOES work on the
same IP. The earlier conclusion in this docstring — that the clearance is
bound to the browser's TLS session, and that replaying the jar still
returned 403 — was wrong. So was the sentence claiming a curl_cffi retry
on the same IP immediately after a browser solve was still 403 with a
brand-new incidentId.

Not retested that day, so not overturned and not claimed here:

    requests with no jar                          -> 403 (older note)
    curl_cffi + RU/BY residential IP, no jar      -> 403 (older note)
    plain `requests` + the same jar               -> untested
    the jar from a different IP                   -> untested
    which subset of the 9 cookies is sufficient   -> untested
    operational TTL (declared Expires is ~1 year) -> untested

`document.cookie` is the wrong handoff: only `__Secure-ab-group` and
`xcid` are JS-visible. `abt_data` is HttpOnly and, on this Chrome profile,
partitioned to the Ozon top-level site. `CookieJarTransport` in
`cookiejar.py` reads the jar via CDP `Network.getAllCookies` and replays
it with `curl_cffi`. A cold curl_cffi client still gets 403.

This module stays the in-browser transport and the mint source:

  - requests are page-context `fetch()` over CDP,
  - cookies stay inside Chrome (never serialised here),
  - the TLS fingerprint is Chrome's own.

It is the default `OzonClient` transport, and the fallback when the
optional `curl_cffi` extra is not installed.

Challenge discipline (both transports share :class:`ChallengeGuard`):

  - a 403 / ``ozon-antibot`` / incident JSON / masked-HTML incident is a
    challenge even when the status is not 403,
  - 403 and 429 are never retried in a loop,
  - the browser path does not re-fetch a challenge (that is hammering);
    it cools the session down and further calls fail without a send,
  - identical successful GETs are reused from a short in-memory cache so a
    later call does not re-fetch a page this process already holds.

``warmup`` lands on home first. A deep URL is visited only after that
entry, optionally after a search. See ``ANTI-DETECTION.md``.
"""
from __future__ import annotations

import json
import random
import re
import threading
import time
import urllib.request
from typing import Any
from urllib.parse import quote, urlsplit

from .exceptions import (
    AntibotBlocked,
    AuthRequired,
    NotFound,
    OzonError,
    RateLimited,
    TransportError,
)
from .throttle import TokenBucket

DEFAULT_CDP = "http://127.0.0.1:9222"

# The antibot's 403 body is masked HTML, not JSON, so the incident id has to
# be pulled out of the markup when the JSON parse fails. The 2026-10-16 probe
# also saw a JSON descriptor (incidentId, challengeURL, ...) with status 403.
# Both shapes count.
_INCIDENT_PATTERNS = (
    re.compile(r'"incidentId"\s*:\s*"([^"]+)"'),
    re.compile(r'incidentId[=:]"?([A-Za-z0-9_-]{8,})'),
    re.compile(r'data-incident(?:-id)?="([^"]+)"'),
    re.compile(r"\bfab_chlg_[A-Za-z0-9_]+"),
)

# Cookie values must never surface in an error string. Same idea as
# cookiejar._LEAK; this copy covers HTTP error text raised from this module.
_LEAK = re.compile(
    r"(?i)(cookie|set-cookie|abt_data|xcid|cookie_settings|__secure-[a-z0-9_-]+)"
    r"\s*[:=]\s*\S+"
)


def redact_secrets(text: str, limit: int = 300) -> str:
    """Strip cookie assignments from an error string. Names may remain."""
    return _LEAK.sub(r"\1=<redacted>", text or "")[:limit]


def _incident_id(body: str, headers: dict | None = None) -> str | None:
    """Best-effort incident id from a challenge body (JSON *or* masked HTML)."""
    try:
        d = json.loads(body)
    except Exception:
        d = None
    if isinstance(d, dict):
        for k in ("incidentId", "incident_id"):
            if d.get(k):
                return str(d[k])
    if isinstance(body, str):
        for rx in _INCIDENT_PATTERNS:
            m = rx.search(body)
            if m:
                return m.group(1) if m.lastindex else m.group(0)
    for k, v in (headers or {}).items():
        if "incident" in str(k).lower() and v:
            return str(v)
    return None


def _header(headers: dict | None, name: str) -> str:
    for key, value in (headers or {}).items():
        if str(key).lower() == name:
            return str(value)
    return ""


def is_antibot_challenge(resp: "OracleResponse") -> bool:
    """True for the Ozon challenge, including a non-403 masked HTML body.

    A normal 200 JSON envelope is not a challenge, even if some widget
    string happens to contain the letters "incident". HTML (or any
    non-2xx) must actually carry an incident id or ``ozon-antibot``.
    """
    headers = resp.headers or {}
    if _header(headers, "ozon-antibot").strip() not in ("", "0"):
        return True
    body = resp.text or ""
    stripped = body.lstrip()
    data = None
    if stripped.startswith("{") or stripped.startswith("["):
        try:
            data = json.loads(body)
        except Exception:
            data = None
    if isinstance(data, dict) and (
        data.get("incidentId") or data.get("incident_id") or data.get("challengeURL")
    ):
        return True
    ctype = _header(headers, "content-type").lower()
    htmlish = "html" in ctype or stripped.startswith("<")
    if resp.status == 403 or htmlish:
        if _incident_id(body, headers):
            return True
    return False


class ChallengeGuard:
    """Backoff budget for challenges. Never a retry loop.

    Cookie-jar mode may ask for one retry (``may_retry=True``) after a
    fresh jar read. A second consecutive challenge, a third challenge in
    the life of this guard, any challenge on the browser path
    (``may_retry=False``), or a 429, stops the session. Later ``refusal``
    raises without sending.
    """

    COOLDOWN_SEC = 900.0
    MAX_TOTAL = 3

    def __init__(self) -> None:
        self.total = 0
        self.consecutive = 0
        self.stopped = False
        self.cooldown_until = 0.0
        self.reason = ""
        self.incident_id: str | None = None
        self.retry_after = None

    def refusal(self) -> BaseException | None:
        if not self.stopped and time.monotonic() >= self.cooldown_until:
            return None
        if self.reason == "rate":
            return RateLimited(self.retry_after)
        return AntibotBlocked(self.incident_id, None, None)

    def _stop(self, seconds: float, reason: str) -> None:
        self.stopped = True
        self.reason = reason
        self.cooldown_until = time.monotonic() + max(1.0, seconds)

    def on_challenge(self, incident: str | None, *, may_retry: bool) -> bool:
        """Count one challenge. True only when the caller may send one retry."""
        self.total += 1
        self.consecutive += 1
        if incident:
            self.incident_id = incident
        self.reason = "challenge"
        if (not may_retry) or self.consecutive >= 2 or self.total >= self.MAX_TOTAL:
            self._stop(self.COOLDOWN_SEC, "challenge")
            return False
        return True

    def backoff_seconds(self) -> float:
        """Exponential pause before the single allowed retry. Capped, jittered."""
        step = max(0, self.consecutive - 1)
        return min(30.0, 2.0 * (2 ** step)) * random.uniform(0.75, 1.25)

    def on_rate_limit(self, retry_after) -> None:
        seconds = 60.0
        if retry_after is not None:
            try:
                seconds = max(1.0, float(retry_after))
            except (TypeError, ValueError):
                seconds = 60.0
        self.retry_after = retry_after
        self._stop(max(seconds, 60.0), "rate")

    def on_success(self) -> None:
        if not self.stopped:
            self.consecutive = 0


class ResponseCache:
    """Short TTL for successful GETs. Not a disk cache. No cookies stored.

    The entrypoint repeats itself: ``questions(sku)`` re-fetches the product
    document ``product(sku)`` just loaded. Serving that from memory is one
    less request on the only IP we have. Challenges and non-200s are not
    cached. TTL is short so a dead jar is not masked for long.
    """

    def __init__(self, ttl: float = 90.0, limit: int = 24):
        self.ttl = float(ttl)
        self.limit = int(limit)
        self._lock = threading.Lock()
        self._items: dict[str, tuple[float, dict]] = {}

    def get(self, method: str, url: str) -> "OracleResponse | None":
        if method.upper() != "GET" or self.ttl <= 0:
            return None
        now = time.monotonic()
        with self._lock:
            item = self._items.get(url)
            if not item:
                return None
            ts, payload = item
            if now - ts > self.ttl:
                self._items.pop(url, None)
                return None
            snapshot = dict(payload)
        return OracleResponse(snapshot)

    def put(self, method: str, url: str, resp: "OracleResponse") -> None:
        if method.upper() != "GET" or self.ttl <= 0:
            return
        if not (200 <= resp.status < 300) or is_antibot_challenge(resp):
            return
        payload = {
            "status": resp.status,
            "body": resp.text,
            "headers": dict(resp.headers),
            "url": resp.url,
        }
        with self._lock:
            if len(self._items) >= self.limit:
                oldest = min(self._items, key=lambda key: self._items[key][0])
                self._items.pop(oldest, None)
            self._items[url] = (time.monotonic(), payload)


def _http_json(url: str, timeout: float = 10.0):
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return json.load(r)
    except urllib.error.URLError as e:
        raise TransportError(
            f"cannot reach Chrome DevTools at {url}: {e}. "
            "Start Chrome with --remote-debugging-port=9222 first."
        ) from e


def _origin_of(url: str) -> str:
    parts = urlsplit(url)
    if parts.scheme and parts.netloc:
        return f"{parts.scheme}://{parts.netloc}"
    return "https://ozon.by"


def _same_document(a: str, b: str) -> bool:
    """True when both URLs are the site root (home), ignoring query noise."""
    pa = urlsplit(a).path or "/"
    pb = urlsplit(b).path or "/"
    return pa in ("", "/") and pb in ("", "/")


def _wire_target(url: str) -> str:
    """Document path or API path for logs. Query tokens are not included."""
    parts = urlsplit(url)
    qs = {}
    if parts.query:
        from urllib.parse import parse_qs
        qs = parse_qs(parts.query)
    if qs.get("url"):
        doc = qs["url"][0]
        return (doc.split("?", 1)[0] or "/")[:180]
    return (parts.path or "/")[:180]


class BrowserOracle:
    """Issues HTTP requests from inside a live Chrome page via CDP."""

    def __init__(self, cdp: str = DEFAULT_CDP, timeout: float = 45.0,
                 throttle: TokenBucket | None = None):
        self.cdp = cdp.rstrip("/")
        self.timeout = timeout
        self.throttle = throttle or TokenBucket(rate=0.5, burst=1.0)
        self._ws = None
        self._sess: str | None = None
        self._id = 0
        self._guard = ChallengeGuard()
        self._cache = ResponseCache()
        self.cache_hits = 0
        # Wire calls only: method, document-or-path, status. No headers, no cookies.
        self.wire_log: list[dict] = []

    # ---------- lifecycle ----------

    def _import_ws(self):
        try:
            import websocket  # websocket-client
        except ImportError as e:  # pragma: no cover
            raise TransportError(
                "websocket-client not installed: pip install websocket-client"
            ) from e
        return websocket

    def connect(self) -> "BrowserOracle":
        """Attach to a page target, reusing the live socket when possible.

        Raises TransportError (an OzonError) on every failure path, and never
        leaves a half-built connection behind — otherwise the next call would
        open a second socket and leak the first.
        """
        if self._ws is not None and self._sess:
            return self
        ws_mod = self._import_ws()
        ws = None
        try:
            ver = _http_json(f"{self.cdp}/json/version")
            ws = ws_mod.create_connection(
                ver["webSocketDebuggerUrl"], timeout=max(self.timeout, 60)
            )
            tabs = _http_json(f"{self.cdp}/json/list")
        except Exception:
            if ws is not None:
                try:
                    ws.close()
                except Exception:
                    pass
            self._ws = None
            self._sess = None
            raise
        self._ws = ws
        pages = [t for t in tabs if t.get("type") == "page"]
        if not pages:
            self.close()
            raise TransportError("no page target open in Chrome")
        # prefer a tab already on our origin; fall back to the first page
        tab = next((t for t in pages if "ozon." in (t.get("url") or "")),
                   pages[0])
        try:
            res = self._send("Target.attachToTarget",
                             {"targetId": tab["id"], "flatten": True})
        except Exception:
            self.close()
            raise
        self._sess = res["sessionId"]
        self._tab_url = tab.get("url", "")
        return self


    def close(self):
        try:
            if self._ws:
                self._ws.close()
        except Exception:
            pass
        self._ws = None
        self._sess = None

    # ---------- CDP plumbing ----------

    def _send(self, method: str, params: dict | None = None) -> dict:
        """Send one CDP command and wait for its matching response.

        Respects ``self.timeout``: once the deadline passes we give up instead
        of looping on a 1-second socket timeout forever. Non-matching events
        (Page/Network notifications) are skipped, not treated as replies.
        """
        if self._ws is None:
            raise TransportError("not connected")
        self._id += 1
        msg: dict[str, Any] = {"id": self._id, "method": method,
                               "params": params or {}}
        if self._sess:
            msg["sessionId"] = self._sess
        self._ws.send(json.dumps(msg))
        deadline = time.time() + self.timeout
        while True:
            remaining = deadline - time.time()
            if remaining <= 0:
                self.close()
                raise TransportError(
                    f"CDP {method}: timed out after {self.timeout:.0f}s"
                )
            self._ws.settimeout(min(remaining, 5.0))
            try:
                raw = self._ws.recv()
            except Exception as e:
                if time.time() >= deadline:
                    self.close()
                    raise TransportError(
                        f"CDP {method}: timed out after {self.timeout:.0f}s"
                    ) from e
                continue          # transient socket timeout, keep waiting
            m = json.loads(raw)
            if m.get("id") == self._id:
                if "error" in m:
                    raise TransportError(f"CDP {method}: {m['error']}")
                return m.get("result", {})

    def _evaluate(self, expression: str, await_promise: bool = True):
        res = self._send(
            "Runtime.evaluate",
            {"expression": expression, "awaitPromise": await_promise,
             "returnByValue": True, "userGesture": True},
        )
        if res.get("exceptionDetails"):
            d = res["exceptionDetails"]
            raise TransportError(
                f"page JS threw: {d.get('text', '')} "
                f"{str(d.get('exception', {}).get('description', ''))[:200]}"
            )
        return res.get("result", {}).get("value")

    def _note_wire(self, method: str, url: str, status: int) -> None:
        self.wire_log.append({
            "method": method.upper(),
            "target": _wire_target(url),
            "status": int(status),
        })

    # ---------- public request API ----------

    def request(self, method: str, url: str, headers: dict | None = None,
                json_body: Any = None, retries: int = 2) -> "OracleResponse":
        """Perform a request from inside the page.

        Retries transport-level failures with exponential backoff + jitter.
        HTTP 403/429 are NOT retried — a challenge or a rate limit fails
        the same way on a second try, so the caller gets the typed
        exception and the session cools down instead of burning the IP.
        5xx still retries within ``retries``. A repeated successful GET
        inside the cache TTL does not touch the network.
        """
        refusal = self._guard.refusal()
        if refusal is not None:
            raise refusal
        cached = self._cache.get(method, url)
        if cached is not None and json_body is None:
            self.cache_hits += 1
            return cached
        self.connect()
        last: Exception | None = None
        for attempt in range(retries + 1):
            self.throttle.acquire()
            js = self._build_js(method, url, headers, json_body)
            try:
                val = self._evaluate(js)
            except TransportError as e:
                last = e
                self._backoff(attempt, retries, base=1.5)
                continue
            if not isinstance(val, dict):
                last = TransportError(f"unexpected page result: {val!r}"[:300])
                self._backoff(attempt, retries, base=1.0)
                continue
            if val.get("err"):
                last = TransportError(
                    "fetch failed in page: " + redact_secrets(str(val["err"]))
                )
                self._backoff(attempt, retries, base=1.5)
                continue
            resp = OracleResponse(val)
            self._note_wire(method, url, resp.status)
            if is_antibot_challenge(resp):
                incident = _incident_id(resp.text or "", resp.headers)
                # No re-fetch. One challenge cools the browser session down.
                self._guard.on_challenge(incident, may_retry=False)
                raise AntibotBlocked(incident, None, None)
            if resp.status == 429:
                retry_after = resp.headers.get("retry-after")
                self._guard.on_rate_limit(retry_after)
                raise RateLimited(retry_after)
            if resp.status in (500, 502, 503, 504) and attempt < retries:
                last = TransportError(f"HTTP {resp.status}")
                self._backoff(attempt, retries, base=2.0)
                continue
            self._raise_for_status(resp)
            self._guard.on_success()
            self._cache.put(method, url, resp)
            return resp
        raise last if last else TransportError("request failed")

    @staticmethod
    def _backoff(attempt: int, retries: int, base: float) -> None:
        """Sleep base * 2**attempt, jittered +-25%; no-op on the last try."""
        if attempt >= retries:
            return
        time.sleep(base * (2 ** attempt) * random.uniform(0.75, 1.25))

    @staticmethod
    def _raise_for_status(resp: "OracleResponse"):
        st = resp.status
        if 200 <= st < 300:
            return
        body = redact_secrets(resp.text or "", limit=200)
        if st == 429:
            raise RateLimited(resp.headers.get("retry-after"))
        if st == 404:
            raise NotFound(f"404 {resp.url}")
        if st == 401:
            raise AuthRequired(f"401 {resp.url} — needs a logged-in session")
        if st == 403:
            incident = _incident_id(resp.text or "", resp.headers)
            if incident or "ozon-antibot" in str(resp.headers):
                raise AntibotBlocked(incident, None, None)
            raise AuthRequired(f"403 {resp.url} — blocked, no antibot incident id")
        raise OzonError(f"HTTP {st} for {resp.url}: {body}")

    def _build_js(self, method: str, url: str, headers, json_body) -> str:
        h = dict(headers or {})
        h.setdefault("accept", "application/json")
        h.setdefault("content-type", "application/json")
        h.setdefault("x-o3-app-name", "dweb_client")
        body_js = "null"
        if json_body is not None:
            body_js = json.dumps(json.dumps(json_body, ensure_ascii=False))
        return """(async () => {
  const opt = {method: %s, credentials: 'include', headers: %s};
  if (%s !== null) opt.body = %s;
  try {
    const r = await fetch(%s, opt);
    const t = await r.text();
    const hdrs = {};
    r.headers.forEach((v, k) => { hdrs[k] = v; });
    return {status: r.status, body: t, headers: hdrs, url: r.url, err: null};
  } catch (e) { return {err: String(e).slice(0, 300)}; }
})()""" % (
            json.dumps(method.upper()),
            json.dumps(h, ensure_ascii=False),
            body_js,
            body_js,
            json.dumps(url),
        )

    # ---------- session warmup ----------

    def warmup(self, url: str = "https://www.ozon.ru/?__rr=1",
               settle: float = 6.0, *, search: str | None = None) -> dict:
        """Open a plausible entry, then the requested document.

        Home is always the first navigation. ``search`` (optional) is a
        catalogue query visited after home. ``url`` is opened after that
        only when it is not itself home. A single home warmup — the common
        case — is still one navigation and sleeps ``settle`` once.

        The returned dict includes ``entry``, the absolute URLs landed on,
        in order. No cookie values.
        """
        self.connect()
        origin = _origin_of(url)
        home = f"{origin}/?__rr=1"
        trail: list[str] = []

        def nav(target: str, pause: float) -> None:
            self._send("Page.navigate", {"url": target})
            time.sleep(max(0.0, pause))
            trail.append(target)

        deep = not _same_document(home, url)
        if deep or search:
            nav(home, min(float(settle), 2.5))
            if search:
                nav(
                    f"{origin}/search/?text={quote(str(search))}&from_global=true",
                    min(float(settle), 2.5),
                )
            if deep:
                nav(url, float(settle))
        else:
            nav(home, float(settle))
        info = self._evaluate(
            "(async () => ({href: location.href, "
            "cookieCount: document.cookie.split(';').filter(Boolean).length, "
            "title: document.title}))()"
        )
        if not isinstance(info, dict):
            info = {}
        info["entry"] = trail
        return info

    def page_url(self) -> str:
        self.connect()
        return self._evaluate("location.href") or ""


class OracleResponse:
    """Minimal response object mirroring the requests API surface."""

    def __init__(self, val: dict):
        self.status: int = int(val.get("status", 0))
        self.text: str = val.get("body", "") or ""
        self.headers: dict = {k.lower(): v for k, v in (val.get("headers") or {}).items()}
        self.url: str = val.get("url", "")

    def json(self):
        try:
            return json.loads(self.text)
        except json.JSONDecodeError as e:
            from .exceptions import ParseError
            raise ParseError(
                f"non-JSON response ({self.status}): {redact_secrets(self.text, 200)}"
            ) from e

    def __repr__(self):
        return f"<OracleResponse {self.status} {len(self.text)}B>"
