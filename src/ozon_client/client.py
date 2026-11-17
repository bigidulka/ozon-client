"""Ozon client facade.

    from ozon_client import OzonClient
    c = OzonClient()                        # browser oracle on :9222 (default)
    c = OzonClient(transport="cookiejar")  # curl_cffi + CDP cookie jar
    c.search("iphone 17")                   # -> {"products": [...], ...}
"""
from __future__ import annotations

import os
import sys

from . import catalog, session
from .auth import BrowserSessionSigner, Signer, signer_for
from .http import BrowserOracle
from .throttle import TokenBucket

DEFAULT_BASE = "https://ozon.by"

_BROWSER = {"browser", "oracle", "cdp", "browseroracle"}
_COOKIEJAR = {"cookiejar", "cookie-jar", "browserfree", "browser-free"}


def build_transport(name: str | None, *, cdp: str, timeout: float,
                    throttle: TokenBucket, base: str, ua_source: str | None = None):
    """Return ``(name, transport)``.

    ``cookiejar`` without ``curl_cffi`` falls back to ``BrowserOracle`` and
    says so on stderr. It does not raise at import time. An unknown name
    raises ``ValueError`` rather than silently picking a transport.
    """
    requested = (name or "browser").strip().lower()
    if requested in _BROWSER:
        return "browser", BrowserOracle(cdp=cdp, timeout=timeout, throttle=throttle)
    if requested in _COOKIEJAR:
        from .cookiejar import CookieJarTransport, curl_cffi_available

        if not curl_cffi_available():
            print(
                "ozon_client: transport 'cookiejar' needs curl_cffi "
                "(pip install 'ozon-client[browserfree]'). "
                "Falling back to BrowserOracle.",
                file=sys.stderr,
            )
            return "browser", BrowserOracle(
                cdp=cdp, timeout=timeout, throttle=throttle,
            )
        return "cookiejar", CookieJarTransport(
            cdp=cdp, timeout=timeout, throttle=throttle, base=base,
            ua_source=ua_source,
        )
    raise ValueError(
        f"unknown transport {name!r}; expected 'browser' or 'cookiejar'"
    )


class OzonClient:
    """Facade over the domain modules.

    ``transport`` is ``"browser"`` (default) or ``"cookiejar"``. The default
    stays the in-page oracle: existing ``OzonClient()`` callers keep working
    without the optional ``curl_cffi`` extra, and the live browser jar is
    still what the site itself refreshes. Cookie-jar mode is opt-in
    (``transport="cookiejar"`` or ``OZON_TRANSPORT``). It still needs Chrome
    once to mint cookies; after that the requests are curl_cffi.
    """

    def __init__(self, base: str | None = None, cdp: str | None = None,
                 rate: float = 0.5, burst: float = 1.0, tier: int = 6,
                 signer: Signer | None = None, timeout: float = 45.0,
                 transport: str | None = None, ua_source: str | None = None):
        self.base = (base or os.getenv("OZON_BASE") or DEFAULT_BASE).rstrip("/")
        self.cdp = cdp or os.getenv("OZON_CDP") or "http://127.0.0.1:9222"
        self.throttle = TokenBucket(rate=rate, burst=burst)
        requested = transport if transport is not None else os.getenv("OZON_TRANSPORT")
        ua = ua_source if ua_source is not None else os.getenv("OZON_UA_SOURCE")
        self.transport_name, self.transport = build_transport(
            requested, cdp=self.cdp, timeout=timeout,
            throttle=self.throttle, base=self.base, ua_source=ua,
        )
        self.signer = signer or signer_for(tier)

    @property
    def throttle(self):
        return self._throttle

    @throttle.setter
    def throttle(self, bucket):
        """Reassigning also repoints the transport, so a shared bucket
        really is shared (the transport acquires from its own reference)."""
        self._throttle = bucket
        if getattr(self, "transport", None) is not None:
            self.transport.throttle = bucket

    # --- lifecycle ---
    def warmup(self, url: str | None = None, search: str | None = None) -> dict:
        """Home, then optional search, then ``url`` when it is not home.

        The signer's page-view ids follow that entry trail. Cookie-jar mode
        uses the same trail as its referer chain. Call this before a deep
        product, reviews, or questions URL.
        """
        target = url or f"{self.base}/?__rr=1"
        info = self.transport.warmup(target, search=search)
        note = getattr(self.signer, "note_entry", None)
        if callable(note):
            trail = info.get("entry") if isinstance(info, dict) else None
            note(trail if isinstance(trail, list) and trail else [target])
        return info

    def ready(self) -> bool:
        return self.signer.verify(self)

    def page_url(self) -> str:
        return self.transport.page_url()

    def close(self):
        self.transport.close()

    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.close()

    # --- catalog ---
    def search(self, query: str, page: int = 1, *,
               sorting: str | None = None, filters: dict | None = None) -> dict:
        return catalog.search(self, query, page=page, sorting=sorting, filters=filters)

    def product(self, url_or_sku: str) -> dict:
        return catalog.product(self, url_or_sku)

    def category(self, slug: str, page: int = 1, *,
                 sorting: str | None = None, filters: dict | None = None) -> dict:
        return catalog.category(self, slug, page=page, sorting=sorting, filters=filters)

    def reviews(self, sku: str, page: int = 1, sort: str | None = None) -> dict:
        return catalog.reviews(self, sku, page=page, sort=sort)

    def questions(self, sku_or_url: str, qsort: str | None = None,
                  cursor: str | None = None) -> dict:
        return catalog.questions(self, sku_or_url, qsort=qsort, cursor=cursor)

    # --- session ---
    def summary(self) -> dict:
        return session.summary(self)

    def cart(self) -> dict:
        return session.cart(self)

    def favorites(self) -> dict:
        return session.favorites(self)

    def address_bar(self, prv: str = "home") -> dict:
        return session.address_bar(self, prv)

    def menu_children(self, menu_id: int = 237) -> dict:
        return session.menu_children(self, menu_id)

    def search_suggest(self, text: str = "") -> dict:
        return session.search_suggest(self, text)

    def page(self, url: str) -> dict:
        return catalog.page(self, url)

    def brand(self, slug: str, page: int = 1, *,
              sorting: str | None = None, filters: dict | None = None) -> dict:
        return catalog.brand(self, slug, page=page, sorting=sorting, filters=filters)

    def seller(self, slug: str, page: int = 1, *,
               sorting: str | None = None, filters: dict | None = None) -> dict:
        return catalog.seller(self, slug, page=page, sorting=sorting, filters=filters)

    def highlight(self, slug: str, page: int = 1, *,
                  sorting: str | None = None, filters: dict | None = None) -> dict:
        return catalog.highlight(self, slug, page=page, sorting=sorting, filters=filters)

    def brands(self) -> dict:
        return catalog.brands(self)

    def sellers(self, cursor: str | None = None) -> dict:
        return catalog.sellers(self, cursor=cursor)

    def similar(self, url_or_sku: str) -> dict:
        return catalog.similar(self, url_or_sku)

    def media(self, url_or_sku: str) -> dict:
        return catalog.media(self, url_or_sku)

    def features(self, url_or_sku: str) -> dict:
        return catalog.features(self, url_or_sku)

    def review_stats(self, url_or_sku: str, variant: str = "all") -> dict:
        return catalog.review_stats(self, url_or_sku, variant=variant)

    def availability(self, url_or_sku: str) -> dict:
        return catalog.availability(self, url_or_sku)

    def location_current(self) -> dict:
        return catalog.location_current(self)

    def location_search(self, text: str, limit: int = 10) -> dict:
        return catalog.location_search(self, text, limit=limit)

    def review_comments(self, review_uuid: str, sku: str, *,
                        root_sku: str | None = None, limit: int = 10,
                        offset: int = 0) -> dict:
        return catalog.review_comments(
            self, review_uuid, sku, root_sku=root_sku, limit=limit, offset=offset,
        )


__all__ = ["OzonClient", "BrowserSessionSigner", "signer_for", "build_transport",
           "catalog", "session"]
