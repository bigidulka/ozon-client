"""Signer/auth module — app headers, separate from the cookie jar.

CLASSIFICATION: Hybrid / challenge-handling Method 4.
The old line "TIER FOUND: 6 — browser-executed challenge, non-portable
clearance" was wrong. See audit/antibot_probe.md (2026-10-16).

A cold client — curl_cffi impersonating Chrome, full Chrome headers, these
`x-o3-*` headers, and no cookies — gets 403 with `ozon-antibot: 1` and a
JSON challenge descriptor (`incidentId`, `challengeURL`, `supportURL`,
`timeoutSec`, `blockURL`). The same request plus the browser's cookie jar
returns 200 on the same IP, with the same `widgetStates` payload as an
in-page fetch. The clearance is portable. It is not bound to the browser's
TLS session.

What that probe did **not** show: plain `requests` (no impersonation) plus
the jar, a different egress IP, which of the nine cookie names are
sufficient, or how long the jar stays valid. Declared `Expires` is not a
measured TTL. Do not treat "any HTTP client + the jar" as proven.
`CookieJarTransport` is the replay path; this module does not attach cookies.

`document.cookie` is the wrong handoff. It exposes only `__Secure-ab-group`
and `xcid`. `abt_data` and the other `__Secure-*` tokens are HttpOnly.
`abt_data` is also partitioned; reading it needs CDP, not JS.

This module only builds headers:

    headers(...)   -> the x-o3-* / page headers the frontend sends
    verify(...)    -> probes whether the current transport is still cleared

`x-o3-parent-requestid` and `x-page-view-id` stay fixed for one document
and rotate together when the document changes. Layout slices of the same
PDP (`layout_page_index`, `paginator_token`, …) are the same page view.
`x-page-previous` is the previous page *type* (`home`, `pdp`, `search`, …),
which is what `main.js` puts in that header (`previousPageType`), not a
second id. It is empty on the first page view. Header names, manifest and
app version are unchanged.

`signer_for(6)` still returns `BrowserSessionSigner` and `signer_for(0)`
returns `NullSigner`. The integer is a historical selector so existing
callers keep working. It is not a finding that the clearance is non-portable.
"""
from __future__ import annotations

import threading
import uuid
from typing import Any
from urllib.parse import parse_qs, parse_qsl, quote, urlencode, urlsplit

MANIFEST_VERSION = (
    "frontend-ozon-ru:aeebf0af395bcfe6503a42b7a9dce77ef16a9d6a,"
    "search-render-api:946cdcd43783bc56ad9623fe146d27ddcdebc700,"
    "fav-render-api:3c1be439a2254ff5c1f408c551c991dd20898ec4,"
    "rtb-render-api:769a37c1163b62075ca7570c2ddf81532306c7db,"
    "checkout-render-api:ed351a2a872750cc731de69618212ed89899bf48,"
    "sf-render-api:70dadc0de217fcb21a5c4adb2984a9a490891d93"
)
APP_VERSION = "release_15-9-2026_aeebf0af"

# Layout-slice and noise params. Two entrypoint URLs that differ only here
# are still one page view (PDP screen 1 and screen 2).
_LAYOUT_DROP = frozenset({
    "layout_page_index",
    "layout_container",
    "start_page_id",
    "paginator_token",
    "layout_page_token",
    "__rr",
})


def _split_doc(doc: str) -> tuple[str, list[tuple[str, str]]]:
    """Path plus query pairs for a site document or an absolute URL."""
    raw = (doc or "").strip()
    if raw.startswith("http://") or raw.startswith("https://"):
        parts = urlsplit(raw)
        return parts.path or "/", parse_qsl(parts.query, keep_blank_values=True)
    if "?" in raw:
        path, query = raw.split("?", 1)
    else:
        path, query = raw, ""
    if not path.startswith("/"):
        path = "/" + path
    return path or "/", parse_qsl(query, keep_blank_values=True)


def document_key(doc: str) -> str:
    """Stable identity of a document, ignoring layout-slice params.

    ``/product/x/?__rr=1`` and the paginator's ``layout_page_index=2`` URL
    share a key. ``page=2`` on a listing does not — that is a new document.
    Query values are re-encoded so the key is safe to use as a referer.
    """
    path, pairs = _split_doc(doc)
    kept = [(k, v) for k, v in pairs if k not in _LAYOUT_DROP]
    if not path.startswith("/"):
        path = "/" + path
    if path != "/" and not path.endswith("/"):
        path += "/"
    if not kept:
        return path or "/"
    return path + "?" + urlencode(kept, safe="", quote_via=quote)


def infer_page_type(doc: str) -> str:
    """Coarse page type, the shape of ``x-page-previous`` / ``x-o3-page-type``.

    Questions and reviews are matched before the PDP prefix so
    ``/product/<slug>/questions/`` is not labelled ``pdp``.
    """
    path, _pairs = _split_doc(doc)
    p = path.rstrip("/") or "/"
    if p == "/":
        return "home"
    if p == "/search" or p.startswith("/search/"):
        return "search"
    if p == "/category" or p.startswith("/category/"):
        return "category"
    if p.endswith("/questions") or "/questions/" in path:
        return "questions"
    if p.endswith("/reviews") or "/reviews/" in path or p.startswith("/reviews"):
        return "reviews"
    if p.startswith("/product"):
        return "pdp"
    if p.startswith("/cart"):
        return "cart"
    if "favorites" in p:
        return "favorites"
    seg = p.strip("/").split("/", 1)[0]
    return seg or "home"


def request_page_identity(url: str) -> tuple[str, str] | None:
    """``(document_key, page_type)`` for a navigation, or None for an XHR.

    Composer ``/_action/`` and widget calls fired from the current document
    keep the current page view. The entrypoint's ``url=`` query is the
    document. Anything else (a bare path) is its own page.
    """
    parts = urlsplit(url)
    qs = parse_qs(parts.query)
    path = parts.path or "/"
    if path.rstrip("/").endswith("page/json/v2") and qs.get("url"):
        doc = qs["url"][0]
        return document_key(doc), infer_page_type(doc)
    if "/_action/" in path or "/widget/json/" in path:
        return None
    return document_key(path), infer_page_type(path)


class Signer:
    """Interface every auth tier implements."""

    def headers(self, method: str, url: str, **kw) -> dict[str, str]:  # pragma: no cover
        raise NotImplementedError

    def verify(self, transport) -> bool:  # pragma: no cover
        raise NotImplementedError


class BrowserSessionSigner(Signer):
    """Frontend app headers. Clearance is the cookie jar, not this class.

    curl_cffi impersonating Chrome can send that jar and get 200 on the
    same IP (audit/antibot_probe.md). This signer does not hold the cookies
    and does not require the browser's TLS session. Plain `requests` plus
    the jar was not tested. `document.cookie` is not a complete jar
    (`abt_data` and most `__Secure-*` cookies are HttpOnly).

    The x-o3-* headers below are what the real frontend sends (captured from
    live traffic). They are not the antibot clearance — the same headers
    with no cookies are still challenged — but every transport should keep
    sending them. ``x-o3-parent-requestid`` and ``x-page-view-id`` rotate
    once per document, not once per HTTP call. ``x-page-previous`` carries
    the previous page type (empty on the first view).
    """

    def __init__(self, page_view_id: str | None = None,
                 parent_request_id: str | None = None):
        self.page_view_id = page_view_id or str(uuid.uuid4())
        self.parent_request_id = parent_request_id or uuid.uuid4().hex
        self._page_previous = ""
        self._page_key: str | None = None
        self._page_type = ""
        self._lock = threading.Lock()

    def _rotate(self) -> None:
        self._page_previous = self._page_type
        self.page_view_id = str(uuid.uuid4())
        self.parent_request_id = uuid.uuid4().hex

    def _bind(self, key: str, page_type: str) -> None:
        if self._page_key is None:
            self._page_key = key
            self._page_type = page_type
            return
        if key == self._page_key:
            return
        self._rotate()
        self._page_key = key
        self._page_type = page_type

    def note_entry(self, trail: list[str]) -> None:
        """Bind a warmup trail (home, optional search, optional deep URL).

        The first document keeps the ids this signer was constructed with.
        Each later document rotates once, so the next API call's
        ``x-page-previous`` is the type of the page warmup landed on only
        after a further navigation. After a home-only warmup the current
        view is ``home`` and ``x-page-previous`` is still empty — the
        following search/PDP call is what sets previous to ``home``.
        """
        with self._lock:
            self._page_previous = ""
            self._page_key = None
            self._page_type = ""
            for doc in trail or []:
                self._bind(document_key(doc), infer_page_type(doc))

    def headers(self, method: str, url: str, referer: str | None = None) -> dict[str, str]:
        with self._lock:
            ident = request_page_identity(url)
            if ident is None:
                if self._page_key is None:
                    path = urlsplit(url).path or "/"
                    self._bind(path, "summary" if path.rstrip("/").endswith("summaryV2") else infer_page_type(path))
            else:
                self._bind(*ident)
            prev = self._page_previous
            page_view = self.page_view_id
            parent = self.parent_request_id
        return {
            "x-o3-app-name": "dweb_client",
            "x-o3-app-version": APP_VERSION,
            "x-o3-manifest-version": MANIFEST_VERSION,
            "x-o3-parent-requestid": parent,
            "x-page-view-id": page_view,
            "x-page-previous": prev,
            "accept": "application/json",
            "content-type": "application/json",
            **({"referer": referer} if referer else {}),
        }

    def verify(self, client) -> bool:
        """Session is warm iff the cheapest gated endpoint returns 200.

        Never raises: any failure — including a raw socket timeout, which is
        not an OzonError — simply means "not warm".
        """
        url = f"{client.base}/api/composer-api.bx/_action/summaryV2"
        try:
            r = client.transport.request(
                "GET", url, headers=self.headers("GET", url), retries=0,
            )
            return r.status == 200
        except Exception:
            return False


class NullSigner(Signer):
    """No auth at all — for CDN/static hosts that are not gated."""

    def headers(self, method: str, url: str, **kw) -> dict[str, str]:
        return {"accept": "*/*"}

    def verify(self, client) -> bool:
        return True


def signer_for(tier: int = 6, **kw: Any) -> Signer:
    if tier == 6:
        return BrowserSessionSigner(**kw)
    if tier == 0:
        return NullSigner()
    raise ValueError(
        f"no signer implemented for tier {tier} — only selector 6 "
        "(BrowserSessionSigner) and 0 (NullSigner) are implemented"
    )
