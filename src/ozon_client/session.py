"""Session domain: summary, cart, favourites, address bar.

These are the small "chrome" endpoints the site fires on every page load.
All are read-only here — nothing in this module mutates state on the target.
"""
from __future__ import annotations

from .exceptions import ParseError

COMPOSER = "/api/composer-api.bx"


def summary(client) -> dict:
    """Cheapest gated call — doubles as the session-warmth probe.

    Live response is `{}` (2 bytes) for an anonymous session.
    """
    url = f"{client.base}{COMPOSER}/_action/summaryV2"
    r = client.transport.request("GET", url,
                                 headers=client.signer.headers("GET", url))
    try:
        return r.json()
    except ParseError:
        return {"raw": r.text}


def cart(client) -> dict:
    """Cart contents (anonymous session -> mostly empty)."""
    from urllib.parse import quote

    from .catalog import _page_url
    env = _page_url(client, "/cart")
    if not isinstance(env, dict):
        raise ParseError("cart: envelope is not an object")
    return {
        "seo": (env.get("seo") or {}).get("title"),
        "widget_count": len(env.get("widgetStates") or {}),
        "pageInfo": env.get("pageInfo"),
    }


def favorites(client) -> dict:
    """Favourites page for the current (anonymous) session."""
    from .catalog import _page_url
    from .exceptions import ParseError

    env = _page_url(client, "/my/favorites/")
    if not isinstance(env, dict):
        raise ParseError("favorites: envelope is not an object")
    return {
        "seo": (env.get("seo") or {}).get("title"),
        "widget_count": len(env.get("widgetStates") or {}),
    }


def address_bar(client, prv: str = "home") -> dict:
    """Location/address widget (`addressBookBarTooltip`). Read-only."""
    url = (f"{client.base}{COMPOSER}/_action/v2/addressBookBarTooltip"
           f"?prv={prv}&set_sm=1")
    r = client.transport.request("POST", url, json_body={},
                                 headers=client.signer.headers("POST", url))
    return r.json()


def menu_children(client, menu_id: int = 237) -> dict:
    """Horizontal catalogue menu children."""
    url = f"{client.base}{COMPOSER}/_action/v2/shellHorizontalMenuGetChildV1?menuId={menu_id}"
    r = client.transport.request("GET", url,
                                 headers=client.signer.headers("GET", url))
    return r.json()


def search_suggest(client, text: str = "") -> dict:
    """searchSuggestions — the site fires this on nearly every page."""
    from urllib.parse import quote

    from .catalog import _page_url
    env = _page_url(client, "/searchSuggestions/search/",
                    **{"text": text, "from_global": "true"})
    return {
        "seo": (env.get("seo") or {}).get("title") if isinstance(env, dict) else None,
        "widget_count": len(env.get("widgetStates") or {}) if isinstance(env, dict) else 0,
    }
