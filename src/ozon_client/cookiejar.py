"""Cookie-jar transport — curl_cffi replay of a browser-minted jar.

Hybrid / challenge-handling Method 4 (audit/antibot_probe.md, 2026-10-16).
A cold curl_cffi client is still 403 + ``ozon-antibot: 1``. The same client
with the browser's cookies returns 200 on the same IP. The clearance is the
jar, not the browser TLS session.

The nine names, values never logged or written:

    __Secure-access-token, abt_data, __Secure-ab-group, __Secure-user-id,
    __Secure-ext_xcid, xcid, cookie_settings, __Secure-ETC,
    __Secure-refresh-token

``document.cookie`` only shows ``__Secure-ab-group`` and ``xcid``. The rest
are HttpOnly. ``abt_data`` is also partitioned (``topLevelSite`` = the Ozon
origin). ``Network.getCookies`` for ``https://ozon.by/`` omitted it when the
attached tab was not on that origin; ``Network.getAllCookies`` returned it.
This module filters to the first-party cookie for our host and drops every
other site's cookies immediately.

A warm Chrome is required once, to mint. Later requests do not use the page.

The jar is bound to the UA that minted it. curl_cffi 0.15.0's newest
desktop profile is ``chrome146``; the live browser here is Chrome/153.
Sending the profile's own UA and ``sec-ch-ua*`` with that jar is 403.
Sending the minting browser's UA on the same TLS profile is 200. So the
default ``ua_source`` is ``browser`` (``auto`` is the same thing): UA,
``sec-ch-ua`` and ``sec-ch-ua-platform`` come from the live page, even
when that Chrome is newer than the impersonation profile. ``profile`` is
an explicit opt-in for a browser whose major matches the profile. A 403
with ``ozon-antibot: 1`` while profile hints are in use is retried once
with the live UA, then the session cools down. It is not retried again.

That leaves a known hole: TLS says Chrome 146, the UA says Chrome 153.
Nothing in curl_cffi 0.15.0 closes it. See ``ANTI-DETECTION.md``.

Referer is not a fixed home URL. It follows the documents this process has
actually requested (home, then search/category, then the product). ``warmup``
lands the real browser on home (then optional search, then a deep URL) and
seeds that story.

On any other challenge (JSON descriptor, or masked HTML with an incident
id, even when status is not 403) the jar is re-read once, after an
exponential backoff, and the same UA is kept. A second consecutive
challenge, a third challenge in the session, or a 429 cools the session
down: later calls raise and do not send. 403/429 are never retried in a loop.
"""
from __future__ import annotations

import re
import threading
import time
from typing import Any
from urllib.parse import parse_qs, quote, urlsplit

from .auth import document_key
from .exceptions import AntibotBlocked, RateLimited, TransportError
from .http import (
    DEFAULT_CDP,
    BrowserOracle,
    ChallengeGuard,
    OracleResponse,
    ResponseCache,
    _incident_id,
    _wire_target,
    is_antibot_challenge,
)
from .throttle import TokenBucket

# Order matches the probe. Values are never part of this tuple.
REQUIRED_COOKIE_NAMES: tuple[str, ...] = (
    "__Secure-access-token",
    "abt_data",
    "__Secure-ab-group",
    "__Secure-user-id",
    "__Secure-ext_xcid",
    "xcid",
    "cookie_settings",
    "__Secure-ETC",
    "__Secure-refresh-token",
)

_ACCEPT_LANGUAGE = "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7"
_CHROME_PROFILE = re.compile(r"chrome(\d+)([a-z]*)$")
_CHROME_UA = re.compile(r"Chrome/(\d+)")
# Drop Cookie / Set-Cookie assignments if a library exception quotes them.
# xcid and cookie_settings are in the jar and are not matched by __secure-.
_LEAK = re.compile(
    r"(?i)(cookie|set-cookie|abt_data|xcid|cookie_settings|__secure-[a-z0-9_-]+)"
    r"\s*[:=]\s*\S+"
)

_HINT_CACHE: dict[str, dict[str, str]] = {}
_HINT_LOCK = threading.Lock()
_UA_SOURCES = frozenset({"profile", "browser", "auto"})


def curl_cffi_available() -> bool:
    """True when the optional browser-free extra is installed."""
    try:
        import curl_cffi.requests  # noqa: F401
    except ImportError:
        return False
    return True


def newest_chrome_impersonate() -> str:
    """Newest desktop Chrome profile shipped by the installed curl_cffi.

    Android profiles (``chrome131_android``) are skipped. A letter suffix
    such as ``chrome133a`` loses to a higher major. curl_cffi 0.15.0
    resolves to ``chrome146``; there is no ``chrome153`` profile. The
    literal is not pinned, so a newer library picks up its own newest
    desktop profile without a code change.
    """
    from curl_cffi.requests import BrowserType
    from curl_cffi.requests.impersonate import DEFAULT_CHROME

    best_name = str(DEFAULT_CHROME)
    best_key = (-1, -1)
    for member in BrowserType:
        name = member.value if isinstance(member.value, str) else str(member.name)
        match = _CHROME_PROFILE.fullmatch(name)
        if not match:
            continue
        key = (int(match.group(1)), 1 if match.group(2) == "" else 0)
        if key > best_key:
            best_key = key
            best_name = name
    return best_name


def _profile_major(impersonate: str) -> int | None:
    match = _CHROME_PROFILE.fullmatch(impersonate or "")
    if match:
        return int(match.group(1))
    found = re.search(r"chrome(\d+)", impersonate or "")
    return int(found.group(1)) if found else None


def _ua_major(ua: str) -> int | None:
    match = _CHROME_UA.search(ua or "")
    return int(match.group(1)) if match else None


def _synthetic_hints(impersonate: str) -> dict[str, str]:
    """Last resort when the localhost profile read fails. Same major as TLS."""
    major = _profile_major(impersonate) or 0
    version = str(major or 0)
    return {
        "user-agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            f"Chrome/{version}.0.0.0 Safari/537.36"
        ),
        "sec-ch-ua": (
            f'"Chromium";v="{version}", "Not-A.Brand";v="24", '
            f'"Google Chrome";v="{version}"'
        ),
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"macOS"',
    }


def _capture_profile_hints(impersonate: str) -> dict[str, str]:
    """Read the UA and client hints curl_cffi actually attaches for this profile.

    One request to 127.0.0.1, not to Ozon. Cached per profile name so a
    newer curl_cffi does not need a code change when chrome146 stops being
    the newest desktop profile.
    """
    from http.server import BaseHTTPRequestHandler, HTTPServer

    from curl_cffi.requests import Session

    captured: dict[str, str] = {}

    class _Handler(BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802
            wanted = ("user-agent", "sec-ch-ua", "sec-ch-ua-mobile", "sec-ch-ua-platform")
            for key, value in self.headers.items():
                if key.lower() in wanted:
                    captured[key.lower()] = value
            body = b"{}"
            self.send_response(200)
            self.send_header("content-type", "application/json")
            self.send_header("content-length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, fmt: str, *args) -> None:
            return

    server = HTTPServer(("127.0.0.1", 0), _Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        port = server.server_address[1]
        session = Session(impersonate=impersonate)
        try:
            session.get(f"http://127.0.0.1:{port}/profile-hints", timeout=10)
        finally:
            session.close()
    finally:
        server.shutdown()
        server.server_close()
    if "user-agent" not in captured or "sec-ch-ua" not in captured:
        return _synthetic_hints(impersonate)
    captured.setdefault("sec-ch-ua-mobile", "?0")
    captured.setdefault("sec-ch-ua-platform", '"macOS"')
    return captured


def profile_client_hints(impersonate: str) -> dict[str, str]:
    """UA + sec-ch-ua* that belong to ``impersonate``. Never a browser UA."""
    with _HINT_LOCK:
        cached = _HINT_CACHE.get(impersonate)
        if cached is not None:
            return dict(cached)
    try:
        hints = _capture_profile_hints(impersonate)
    except Exception:
        hints = _synthetic_hints(impersonate)
    with _HINT_LOCK:
        _HINT_CACHE[impersonate] = dict(hints)
        return dict(hints)


def _host_of(domain: str) -> str:
    return (domain or "").lstrip(".").lower()


def _partition_allows(partition: Any, host: str) -> bool:
    """Unpartitioned cookies pass. Partitioned ones must be first-party.

    Cross-site partitions (``hasCrossSiteAncestor``) are cookies embedded
    frames would send to other hosts. They are not part of the ozon.by jar
    the probe replayed.
    """
    if not partition:
        return True
    if isinstance(partition, str):
        top = partition
        cross = False
    elif isinstance(partition, dict):
        top = str(partition.get("topLevelSite") or partition.get("sourceOrigin") or "")
        cross = bool(partition.get("hasCrossSiteAncestor"))
    else:
        return False
    if cross:
        return False
    top_host = top.split("://", 1)[-1].split("/", 1)[0].split(":", 1)[0].lower()
    return top_host == host


def select_clearance_cookies(cookies: list[dict], host: str) -> dict[str, dict]:
    """Copy the clearance jar for ``host``. Names from the probe only.

    The returned dict holds values in memory for the curl session. Callers
    must not log it. Cookies for other domains, and partitioned cookies for
    other top-level sites, are not copied.
    """
    host = host.lower()
    chosen: dict[str, dict] = {}
    for cookie in cookies:
        if not isinstance(cookie, dict):
            continue
        name = cookie.get("name")
        if name not in REQUIRED_COOKIE_NAMES:
            continue
        domain = str(cookie.get("domain") or "")
        dom = _host_of(domain)
        if not dom or not (host == dom or host.endswith("." + dom)):
            continue
        path = str(cookie.get("path") or "/")
        if path != "/" and path != "":
            continue
        if not _partition_allows(cookie.get("partitionKey"), host):
            continue
        value = cookie.get("value")
        if not isinstance(value, str) or value == "":
            continue
        chosen[str(name)] = {
            "name": str(name),
            "value": value,
            "domain": domain,
            "path": path or "/",
            "secure": bool(cookie.get("secure")),
        }
    return chosen


def _safe_error(exc: BaseException) -> str:
    text = _LEAK.sub(r"\1=<redacted>", str(exc))
    return text[:300]


def _format_sec_ch_ua(brands: Any) -> str | None:
    if not isinstance(brands, list):
        return None
    parts: list[str] = []
    for brand in brands:
        if not isinstance(brand, dict):
            continue
        name = brand.get("brand")
        version = brand.get("version")
        if isinstance(name, str) and name and version is not None:
            parts.append(f'"{name}";v="{version}"')
    return ", ".join(parts) if parts else None


def _document_target(request_url: str) -> str | None:
    """Site document inside an entrypoint ``url=`` query, else None."""
    parts = urlsplit(request_url)
    if not parts.path.rstrip("/").endswith("page/json/v2"):
        return None
    qs = parse_qs(parts.query)
    if not qs.get("url"):
        return None
    return qs["url"][0]


class NavigationStory:
    """Referer chain for one cookie-jar session. URLs only, never cookies.

    Cold start refers from home. After a document succeeds, the next
    *different* document refers from it. A layout slice of the same
    document (PDP screen 2) refers from that document, which is what
    ``fetch()`` on the page would send.
    """

    def __init__(self, base: str):
        self.base = base.rstrip("/")
        self.home = f"{self.base}/?__rr=1"
        self.current: str | None = None
        self.current_key: str | None = None

    def referer_for(self, request_url: str) -> str:
        doc = _document_target(request_url)
        if doc is None:
            return self.current or self.home
        key = document_key(doc)
        if self.current is not None and key == self.current_key:
            return self.current
        return self.current or self.home

    def observe(self, request_url: str) -> None:
        doc = _document_target(request_url)
        if doc is None:
            return
        key = document_key(doc)
        if key == self.current_key:
            return
        self.current = self.home if key in ("", "/") else self.base + key
        self.current_key = key

    def adopt_trail(self, trail: list[str] | None) -> None:
        """Seed the story from warmup's navigation trail."""
        self.current = None
        self.current_key = None
        for url in trail or []:
            parts = urlsplit(url)
            doc = parts.path or "/"
            if parts.query:
                doc = doc + "?" + parts.query
            fake = (
                f"{self.base}/api/entrypoint-api.bx/page/json/v2?url="
                + quote(doc, safe="")
            )
            self.observe(fake)


class CookieJarTransport:
    """``curl_cffi`` transport with a CDP-minted cookie jar.

    ``request`` matches ``BrowserOracle.request``: ``.status``, ``.text``,
    ``.headers``, ``.url``, ``.json()`` via :class:`OracleResponse`.

    ``ua_source`` is ``browser`` (default; ``auto`` is the same) or
    ``profile``. Browser copies the live page's UA and client hints,
    including when that Chrome is newer than the TLS profile — the jar
    is bound to the UA that minted it. Profile is the impersonation
    profile's own hints, opt-in, and a 403 ``ozon-antibot: 1`` on those
    hints is retried once with the live UA.
    """

    def __init__(self, cdp: str = DEFAULT_CDP, timeout: float = 45.0,
                 throttle: TokenBucket | None = None, base: str = "https://ozon.by",
                 impersonate: str | None = None, ua_source: str | None = None):
        if not curl_cffi_available():
            raise TransportError(
                "curl_cffi is not installed. "
                "pip install 'ozon-client[browserfree]' "
                "or construct OzonClient(transport='browser')."
            )
        self.cdp = cdp.rstrip("/")
        self.timeout = timeout
        self.throttle = throttle or TokenBucket(rate=0.5, burst=1.0)
        self.base = base.rstrip("/")
        self.host = (urlsplit(self.base).hostname or "").lower()
        if not self.host:
            raise TransportError(f"cookie-jar transport needs an absolute base URL, got {base!r}")
        self.impersonate = impersonate or newest_chrome_impersonate()
        requested = (ua_source or "browser").strip().lower()
        if requested == "auto":
            requested = "browser"
        if requested not in ("profile", "browser"):
            raise TransportError(
                f"ua_source must be 'browser', 'auto', or 'profile', got {ua_source!r}"
            )
        self.ua_source_requested = requested
        self.ua_source = requested
        self.ua_fallback: str | None = None
        self.ua_mismatch: str | None = None
        # Set when a profile-hint 403 is given its one retry on the live UA.
        self._switched_to_browser = False
        self._client_hints: dict[str, str] = {}
        self._session = None
        self._oracle: BrowserOracle | None = None
        self._minted = False
        self._jar_names: list[str] = []
        self._story = NavigationStory(self.base)
        self._guard = ChallengeGuard()
        self._cache = ResponseCache()
        self.cache_hits = 0
        self._last_referer = self._story.home
        # Status codes of Ozon HTTP calls only. No headers, no bodies.
        self.statuses: list[int] = []
        # method / document path / status / referer. No cookie values.
        self.wire_log: list[dict] = []
        self._apply_hints(None)

    @property
    def user_agent(self) -> str:
        return self._client_hints.get("user-agent", "")

    def __repr__(self) -> str:
        # Names only. Never the jar.
        return (f"<CookieJarTransport impersonate={self.impersonate} "
                f"cookies={self._jar_names} ua_source={self.ua_source}>")

    # ---------- lifecycle ----------

    def _browser(self) -> BrowserOracle:
        """CDP client used only to mint cookies and read client hints.

        Its throttle is disabled so a cookie read does not spend the HTTP
        budget. ``BrowserOracle.request`` is not called on it.
        """
        if self._oracle is None:
            self._oracle = BrowserOracle(
                cdp=self.cdp, timeout=self.timeout, throttle=TokenBucket(rate=0),
            )
        return self._oracle

    def _ensure_session(self):
        if self._session is not None:
            return self._session
        from curl_cffi.requests import Session

        self._session = Session(impersonate=self.impersonate)
        return self._session

    def close(self):
        try:
            if self._session is not None:
                self._session.close()
        except Exception:
            pass
        self._session = None
        self._minted = False
        self._jar_names = []
        try:
            if self._oracle is not None:
                self._oracle.close()
        except Exception:
            pass
        self._oracle = None

    def connect(self) -> "CookieJarTransport":
        """Mint the jar if needed. Does not call Ozon."""
        self._ensure_minted()
        return self

    def page_url(self) -> str:
        return self._browser().page_url()

    def warmup(self, url: str | None = None, settle: float = 6.0,
               *, search: str | None = None) -> dict:
        """Navigate home, optional search, then ``url`` if it is deeper.

        Same entry as ``BrowserOracle.warmup``. The jar is re-read after
        the browser lands, and the referer story is seeded from ``entry``.
        The returned dict lists cookie names, never values.
        """
        target = url or f"{self.base}/?__rr=1"
        info = self._browser().warmup(target, settle=settle, search=search)
        self._mint(force=True)
        trail = info.get("entry") if isinstance(info, dict) else None
        if not isinstance(trail, list) or not trail:
            trail = [target]
        self._story.adopt_trail(trail)
        out = dict(info or {})
        out["jar_names"] = list(self._jar_names)
        out["transport"] = "cookiejar"
        out["impersonate"] = self.impersonate
        out["ua_source"] = self.ua_source
        if self.ua_fallback:
            out["ua_fallback"] = self.ua_fallback
        return out

    # ---------- mint ----------

    def _use_browser_hints(self) -> bool:
        return self.ua_source_requested == "browser" or self._switched_to_browser

    def _install_browser_hints(self, hints: Any, profile: dict[str, str]) -> bool:
        """Copy the live page's UA and client hints. True if they were usable."""
        if not isinstance(hints, dict):
            return False
        ua = hints.get("ua")
        sec = _format_sec_ch_ua(hints.get("brands"))
        if not (isinstance(ua, str) and ua.strip() and sec):
            return False
        platform = hints.get("platform")
        if isinstance(platform, str) and platform.strip():
            plat = f'"{platform.strip()}"'
        else:
            plat = profile.get("sec-ch-ua-platform", '"macOS"')
        self._client_hints = {
            "user-agent": ua.strip(),
            "sec-ch-ua": sec,
            "sec-ch-ua-mobile": "?1" if hints.get("mobile") else "?0",
            "sec-ch-ua-platform": plat,
        }
        self.ua_source = "browser"
        major = _ua_major(ua)
        pmajor = _profile_major(self.impersonate)
        if major is not None and pmajor is not None and major != pmajor:
            self.ua_mismatch = (
                f"UA is the minting Chrome/{major}; TLS impersonation is "
                f"{self.impersonate}. No curl_cffi profile matches. The jar "
                "requires this UA; the mismatch cannot be removed here."
            )
        else:
            self.ua_mismatch = None
        return True

    def _apply_hints(self, hints: Any) -> None:
        """Choose UA and sec-ch-ua*.

        ``browser`` (the default) always follows the live page, even when
        its major is newer than the impersonation profile. ``profile`` keeps
        the profile's own hints until a 403 ``ozon-antibot: 1`` sets
        ``_switched_to_browser`` for the one allowed retry. Hints are not
        logged. Cookie values are not involved.
        """
        profile = profile_client_hints(self.impersonate)
        if self._use_browser_hints():
            if self._install_browser_hints(hints, profile):
                if self._switched_to_browser and self.ua_source_requested == "profile":
                    self.ua_fallback = (
                        "profile client hints got 403 ozon-antibot; "
                        "one retry used the minting browser UA"
                    )
                else:
                    self.ua_fallback = None
                return
            if hints is None:
                # Called from __init__, before CDP. Mint replaces this.
                self._client_hints = dict(profile)
                self.ua_source = "browser"
                self.ua_fallback = None
                self.ua_mismatch = None
                return
            self.ua_fallback = (
                "browser client hints unreadable; using the profile client hints"
            )
            self._client_hints = dict(profile)
            self.ua_source = "profile"
            self.ua_mismatch = None
            return
        self._client_hints = dict(profile)
        self.ua_source = "profile"
        self.ua_mismatch = None
        self.ua_fallback = None
        if isinstance(hints, dict):
            major = _ua_major(str(hints.get("ua") or ""))
            pmajor = _profile_major(self.impersonate)
            if major is not None and pmajor is not None and major != pmajor:
                self.ua_fallback = (
                    f"profile hints kept by request; minting browser is "
                    f"Chrome/{major}, impersonation is {self.impersonate}"
                )

    def _read_browser_jar(self) -> tuple[dict[str, dict], Any]:
        oracle = self._browser()
        oracle.connect()
        raw = oracle._send("Network.getAllCookies", {})
        blob = raw.get("cookies") if isinstance(raw, dict) else None
        chosen = select_clearance_cookies(blob if isinstance(blob, list) else [], self.host)
        # Partitioned abt_data is invisible to getCookies unless the attached
        # tab is already on the origin. Use that only as a fill-in.
        if "abt_data" not in chosen:
            scoped = oracle._send("Network.getCookies", {"urls": [f"{self.base}/"]})
            extra_blob = scoped.get("cookies") if isinstance(scoped, dict) else None
            extra = select_clearance_cookies(
                extra_blob if isinstance(extra_blob, list) else [], self.host,
            )
            for name, cookie in extra.items():
                chosen.setdefault(name, cookie)
        hints = None
        try:
            hints = oracle._evaluate(
                "(() => { const d = navigator.userAgentData;"
                " return {ua: navigator.userAgent,"
                " brands: d && d.brands ? d.brands.map(b => ({brand: b.brand, version: b.version})) : null,"
                " mobile: !!(d && d.mobile), platform: d ? d.platform : ''}; })()",
                await_promise=False,
            )
        except TransportError:
            hints = None
        return chosen, hints

    def _install(self, chosen: dict[str, dict]) -> None:
        session = self._ensure_session()
        session.cookies.clear()
        for name in REQUIRED_COOKIE_NAMES:
            cookie = chosen[name]
            session.cookies.set(
                name,
                cookie["value"],
                domain=cookie["domain"],
                path=cookie["path"],
                secure=cookie["secure"],
            )
        self._jar_names = list(REQUIRED_COOKIE_NAMES)
        self._minted = True

    def _mint(self, force: bool = False) -> None:
        if self._minted and not force:
            return
        chosen, hints = self._read_browser_jar()
        missing = [name for name in REQUIRED_COOKIE_NAMES if name not in chosen]
        if missing:
            raise TransportError(
                "CDP cookie jar is missing "
                + ", ".join(missing)
                + ". document.cookie is not sufficient (HttpOnly; abt_data is "
                "partitioned). Land the warm Chrome on the origin "
                "(ozon warmup) and retry. Cookie values are not included here."
            )
        self._apply_hints(hints)
        self._install(chosen)

    def _ensure_minted(self) -> None:
        if not self._minted:
            self._mint(force=False)

    # ---------- request ----------

    def _headers(self, caller: dict | None, request_url: str) -> dict[str, str]:
        referer = self._story.referer_for(request_url)
        self._last_referer = referer
        headers = {
            "accept": "application/json",
            "accept-language": _ACCEPT_LANGUAGE,
            "content-type": "application/json",
            "priority": "u=1, i",
            "referer": referer,
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
        }
        for key, value in (caller or {}).items():
            if value is None:
                continue
            headers[str(key).lower()] = str(value)
        # Client hints and the navigation referer are owned by this
        # transport. A caller-supplied Chrome UA, or the old static home
        # referer, would undo the consistency fix.
        for key, value in self._client_hints.items():
            headers[key] = value
        headers["referer"] = referer
        return headers

    def _note_wire(self, method: str, url: str, status: int, referer: str | None,
                   cache: bool = False) -> None:
        self.wire_log.append({
            "method": method.upper(),
            "target": _wire_target(url),
            "status": int(status),
            "referer": referer,
            "cache": cache,
        })

    def _once(self, method: str, url: str, headers: dict | None,
              json_body: Any) -> OracleResponse:
        session = self._ensure_session()
        kwargs: dict[str, Any] = {
            "headers": self._headers(headers, url),
            "timeout": self.timeout,
        }
        if json_body is not None:
            kwargs["json"] = json_body
        try:
            response = session.request(method.upper(), url, **kwargs)
        except Exception as exc:
            raise TransportError(
                f"curl_cffi {method.upper()} failed: {_safe_error(exc)}"
            ) from exc
        # fetch() hides Set-Cookie from page JS. Drop it here too so a
        # caller printing response headers cannot persist a new cookie value.
        # The curl session still stores it in memory.
        visible: dict[str, str] = {}
        try:
            pairs = list(response.headers.items())
        except Exception:
            pairs = []
        for key, value in pairs:
            if str(key).lower() in ("set-cookie", "set-cookie2"):
                continue
            if isinstance(value, (list, tuple)):
                value = ", ".join(str(item) for item in value)
            visible[str(key)] = str(value)
        text = response.text if isinstance(getattr(response, "text", None), str) else ""
        status = int(response.status_code)
        self.statuses.append(status)
        return OracleResponse({
            "status": status,
            "body": text,
            "headers": visible,
            "url": str(response.url),
        })

    def request(self, method: str, url: str, headers: dict | None = None,
                json_body: Any = None, retries: int = 2) -> OracleResponse:
        """Transport retries, one challenge retry, then a hard cool-down.

        Transport errors and HTTP 5xx use ``retries`` with backoff. 429 is
        not retried; it cools the session down. A challenge (antibot header,
        JSON descriptor, or masked HTML with an incident id — status need
        not be 403) re-mints from CDP once, after exponential backoff, even
        when ``retries`` is 0. A second consecutive challenge raises
        ``AntibotBlocked`` and does not send again until a new transport is
        built. Successful GETs are cached briefly so the product document
        ``questions()`` repeats is not fetched twice.
        """
        refusal = self._guard.refusal()
        if refusal is not None:
            raise refusal
        self._ensure_minted()
        refreshed = False
        attempt = 0
        while True:
            if attempt == 0 and not refreshed and json_body is None:
                cached = self._cache.get(method, url)
                if cached is not None:
                    self.cache_hits += 1
                    self._story.observe(url)
                    self._note_wire(method, url, cached.status, None, cache=True)
                    return cached
            self.throttle.acquire()
            try:
                resp = self._once(method, url, headers, json_body)
            except TransportError:
                if attempt >= retries:
                    raise
                BrowserOracle._backoff(attempt, retries, base=1.5)
                attempt += 1
                continue
            self._note_wire(method, url, resp.status, self._last_referer)
            if is_antibot_challenge(resp):
                incident = _incident_id(resp.text or "", resp.headers)
                # Profile hints + ozon-antibot 403 get their one retry on
                # the minting UA. Any other challenge still gets one remint
                # on the UA already in use. Never a second retry.
                switch_ua = (
                    not refreshed
                    and resp.status == 403
                    and str(resp.headers.get("ozon-antibot", "")).strip() == "1"
                    and self.ua_source == "profile"
                    and not self._switched_to_browser
                )
                if self._guard.on_challenge(incident, may_retry=not refreshed):
                    if switch_ua:
                        self._switched_to_browser = True
                    time.sleep(self._guard.backoff_seconds())
                    try:
                        self._mint(force=True)
                    except Exception:
                        self._guard.on_challenge(incident, may_retry=False)
                        raise AntibotBlocked(incident, None, None) from None
                    refreshed = True
                    continue
                raise AntibotBlocked(incident, None, None)
            if resp.status == 429:
                retry_after = resp.headers.get("retry-after")
                self._guard.on_rate_limit(retry_after)
                raise RateLimited(retry_after)
            if resp.status in (500, 502, 503, 504) and attempt < retries:
                BrowserOracle._backoff(attempt, retries, base=2.0)
                attempt += 1
                continue
            BrowserOracle._raise_for_status(resp)
            self._guard.on_success()
            if json_body is None:
                self._cache.put(method, url, resp)
            self._story.observe(url)
            return resp
