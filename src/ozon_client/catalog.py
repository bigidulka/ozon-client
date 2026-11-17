"""Catalog domain: search, product card, category, reviews, questions.

Response shape (captured live, not assumed). `entrypoint-api.bx/page/json/v2`
returns an envelope:

    {"layout": [...], "widgetStates": {"<widget>-<id>-default-N": "<json str>",
     "shared": ..., "seo": {...}, "pageInfo": {...}, "location": {...}}}

Product tiles live under `tileGrid*`, `tileScrollDesktop`, `skuGrid` and
`skuShelfGoods` widget states. Prices are a `priceV2` atom
(`price[].text` + `textStyle`), not a flat field. `?tab=` on a product URL
is a scroll hint only — it does not change the widget set. Description and
full characteristics are on layout page 2, reached via `paginator.nextPage`
(`layout_container=pdpPage2column&layout_page_index=2`).
"""
from __future__ import annotations

import html
import json
import re
from html.parser import HTMLParser
from typing import Any, Iterator
from urllib.parse import quote, unquote, urlparse

from .exceptions import NotFound, ParseError

ENTRYPOINT = "/api/entrypoint-api.bx/page/json/v2"
COMPOSER = "/api/composer-api.bx"

# widget-state keys that hold product tiles (observed live).
# `tileGridDesktop`, `tileScrollDesktop` share the tile shape; `skuGrid` and
# `skuShelfGoods` keep the same atoms under productContainer.products.
_TILE_WIDGET_RE = re.compile(
    r"^(?:tileGrid\w*|tileScrollDesktop\w*|skuGrid\w*|skuShelfGoods\w*)"
)

# PDP `?tab=` is not a data selector (byte-identical to screen 1). Never send it.
_PDP_PAGE2_QUERY = "layout_container=pdpPage2column&layout_page_index=2"


def _page_url(client, path: str, **params) -> dict:
    """Fetch a rendered page envelope through the entrypoint API."""
    target = str(path).strip()
    if target.startswith("http://") or target.startswith("https://"):
        target = _site_path(target, keep_query=True)
    if not target.startswith("/"):
        target = "/" + target
    extra = "&".join(
        f"{k}={quote(str(v), safe='')}" for k, v in params.items() if v is not None
    )
    if extra:
        target += ("&" if "?" in target else "?") + extra
    url = f"{client.base}{ENTRYPOINT}?url={quote(target, safe='')}"
    r = client.transport.request("GET", url,
                                 headers=client.signer.headers("GET", url))
    return r.json()


def _site_path(value: str, keep_query: bool = False) -> str:
    """Host-relative path. Absolute URLs lose the host; query is optional."""
    raw = str(value).strip()
    if raw.startswith("http://") or raw.startswith("https://"):
        u = urlparse(raw)
        raw = u.path or "/"
        if keep_query and u.query:
            raw = raw + "?" + u.query
    if not raw.startswith("/"):
        raw = "/" + raw
    if not keep_query:
        raw = raw.split("?", 1)[0]
    return raw


def _with_slash(path: str) -> str:
    if "?" in path:
        base, query = path.split("?", 1)
        if not base.endswith("/"):
            base += "/"
        return base + "?" + query
    return path if path.endswith("/") else path + "/"


def _iter_atoms(node: Any) -> Iterator[dict]:
    """Yield every dict inside mainState-like atom lists."""
    if isinstance(node, dict):
        yield node
        for v in node.values():
            yield from _iter_atoms(v)
    elif isinstance(node, list):
        for v in node:
            yield from _iter_atoms(v)


def _collect(node: Any, key: str, out: list):
    if isinstance(node, dict):
        for k, v in node.items():
            if k == key and isinstance(v, (str, int, float)):
                out.append(v)
            _collect(v, key, out)
    elif isinstance(node, list):
        for v in node:
            _collect(v, key, out)


_PRICE_RE = re.compile(r"^[\d\s\u00a0\u202f\u2009,.]+$")
# `р.` must be a standalone token/word — "500 гр." (grams) is not a price.
_MONEY_RE = re.compile(r"(?<![\wа-яё])BYN(?![\wа-яё])|\u20bd"
                       r"|(?<![\wа-яё])руб\.?(?![\wа-яё])"
                       r"|(?<![\wа-яё])р\.(?![\wа-яё])", re.I)
# rating: 0..5 with 0-2 decimals; also matches "4,85"
_RATING_RE = re.compile(r"^[0-5]([.,]\d{1,2})?$")
_REVIEWS_RE = re.compile(r"(\d[\d\s\u00a0]*)\s*(отзыв|отзыва|отзывов)")
_NOISE_RE = re.compile(r"отзыв|шт\b|проверен|распродажа|хит|OZON|BYN|\u20bd", re.I)
# installment line inside its own priceV2 atom: "363,08 BYN × 12 мес"
_INSTALLMENT_RE = re.compile(r"×|\bx\b|мес", re.I)


def _norm(s: str) -> str:
    return str(s).replace("\u00a0", " ").replace("\u202f", " ").replace("\u2009", " ").strip()


def _digits(s: str) -> int:
    return sum(ch.isdigit() for ch in s)


def _iter_price_v2(node: Any) -> Iterator[dict]:
    """Every priceV2 atom. Search tiles carry two: installment, then the sale price."""
    if isinstance(node, dict):
        block = node.get("priceV2")
        taken = isinstance(block, dict) and (
            node.get("type") == "priceV2" or isinstance(block.get("price"), list)
        )
        if taken:
            yield block
        for key, value in node.items():
            if taken and key == "priceV2":
                continue
            yield from _iter_price_v2(value)
    elif isinstance(node, list):
        for value in node:
            yield from _iter_price_v2(value)


def _choose_price_v2(node: Any) -> dict | None:
    """Pick the sale price atom, not the installment (`× N мес`) atom.

    Absent entirely → None, and the caller uses the text heuristic.
    """
    blocks = list(_iter_price_v2(node))
    if not blocks:
        return None

    def rank(block: dict) -> tuple:
        price, original, discount = _price_from_v2(block)
        installment = bool(price and _INSTALLMENT_RE.search(price))
        style = None
        price_style = block.get("priceStyle")
        if isinstance(price_style, dict):
            style = price_style.get("styleType")
        return (
            0 if installment else 1,
            1 if original else 0,
            1 if discount else 0,
            1 if style == "SALE_PRICE" else 0,
        )

    return max(blocks, key=rank)


def _price_from_v2(block: dict) -> tuple[str | None, str | None, str | None]:
    """(price, original_price, discount) from a priceV2 atom.

    Prefer the entry whose textStyle is PRICE. ORIGINAL_PRICE and discount
    are kept beside it. The currency-text heuristic is intentionally not
    used here — that fallback is only for tiles with no priceV2 at all.
    """
    entries = [e for e in (block.get("price") or []) if isinstance(e, dict)]
    price = None
    original = None
    for entry in entries:
        text = entry.get("text")
        if not isinstance(text, str) or not text.strip():
            continue
        style = entry.get("textStyle")
        normed = _norm(text)
        if style == "PRICE" and price is None:
            price = normed
        elif style == "ORIGINAL_PRICE" and original is None:
            original = normed
    if price is None:
        for entry in entries:
            text = entry.get("text")
            if isinstance(text, str) and text.strip():
                price = _norm(text)
                break
    discount = block.get("discount") if isinstance(block.get("discount"), str) else None
    return price, original, discount


def parse_tile(item: dict) -> dict:
    """Flatten one product tile into a normalised record.

    Price comes from a `priceV2` atom (`textStyle == PRICE`, plus
    `ORIGINAL_PRICE` and `discount`) when one exists. A tile may carry two
    of those atoms — the installment line (`363 BYN × 12 мес`) and the sale
    price — and the sale price wins. Otherwise the legacy text heuristic
    applies: prefer the currency token with the most digits, and require the
    token to actually contain digits. Name, rating and review-count stay
    heuristic — tiles still have no flat fields for them.
    """
    texts: list[str] = []
    _collect(item, "text", texts)
    atoms: list[str] = []
    _collect(item, "atom", atoms)
    for a in atoms:            # some tiles carry the name in `atom`
        try:
            sub = json.loads(a)
        except Exception:
            continue
        _collect(sub, "text", texts)

    normed = [_norm(t) for t in texts]

    pv = _choose_price_v2(item)
    original_price = None
    discount = None
    if pv is not None:
        price, original_price, discount = _price_from_v2(pv)
    else:
        # price: currency token with the most digits wins
        money = [s for s in normed if _MONEY_RE.search(s) and _digits(s)]
        price = max(money, key=_digits) if money else None
        if price is None:
            # Currency may live in a sibling atom ("1 299" + "₽"): accept a bare
            # number, but require >=2 digits and reject anything that parses as a
            # rating — otherwise "4.85" is mistaken for a price.
            bare = [s for s in normed if _PRICE_RE.match(s) and _digits(s) >= 2
                    and not _RATING_RE.match(s)]
            price = max(bare, key=_digits) if bare else None

    # rating: 0..5 token that isn't the price. Prefer a decimal rating — a
    # bare integer is more often a quantity than a score.
    rating = None
    reviews = None
    plain = [s for s in normed if _RATING_RE.match(s) and s != price
             and s != original_price and "." not in s and "," not in s]
    dec = [s for s in normed if _RATING_RE.match(s) and s != price
           and s != original_price and ("." in s or "," in s)]
    rating = dec[0] if dec else (plain[0] if plain else None)
    for s in normed:
        m = _REVIEWS_RE.search(s)
        if m and reviews is None:
            reviews = m.group(1).strip()

    # name: longest non-noise text that isn't the price/rating
    cand = [s for s in normed
            if len(s) >= 4 and s != price and s != original_price and s != rating
            and not _NOISE_RE.search(s) and not _PRICE_RE.match(s)]
    name = max(cand, key=len) if cand else None
    if name is None and isinstance(item.get("alt"), str):
        alt = _norm(item["alt"])
        if len(alt) >= 4 and not _NOISE_RE.search(alt):
            name = alt

    link = None
    act = item.get("action") if isinstance(item.get("action"), dict) else {}
    if isinstance(act.get("link"), str):
        link = act["link"]
    elif isinstance(item.get("link"), str):
        link = item["link"]

    images: list[str] = []
    seen: set[str] = set()

    def _add_image(url: Any) -> None:
        if isinstance(url, str) and url and url not in seen:
            seen.add(url)
            images.append(url)

    ti = item.get("tileImage") or {}
    if isinstance(ti, dict):
        for im in (ti.get("items") or []):
            if isinstance(im, dict) and isinstance(im.get("image"), dict):
                _add_image(im["image"].get("link"))
    # skuGrid / skuShelfGoods carry images as items[].image.link
    for im in (item.get("items") or []):
        if isinstance(im, dict) and isinstance(im.get("image"), dict):
            _add_image(im["image"].get("link"))

    return {
        "sku": item.get("sku") or item.get("skuId") or item.get("id"),
        "name": name,
        "price": price,
        "original_price": original_price,
        "discount": discount,
        "rating": rating,
        "reviews": reviews,
        "url": link,
        "images": images,
    }


def _decode(raw: Any) -> Any:
    """Widget states are JSON-in-string; occasionally double-encoded, and
    occasionally already objects. Return something dict/list-shaped."""
    for _ in range(3):
        if not isinstance(raw, str):
            return raw if isinstance(raw, (dict, list)) else None
        try:
            raw = json.loads(raw)
        except (json.JSONDecodeError, ValueError):
            return None
    return raw if isinstance(raw, (dict, list)) else None


def _family(key: Any) -> str:
    return str(key).split("-", 1)[0]


def _widgets(envelope: dict, family: str) -> list[dict]:
    """Decoded widget states whose family (text before the first '-') matches."""
    ws = envelope.get("widgetStates") if isinstance(envelope, dict) else None
    if not isinstance(ws, dict):
        return []
    out: list[dict] = []
    for key, raw in ws.items():
        if _family(key) != family:
            continue
        obj = _decode(raw)
        if isinstance(obj, dict):
            out.append(obj)
    return out


def _widget(envelope: dict, family: str) -> dict | None:
    found = _widgets(envelope, family)
    return found[0] if found else None


def _tile_items(obj: dict) -> list:
    items = obj.get("items")
    if isinstance(items, list):
        return items
    container = obj.get("productContainer")
    if isinstance(container, dict) and isinstance(container.get("products"), list):
        return container["products"]
    return []


def _tiles(envelope: dict) -> list[dict]:
    out: list[dict] = []
    ws = envelope.get("widgetStates") or {}
    if not isinstance(ws, dict):
        return out
    for key, raw in ws.items():
        if not _TILE_WIDGET_RE.match(str(key)):
            continue
        obj = _decode(raw)
        if not isinstance(obj, dict):
            continue
        for it in _tile_items(obj):
            if not isinstance(it, dict):
                continue
            rec = parse_tile(it)
            if rec.get("sku") or rec.get("name"):
                out.append(rec)
    return out


def _rs_content(node: Any) -> str | None:
    """Join rich-text `content`/`text` fragments. Missing node → None."""
    if isinstance(node, str):
        text = _norm(node)
        return text or None
    if isinstance(node, dict) and isinstance(node.get("text"), str) and "textRs" not in node:
        text = _norm(node["text"])
        return text or None
    items = node
    if isinstance(node, dict):
        items = node.get("textRs")
        if not isinstance(items, list):
            items = node.get("text")
    if not isinstance(items, list):
        return None
    parts: list[str] = []
    for item in items:
        if isinstance(item, str):
            parts.append(item)
        elif isinstance(item, dict) and isinstance(item.get("content"), str):
            parts.append(item["content"])
        elif isinstance(item, dict) and isinstance(item.get("text"), str):
            parts.append(item["text"])
    text = _norm(" ".join(p for p in parts if p))
    return text or None


def _seo_description(seo: Any) -> str | None:
    if not isinstance(seo, dict):
        return None
    for meta in seo.get("meta") or []:
        if isinstance(meta, dict) and meta.get("name") == "description":
            content = meta.get("content")
            return content if isinstance(content, str) else None
    return None


def _sku_from_text(text: str) -> str | None:
    m = re.search(r"-(\d{6,})(?:/|$|\?)", text) or re.search(r"(\d{6,})", text)
    return m.group(1) if m else None


def _product_path(url_or_sku: str) -> str:
    raw = str(url_or_sku).strip()
    if raw.startswith("http://") or raw.startswith("https://") or raw.startswith("/"):
        return _with_slash(_site_path(raw, keep_query=False))
    return f"/product/{raw.strip('/')}/"


def _video_cover(node: Any) -> str | None:
    if isinstance(node, str):
        return node or None
    if not isinstance(node, dict):
        return None
    for key in ("url", "src", "link", "coverUrl", "previewUrl", "videoUrl"):
        if isinstance(node.get(key), str) and node[key]:
            return node[key]
    for value in node.values():
        if isinstance(value, dict):
            for key in ("url", "src", "link"):
                if isinstance(value.get(key), str) and value[key]:
                    return value[key]
    return None


def _price_block(env: dict) -> dict | None:
    chosen = None
    for widget in _widgets(env, "webPrice"):
        if isinstance(widget.get("price"), str):
            chosen = widget
            break
    if chosen is None:
        return None
    price = chosen.get("price")
    original = chosen.get("originalPrice")
    return {
        "price": _norm(price) if isinstance(price, str) else None,
        "original_price": _norm(original) if isinstance(original, str) else None,
        "show_original_price": chosen.get("showOriginalPrice"),
        "is_available": chosen.get("isAvailable"),
        "disclaimer": chosen.get("disclaimerPriceHeader")
        if isinstance(chosen.get("disclaimerPriceHeader"), str) else None,
    }


def _gallery(env: dict) -> dict | None:
    widget = _widget(env, "webGallery")
    if not isinstance(widget, dict):
        return None
    images: list[dict] = []
    raw = widget.get("images")
    if isinstance(raw, list):
        for image in raw:
            if not isinstance(image, dict):
                continue
            src = image.get("src") or image.get("url")
            if isinstance(src, str) and src:
                images.append({"src": src, "alt": image.get("alt")})
    cover = widget.get("coverImage")
    return {
        "cover_image": cover if isinstance(cover, str) else None,
        "images": images,
        "video_cover": _video_cover(widget.get("videoCover")),
    }


def _short_characteristics(env: dict) -> list[dict]:
    widget = _widget(env, "webShortCharacteristics")
    if not isinstance(widget, dict):
        return []
    raw = widget.get("characteristics")
    if not isinstance(raw, list):
        return []
    rows: list[dict] = []
    for row in raw:
        if not isinstance(row, dict):
            continue
        title = row.get("title") if isinstance(row.get("title"), dict) else {}
        hint_node = title.get("hint") if isinstance(title.get("hint"), dict) else {}
        values: list[str] = []
        for value in row.get("values") or []:
            if isinstance(value, dict) and isinstance(value.get("text"), str):
                values.append(value["text"])
            elif isinstance(value, str):
                values.append(value)
        rows.append({
            "id": row.get("id"),
            "name": _rs_content(title.get("textRs")),
            "values": values,
            "hint": _rs_content(hint_node.get("textRs")),
        })
    return rows


def _characteristic_rows(widget: Any) -> list[dict]:
    """Flatten `webCharacteristics.characteristics[].short[]`."""
    if not isinstance(widget, dict):
        return []
    groups = widget.get("characteristics")
    if not isinstance(groups, list):
        return []
    rows: list[dict] = []
    for group in groups:
        if not isinstance(group, dict):
            continue
        short = group.get("short")
        if isinstance(short, list):
            source = short
        elif group.get("name") or group.get("key"):
            source = [group]
        else:
            continue
        for row in source:
            if not isinstance(row, dict):
                continue
            values: list[str] = []
            for value in row.get("values") or []:
                if isinstance(value, dict) and isinstance(value.get("text"), str):
                    values.append(value["text"])
                elif isinstance(value, str):
                    values.append(value)
            rows.append({
                "key": row.get("key"),
                "name": row.get("name"),
                "values": values,
                "copy_text": row.get("copyText") if isinstance(row.get("copyText"), str) else None,
                "hint": row.get("hintText") if isinstance(row.get("hintText"), str) else None,
            })
    return rows


def _brand(env: dict) -> dict | None:
    widget = _widget(env, "webBrand")
    if not isinstance(widget, dict):
        return None
    content = widget.get("content") if isinstance(widget.get("content"), dict) else {}
    title = content.get("title") if isinstance(content.get("title"), dict) else {}
    description = content.get("description") if isinstance(content.get("description"), dict) else {}
    inner = description.get("content") if isinstance(description.get("content"), dict) else {}
    name = _rs_content(title.get("text"))
    link = widget.get("link") if isinstance(widget.get("link"), str) else None
    if not name and not link:
        return None
    return {
        "name": name,
        "url": link,
        "trust": _rs_content(inner.get("text")),
    }


def _seller(env: dict) -> dict | None:
    widget = _widget(env, "webCurrentSeller")
    if not isinstance(widget, dict):
        return None
    cell = widget.get("sellerCell") if isinstance(widget.get("sellerCell"), dict) else {}
    center = cell.get("centerBlock") if isinstance(cell.get("centerBlock"), dict) else {}
    title = center.get("title") if isinstance(center.get("title"), dict) else {}
    name = title.get("text") if isinstance(title.get("text"), str) else None
    common = cell.get("common") if isinstance(cell.get("common"), dict) else {}
    action = common.get("action") if isinstance(common.get("action"), dict) else {}
    url = action.get("link") if isinstance(action.get("link"), str) else None
    rating_w = widget.get("rating") if isinstance(widget.get("rating"), dict) else {}
    rating_title = rating_w.get("title") if isinstance(rating_w.get("title"), dict) else {}
    rating = rating_title.get("text") if isinstance(rating_title.get("text"), str) else None
    factors: list[dict] = []
    for factor in widget.get("trustFactors") or []:
        if not isinstance(factor, dict):
            continue
        ftitle = factor.get("title") if isinstance(factor.get("title"), dict) else {}
        badge = factor.get("badge") if isinstance(factor.get("badge"), dict) else {}
        factors.append({
            "title": ftitle.get("text") if isinstance(ftitle.get("text"), str) else None,
            "badge": badge.get("text") if isinstance(badge.get("text"), str) else None,
        })
    if not name and not url:
        return None
    return {"name": name, "url": url, "rating": rating, "trust_factors": factors}


def _review_score(env: dict) -> dict | None:
    widget = _widget(env, "webReviewProductScore")
    if not isinstance(widget, dict):
        return None
    if widget.get("totalScore") is None and widget.get("reviewsCount") is None:
        return None
    url = widget.get("url") if isinstance(widget.get("url"), str) else None
    if url and not url.startswith("/") and not url.startswith("http"):
        url = "/" + url
    return {
        "total_score": widget.get("totalScore"),
        "reviews_count": widget.get("reviewsCount"),
        "url": url,
    }


def _question_count(env: dict) -> dict | None:
    for widget in _widgets(env, "webQuestionCount"):
        text = widget.get("text") if isinstance(widget.get("text"), str) else None
        link = widget.get("link") if isinstance(widget.get("link"), str) else None
        if not text and not link:
            continue
        count = None
        if text:
            digits = re.sub(r"\D", "", text)
            if digits:
                count = int(digits)
        return {
            "text": text,
            "count": count,
            "url": _site_path(link, keep_query=False) if link else None,
        }
    return None


def _aspects(env: dict) -> list[dict]:
    widget = _widget(env, "webAspects")
    if not isinstance(widget, dict):
        return []
    out: list[dict] = []
    for aspect in widget.get("aspects") or []:
        if not isinstance(aspect, dict):
            continue
        variants: list[dict] = []
        for variant in aspect.get("variants") or []:
            if not isinstance(variant, dict):
                continue
            data = variant.get("data") if isinstance(variant.get("data"), dict) else {}
            text = data.get("searchableText") if isinstance(data.get("searchableText"), str) else None
            if not text:
                text = _rs_content(data.get("textRs"))
            variants.append({
                "sku": variant.get("sku"),
                "link": variant.get("link"),
                "text": text,
                "price": variant.get("price"),
                "active": variant.get("active"),
                "availability": variant.get("availability"),
            })
        out.append({
            "name": aspect.get("aspectName"),
            "key": aspect.get("aspectKey"),
            "type": aspect.get("type"),
            "variants": variants,
        })
    return out


def _strip_query_param(url: str, name: str) -> str:
    """Drop every query parameter named `name`. Other pairs stay as written.

    Values are not re-encoded, so `start_page_id` and similar tokens survive
    byte-for-byte. A `tab` parameter must not be forwarded: it is a scroll
    hint and the response is screen 1 (no description, no characteristics).
    """
    if "?" not in url:
        return url
    base, query = url.split("?", 1)
    fragment = ""
    if "#" in query:
        query, fragment = query.split("#", 1)
        fragment = "#" + fragment
    kept: list[str] = []
    for segment in query.split("&"):
        if not segment:
            continue
        key = unquote(segment.split("=", 1)[0])
        if key == name:
            continue
        kept.append(segment)
    if not kept:
        return base + fragment
    return base + "?" + "&".join(kept) + fragment


def _pdp_next(env: dict, path: str) -> str:
    """Screen-2 URL. Prefer the site's `paginator.nextPage`.

    `layout_page_index` alone is ignored; the container+index pair is enough
    (`start_page_id` is optional). Any `tab` parameter on that URL is removed
    before it is requested — `?tab=` returns screen 1 with no error.
    """
    for widget in _widgets(env, "paginator"):
        nxt = widget.get("nextPage")
        if isinstance(nxt, str) and nxt.strip():
            cleaned = _site_path(nxt.strip(), keep_query=True)
            return _strip_query_param(cleaned, "tab")
    base = _with_slash(_site_path(path, keep_query=False))
    return base + "?" + _PDP_PAGE2_QUERY


def _filter_title(filt: dict) -> str | None:
    if isinstance(filt.get("title"), str):
        return filt["title"]
    for key, value in filt.items():
        if key in ("trackingInfo", "testInfo", "cellTrackingInfo"):
            continue
        if not isinstance(value, dict):
            continue
        title = value.get("title")
        if isinstance(title, str):
            return title
        if isinstance(title, dict) and isinstance(title.get("text"), str):
            return title["text"]
    return None


def _filters(env: dict) -> list[dict]:
    widget = _widget(env, "filtersDesktop")
    if not isinstance(widget, dict):
        return []
    sections = widget.get("sections")
    if not isinstance(sections, list):
        return []
    out: list[dict] = []
    for section in sections:
        if not isinstance(section, dict):
            continue
        filters: list[dict] = []
        raw = section.get("filters")
        if not isinstance(raw, list):
            continue
        for filt in raw:
            if not isinstance(filt, dict):
                continue
            filters.append({
                "type": filt.get("type"),
                "key": filt.get("key"),
                "title": _filter_title(filt),
            })
        if filters:
            title = section.get("title") if isinstance(section.get("title"), str) else None
            out.append({"title": title, "filters": filters})
    return out


def _sort_options(env: dict) -> list[dict]:
    widget = _widget(env, "searchResultsSort")
    if not isinstance(widget, dict):
        return []
    button = widget.get("sortButton") if isinstance(widget.get("sortButton"), dict) else {}
    options = button.get("options")
    if not isinstance(options, list):
        return []
    out: list[dict] = []
    for option in options:
        if not isinstance(option, dict):
            continue
        action = option.get("action") if isinstance(option.get("action"), dict) else {}
        link = action.get("link") if isinstance(action.get("link"), str) else None
        out.append({
            "name": option.get("name"),
            "link": link,
            "is_selected": bool(option.get("isSelected")),
        })
    return out


def _active_filters(env: dict) -> list[dict]:
    widget = _widget(env, "searchResultsFiltersActive")
    if not isinstance(widget, dict):
        return []
    raw = widget.get("activeFilters")
    if not isinstance(raw, list):
        return []
    out: list[dict] = []
    for filt in raw:
        if not isinstance(filt, dict):
            continue
        values: list[dict] = []
        for value in filt.get("activeValues") or []:
            if not isinstance(value, dict):
                continue
            values.append({
                "title": value.get("title"),
                "disable_uri": value.get("disableUri"),
            })
        out.append({
            "key": filt.get("key"),
            "name": filt.get("name"),
            "ftype": filt.get("ftype"),
            "values": values,
        })
    return out


def _next_url(env: dict) -> str | None:
    for widget in _widgets(env, "infiniteVirtualPaginator"):
        nxt = widget.get("nextPage")
        if isinstance(nxt, str) and nxt.strip():
            return _site_path(nxt.strip(), keep_query=True)
    return None


def _listing_extras(env: dict) -> dict:
    return {
        "filters": _filters(env),
        "sort_options": _sort_options(env),
        "active_filters": _active_filters(env),
        "next_url": _next_url(env),
    }


def search(client, query: str, page: int = 1, *,
           sorting: str | None = None, filters: dict | None = None) -> dict:
    """Search the catalogue. Pagination uses `page=N` (verified live).

    `sorting` is a `searchResultsSort` value (`score`, `new`, `price`,
    `price_desc`, `rating`, `discount`). `filters` are extra GET query
    pairs (`{"is_promo": "t"}`). Nothing here is POSTed.
    """
    params: dict[str, Any] = {"text": query, "from_global": "true"}
    if page > 1:
        params["page"] = page
    if sorting:
        params["sorting"] = sorting
    for key, value in (filters or {}).items():
        if value is not None and str(key) not in params:
            params[str(key)] = value
    env = _page_url(client, "/search/", **params)
    if not isinstance(env, dict):
        raise ParseError("search: envelope is not an object")
    out = {
        "query": query,
        "page": page,
        "seo": (env.get("seo") or {}).get("title"),
        "location": (env.get("location") or {}).get("current"),
        "pageInfo": env.get("pageInfo"),
        "products": _tiles(env),
        "widget_count": len(env.get("widgetStates") or {}),
    }
    out.update(_listing_extras(env))
    return out


def product(client, url_or_sku: str) -> dict:
    """Product card. Accepts an SKU, a slug, or a /product/... URL.

    Screen 1 carries price, heading, gallery, short specs, brand, seller,
    score and question count. Description HTML and the full characteristic
    table are on layout page 2: one follow of `paginator.nextPage` (or the
    equivalent `layout_container=pdpPage2column&layout_page_index=2` URL).
    A failure of that second fetch leaves `description_html` and
    `characteristics` as None and does not raise. `?tab=` is never sent.
    """
    path = _product_path(url_or_sku)
    env = _page_url(client, path, __rr="1")
    if not isinstance(env, dict):
        raise ParseError("product: envelope is not an object")
    seo = env.get("seo") if isinstance(env.get("seo"), dict) else {}
    detail = _widget(env, "webDetailSKU") or {}
    sku = detail.get("copyText") if isinstance(detail.get("copyText"), str) else None
    if not sku:
        info = env.get("pageInfo") if isinstance(env.get("pageInfo"), dict) else {}
        analytics = info.get("analyticsInfo") if isinstance(info.get("analyticsInfo"), dict) else {}
        if analytics.get("sku") is not None:
            sku = str(analytics["sku"])
        else:
            sku = _sku_from_text(path)
    heading_w = _widget(env, "webProductHeading") or {}
    heading = heading_w.get("title") if isinstance(heading_w.get("title"), str) else None

    description_html = None
    characteristics = None
    nxt = _pdp_next(env, path)
    if nxt:
        try:
            env2 = _page_url(client, nxt)
        except Exception:
            env2 = None
        if isinstance(env2, dict):
            desc = _widget(env2, "webDescription") or {}
            rich = desc.get("richAnnotation")
            description_html = rich if isinstance(rich, str) else None
            characteristics = _characteristic_rows(_widget(env2, "webCharacteristics"))

    location = None
    if isinstance(env.get("location"), dict):
        location = env["location"].get("current")
    price = _price_block(env)
    gallery = _gallery(env)
    seller = _seller(env)
    review_score = _review_score(env)
    return {
        "sku": sku,
        "seo": seo.get("title"),
        "title": seo.get("title"),
        "heading": heading,
        "description": _seo_description(seo),
        "description_html": description_html,
        "price": price,
        "original_price": price.get("original_price") if isinstance(price, dict) else None,
        "gallery": gallery,
        "gallery_images": gallery.get("images") if isinstance(gallery, dict) else None,
        "short_characteristics": _short_characteristics(env),
        "characteristics": characteristics,
        "brand": _brand(env),
        "seller": seller,
        "seller_rating": seller.get("rating") if isinstance(seller, dict) else None,
        "review_score": review_score,
        "reviews_count": review_score.get("reviews_count") if isinstance(review_score, dict) else None,
        "question_count": _question_count(env),
        "aspects": _aspects(env),
        "location": location,
        "tiles": _tiles(env),
        "widget_count": len(env.get("widgetStates") or {}),
        "pageInfo": env.get("pageInfo"),
    }


def category(client, slug: str, page: int = 1, *,
             sorting: str | None = None, filters: dict | None = None) -> dict:
    """Category listing, e.g. 'elektronika-15500'.

    `sorting` and `filters` match `search` (`sorting=price`, `is_promo=t`).
    """
    params: dict[str, Any] = {}
    if page > 1:
        params["page"] = page
    if sorting:
        params["sorting"] = sorting
    for key, value in (filters or {}).items():
        if value is not None and str(key) not in params:
            params[str(key)] = value
    env = _page_url(client, f"/category/{slug}/", **params)
    if not isinstance(env, dict):
        raise ParseError("category: envelope is not an object")
    out = {
        "category": slug,
        "seo": (env.get("seo") or {}).get("title"),
        "products": _tiles(env),
        "widget_count": len(env.get("widgetStates") or {}),
        "pageInfo": env.get("pageInfo"),
    }
    out.update(_listing_extras(env))
    return out


def _review_paths(sku_or_url: str) -> tuple[list[str], str]:
    """Paths to try. Canonical PDP reviews carry `sortings`; `/reviews/<sku>/` is the fallback."""
    raw = str(sku_or_url).strip()
    label = raw
    found = re.search(r"(\d{6,})", raw)
    if found:
        label = found.group(1)
    if raw.startswith("http://") or raw.startswith("https://") or raw.startswith("/"):
        path = _site_path(raw, keep_query=False).rstrip("/")
        if path.endswith("/reviews") or re.search(r"/reviews/\d+$", path):
            return [_with_slash(path)], label
        if "/product/" in path:
            return [_with_slash(path + "/reviews")], label
        return [_with_slash(path)], label
    token = raw.strip("/")
    if token.isdigit():
        return [f"/product/{token}/reviews/", f"/reviews/{token}/"], token
    return [f"/product/{token}/reviews/"], label


def _review_sorts(raw: Any) -> list[dict]:
    if not isinstance(raw, list):
        return []
    out: list[dict] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        if "value" not in item and "name" not in item:
            continue
        out.append({
            "name": item.get("name"),
            "value": item.get("value"),
            "active": bool(item.get("active")),
        })
    return out


def _media_list(raw: Any) -> list[dict]:
    if not isinstance(raw, list):
        return []
    out: list[dict] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        url = item.get("url") or item.get("link") or item.get("src")
        out.append({
            "url": url if isinstance(url, str) else None,
            "width": item.get("width"),
            "height": item.get("height"),
            "uuid": item.get("UUID") or item.get("uuid"),
        })
    return out


def _usefulness(raw: Any) -> dict | None:
    if not isinstance(raw, dict):
        return None
    return {
        "useful": raw.get("useful"),
        "unuseful": raw.get("unuseful"),
        "userSelection": raw.get("userSelection"),
    }


def _author_name(author: Any) -> str | None:
    if not isinstance(author, dict):
        return None
    first = author.get("firstName") or author.get("fio") or ""
    last = author.get("lastName") or ""
    if not isinstance(first, str):
        first = ""
    if not isinstance(last, str):
        last = ""
    return f"{first} {last}".strip() or None


def reviews(client, sku: str, page: int = 1, sort: str | None = None) -> dict:
    """Product reviews.

    `sort` is a `webListReviews.sortings[].value` (`usefulness_desc`,
    `score_desc`, `score_asc`). A numeric SKU is requested at
    `/product/<sku>/reviews/` (where those sortings are published) and, on
    404 only, at the legacy `/reviews/<sku>/` path. `?tab=` is not used.
    """
    paths, label = _review_paths(str(sku))
    params: dict[str, Any] = {}
    if page > 1:
        params["page"] = page      # `layout_page_index` is ignored here
    if sort:
        params["sort"] = sort
    env = None
    for index, path in enumerate(paths):
        try:
            env = _page_url(client, path, **params)
            break
        except NotFound:
            if index == len(paths) - 1:
                raise
    if not isinstance(env, dict):
        raise ParseError("reviews: envelope is not an object")
    ws = env.get("widgetStates") or {}
    items: list[dict] = []
    paging: dict[str, Any] = {}
    total = None
    score = None
    sortings: list[dict] = []

    for _key, raw in (ws.items() if isinstance(ws, dict) else []):
        obj = _decode(raw)
        if not isinstance(obj, dict):
            continue
        if not sortings:
            parsed_sorts = _review_sorts(obj.get("sortings"))
            if parsed_sorts:
                sortings = parsed_sorts
        # the list widget carries a real `reviews` array
        revs = obj.get("reviews")
        if isinstance(revs, list) and revs:
            for rv in revs:
                if not isinstance(rv, dict):
                    continue
                content = rv.get("content")
                if isinstance(content, dict):
                    text = content.get("text") or content.get("comment")
                    title = content.get("title")
                    rating = content.get("rating") or content.get("score")
                    positive = content.get("positive")
                    negative = content.get("negative")
                    photos = _media_list(content.get("photos"))
                    videos = _media_list(content.get("videos"))
                else:
                    text = content if isinstance(content, str) else None
                    title = rv.get("title")
                    rating = rv.get("rating") or rv.get("score")
                    positive = None
                    negative = None
                    photos = []
                    videos = []
                status = rv.get("status")
                if isinstance(status, dict):
                    status = status.get("name")
                comments = rv.get("comments") if isinstance(rv.get("comments"), dict) else {}
                edited = rv.get("isEdited")
                items.append({
                    "uuid": rv.get("uuid"),
                    "author": _author_name(rv.get("author")),
                    "published_at": rv.get("publishedAt") or rv.get("createdAt"),
                    "rating": rating,
                    "title": title,
                    "text": text,
                    "positive": positive,
                    "negative": negative,
                    "photos": photos,
                    "videos": videos,
                    "usefulness": _usefulness(rv.get("usefulness")),
                    "comments_count": comments.get("totalCount") if isinstance(comments, dict) else None,
                    "itemId": rv.get("itemId"),
                    "status": status,
                    "is_edited": edited if isinstance(edited, bool) else None,
                })
            ps = obj.get("productScore")
            if isinstance(ps, (int, float)):
                score = ps
            elif isinstance(ps, dict):
                score = ps.get("score") or ps.get("value")
            pg = obj.get("paging")
            if isinstance(pg, dict):
                paging["page"] = pg.get("page")
                paging["per_page"] = pg.get("perPage")
                paging["has_next"] = bool(pg.get("nextButton"))
                if total is None and isinstance(pg.get("total"), int):
                    total = pg["total"]
        if isinstance(obj.get("reviewsTotal"), int) and total is None:
            total = obj["reviewsTotal"]

    active = next((item.get("value") for item in sortings if item.get("active")), None)
    return {
        "sku": label,
        "seo": (env.get("seo") or {}).get("title"),
        "total": total,
        "score": score,
        "sort": sort or active,
        "sortings": sortings,
        "paging": paging,
        "reviews": items,
        "widget_count": len(ws) if isinstance(ws, dict) else 0,
    }


class _HTMLText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self._parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self._parts.append(data)

    def text(self) -> str:
        return "".join(self._parts)


def _strip_html(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    parser = _HTMLText()
    try:
        parser.feed(value)
        parser.close()
        text = parser.text()
    except Exception:
        text = re.sub(r"<[^>]+>", "", value)
    text = _norm(html.unescape(text))
    return text or None


def _reactions(raw: Any) -> list[dict]:
    """Read-only reaction labels. Action links (voteQuestionV2) are dropped."""
    if not isinstance(raw, list):
        return []
    out: list[dict] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        out.append({
            "title": item.get("title") if isinstance(item.get("title"), str) else None,
            "icon": item.get("icon") if isinstance(item.get("icon"), str) else None,
        })
    return out


def _question_author(node: Any) -> str | None:
    if not isinstance(node, dict):
        return None
    name = node.get("name")
    if isinstance(name, dict) and isinstance(name.get("text"), str):
        return name["text"]
    if isinstance(name, str):
        return name
    return None


def _question_when(node: Any) -> str | None:
    if isinstance(node, dict) and isinstance(node.get("text"), str):
        return node["text"]
    if isinstance(node, str):
        return node
    return None


def _question_text(node: Any) -> tuple[str | None, str | None]:
    raw = None
    if isinstance(node, dict):
        raw = node.get("text")
    elif isinstance(node, str):
        raw = node
    if not isinstance(raw, str):
        return None, None
    return _strip_html(raw), raw


def _question_product(products: Any, item_id: Any) -> dict | None:
    if not isinstance(products, dict) or item_id is None:
        return None
    prod = products.get(str(item_id))
    if prod is None:
        prod = products.get(item_id)
    if not isinstance(prod, dict):
        return None
    name = prod.get("name")
    if isinstance(name, dict):
        name = name.get("text")
    image = prod.get("coverImage")
    if isinstance(image, dict):
        image = image.get("image") or image.get("src")
    return {
        "name": name if isinstance(name, str) else None,
        "url": prod.get("url") if isinstance(prod.get("url"), str) else None,
        "image": image if isinstance(image, str) else None,
    }


def _question_sortings(sorting: Any) -> list[dict]:
    if not isinstance(sorting, dict):
        return []
    options = sorting.get("options")
    if not isinstance(options, list):
        return []
    out: list[dict] = []
    for option in options:
        if not isinstance(option, dict):
            continue
        title = option.get("title")
        if isinstance(title, dict):
            title = title.get("text")
        url = option.get("url")
        if isinstance(url, str):
            url = unquote(url)
        out.append({
            "title": title if isinstance(title, str) else None,
            "value": option.get("value"),
            "url": url if isinstance(url, str) else None,
        })
    return out


def _tab_counter(env: dict, suffix: str) -> int | None:
    widget = _widget(env, "webProductTabs")
    if not isinstance(widget, dict):
        return None
    tabs = widget.get("tabs")
    if not isinstance(tabs, list):
        return None
    for tab in tabs:
        if not isinstance(tab, dict):
            continue
        value = str(tab.get("value") or "")
        if not value.rstrip("/").endswith(suffix):
            continue
        counter = tab.get("counter")
        if isinstance(counter, int):
            return counter
        if isinstance(counter, str):
            digits = re.sub(r"\D", "", counter)
            if digits:
                return int(digits)
    return None


def _canonical_hrefs(seo: Any) -> list[str]:
    if not isinstance(seo, dict) or not isinstance(seo.get("link"), list):
        return []
    canonical: list[str] = []
    others: list[str] = []
    for link in seo["link"]:
        if not isinstance(link, dict) or not isinstance(link.get("href"), str):
            continue
        if link.get("rel") == "canonical":
            canonical.append(link["href"])
        else:
            others.append(link["href"])
    return canonical + others


def _questions_from_sku(client, sku: str) -> str:
    """Resolve a bare SKU to `/product/<slug>/questions/` via the product page."""
    try:
        env = _page_url(client, f"/product/{sku}/", __rr="1")
    except NotFound:
        return f"/product/{sku}/questions/"
    if not isinstance(env, dict):
        return f"/product/{sku}/questions/"
    for widget in _widgets(env, "webQuestionCount"):
        link = widget.get("link")
        if isinstance(link, str) and "questions" in link:
            return _with_slash(_site_path(link, keep_query=False))
    info = env.get("pageInfo") if isinstance(env.get("pageInfo"), dict) else {}
    url = info.get("url")
    if isinstance(url, str) and "/product/" in url:
        base = _site_path(url, keep_query=False).rstrip("/")
        return _with_slash(base + "/questions")
    for href in _canonical_hrefs(env.get("seo")):
        if "/product/" in href:
            base = _site_path(href, keep_query=False).rstrip("/")
            return _with_slash(base + "/questions")
    return f"/product/{sku}/questions/"


def _questions_path(client, sku_or_url: str) -> tuple[str, str | None]:
    raw = str(sku_or_url).strip()
    sku = _sku_from_text(raw)
    if raw.startswith("http://") or raw.startswith("https://") or raw.startswith("/") or "/" in raw:
        path = _site_path(raw, keep_query=False).rstrip("/")
        if path.endswith("/questions"):
            return _with_slash(path), sku
        if "/product/" in path:
            return _with_slash(path + "/questions"), sku
        return _with_slash(path), sku
    token = raw.strip("/")
    if token.isdigit():
        return _questions_from_sku(client, token), token
    return f"/product/{token}/questions/", sku


def _parse_answer(raw: Any) -> dict | None:
    if not isinstance(raw, dict):
        return None
    text, text_html = _question_text(raw.get("text"))
    return {
        "uuid": raw.get("answerUuid"),
        "author": _question_author(raw.get("author")),
        "created_at": _question_when(raw.get("createdAt")),
        "text": text,
        "text_html": text_html,
        "reactions": _reactions(raw.get("reactions")),
    }


def questions(client, sku_or_url: str, qsort: str | None = None,
              cursor: str | None = None) -> dict:
    """Questions for a product (`webPDPListQuestions` only).

    Accepts a SKU (the slug is resolved from the product page), a product
    slug, or a product / questions URL. `qsort` is one of
    `created_at_desc`, `usefulness_desc`, `has_answers_desc`,
    `has_answers_asc`. Further pages are not `?page=N`; pass `cursor` as
    the previous response's `next_url` (`paginator.nextPage`, which carries
    `page_key`). Question and answer HTML is kept on `text_html` and also
    returned as plain `text`. This never calls `createQuestionV2` or
    `voteQuestionV2`.
    """
    if cursor:
        path = _site_path(str(cursor).strip(), keep_query=True)
        sku = _sku_from_text(path)
        env = _page_url(client, path)
    else:
        path, sku = _questions_path(client, sku_or_url)
        params: dict[str, Any] = {}
        if qsort:
            params["qsort"] = qsort
        env = _page_url(client, path, **params)
    if not isinstance(env, dict):
        raise ParseError("questions: envelope is not an object")
    widget = _widget(env, "webPDPListQuestions") or {}
    products = widget.get("products") if isinstance(widget.get("products"), dict) else {}
    parsed: list[dict] = []
    raw_questions = widget.get("questions")
    if isinstance(raw_questions, list):
        for question in raw_questions:
            if not isinstance(question, dict):
                continue
            text, text_html = _question_text(question.get("text"))
            answers: list[dict] = []
            for answer in question.get("answers") or []:
                parsed_answer = _parse_answer(answer)
                if parsed_answer is not None:
                    answers.append(parsed_answer)
            parsed.append({
                "uuid": question.get("questionUuid"),
                "item_id": question.get("itemId"),
                "author": _question_author(question.get("author")),
                "created_at": _question_when(question.get("createdAt")),
                "text": text,
                "text_html": text_html,
                "answers": answers,
                "reactions": _reactions(question.get("reactions")),
                "product": _question_product(products, question.get("itemId")),
            })
    sortings = _question_sortings(widget.get("sorting"))
    active = None
    sorting = widget.get("sorting")
    if isinstance(sorting, dict) and isinstance(sorting.get("value"), str):
        active = sorting["value"]
    info = env.get("pageInfo") if isinstance(env.get("pageInfo"), dict) else {}
    analytics = info.get("analyticsInfo") if isinstance(info.get("analyticsInfo"), dict) else {}
    if analytics.get("sku") is not None:
        sku = str(analytics["sku"])
    ws = env.get("widgetStates") or {}
    return {
        "sku": sku,
        "qsort": (active if cursor else (qsort or active)),
        "questions": parsed,
        "sortings": sortings,
        "total": _tab_counter(env, "/questions"),
        "n": len(parsed),
        "next_url": _paginator_next(env),
        "pageInfo": env.get("pageInfo"),
        "widget_count": len(ws) if isinstance(ws, dict) else 0,
    }


def _paginator_next(env: dict) -> str | None:
    """`paginator.nextPage` (questions, PDP slices). Not the listing scroller."""
    for widget in _widgets(env, "paginator"):
        nxt = widget.get("nextPage")
        if isinstance(nxt, str) and nxt.strip():
            return _strip_query_param(_site_path(nxt.strip(), keep_query=True), "tab")
    return None


def decode_envelope(env: dict) -> dict:
    """Double-decode `widgetStates`. Drop tokens and tracking chrome.

    Kept top-level keys are `layout`, `widgetStates`, `seo`, `pageInfo`,
    `location`. `userToken`, `pageToken`, `requestID` and the rest stay out.
    """
    if not isinstance(env, dict):
        raise ParseError("page: envelope is not an object")
    raw_states = env.get("widgetStates") if isinstance(env.get("widgetStates"), dict) else {}
    states: dict[str, Any] = {}
    for key, raw in raw_states.items():
        decoded = _decode(raw)
        states[str(key)] = decoded if decoded is not None else None
    return {
        "layout": env.get("layout"),
        "widgetStates": states,
        "seo": env.get("seo"),
        "pageInfo": env.get("pageInfo"),
        "location": env.get("location"),
    }


def page(client, url: str) -> dict:
    """Any public site URL through the entrypoint renderer.

    `url` may be a host-relative path (`/brand/apple-26303000/`) or an
    absolute `https://ozon.by/...` URL. The host is ignored; the request
    always goes to `client.base` as GET.
    """
    target = str(url).strip()
    if not target:
        raise ParseError("page: empty url")
    env = _page_url(client, target)
    return decode_envelope(env)


def _sku_of(env: dict, fallback: str | None = None) -> str | None:
    info = env.get("pageInfo") if isinstance(env.get("pageInfo"), dict) else {}
    analytics = info.get("analyticsInfo") if isinstance(info.get("analyticsInfo"), dict) else {}
    if analytics.get("sku") is not None:
        return str(analytics["sku"])
    detail = _widget(env, "webDetailSKU") or {}
    copy = detail.get("copyText")
    if isinstance(copy, str) and copy.strip():
        return copy.strip()
    main = _widget(env, "webProductMainWidget") or {}
    if main.get("sku") is not None:
        return str(main["sku"])
    return fallback


def _tab_path(url_or_sku: str, tab: str) -> str:
    path = _product_path(url_or_sku).rstrip("/")
    suffix = "/" + tab.strip("/")
    if not path.endswith(suffix):
        path += suffix
    return _with_slash(path)


def _text_of(node: Any) -> str | None:
    if isinstance(node, str):
        text = _norm(node)
        return text or None
    if isinstance(node, dict):
        if isinstance(node.get("text"), str):
            text = _norm(node["text"])
            return text or None
        return _rs_content(node.get("textRs"))
    return None


def _badge_texts(raw: Any) -> list[str]:
    if not isinstance(raw, list):
        return []
    out: list[str] = []
    for badge in raw:
        if not isinstance(badge, dict):
            continue
        text = badge.get("text")
        if isinstance(text, str) and text.strip():
            out.append(_norm(text))
    return out


def _share_url(env: dict) -> str | None:
    widget = _widget(env, "sharingLink")
    if not isinstance(widget, dict):
        return None
    cells = widget.get("cells")
    if not isinstance(cells, list):
        return None
    fallback = None
    for cell in cells:
        if not isinstance(cell, dict):
            continue
        common = cell.get("common") if isinstance(cell.get("common"), dict) else {}
        action = common.get("action") if isinstance(common.get("action"), dict) else {}
        link = action.get("link")
        if not isinstance(link, str) or not link:
            continue
        if action.get("id") == "copy_link":
            return link
        if fallback is None:
            fallback = link
    return fallback


def _shop_header(env: dict) -> dict | None:
    widget = _widget(env, "sellerTransparency")
    if not isinstance(widget, dict):
        return None
    logo = widget.get("logoImage") if isinstance(widget.get("logoImage"), dict) else {}
    image = logo.get("backgroundImage")
    name = _text_of(widget.get("title"))
    if not name and not image:
        return None
    return {
        "name": name,
        "logo": image if isinstance(image, str) else None,
        "badges": _badge_texts(widget.get("badges")),
        "share_url": _share_url(env),
    }


def _results_header(env: dict) -> dict | None:
    widget = _widget(env, "resultsHeader")
    if not isinstance(widget, dict):
        return None
    title = widget.get("title") if isinstance(widget.get("title"), str) else None
    subtitle = widget.get("subtitle") if isinstance(widget.get("subtitle"), str) else None
    if not title and not subtitle:
        return None
    return {"title": title, "subtitle": subtitle or None}


def _editorial_links(env: dict) -> list[dict]:
    """Subcategory / brand strips that are not product tiles."""
    out: list[dict] = []
    seen: set[str] = set()
    for family in ("horizontalCategoryMenu", "objectLine", "objectThumbnailList", "objectBannerList"):
        for widget in _widgets(env, family):
            items = widget.get("items")
            if not isinstance(items, list):
                continue
            for item in items:
                if not isinstance(item, dict):
                    continue
                title = _text_of(item.get("title")) or _text_of(item.get("name"))
                link = item.get("link") or item.get("url")
                if not isinstance(link, str) or not link:
                    continue
                if link in seen:
                    continue
                seen.add(link)
                image = item.get("image") if isinstance(item.get("image"), str) else None
                out.append({
                    "title": title,
                    "url": link,
                    "image": image,
                    "source": family,
                })
    return out


def _listing_query(page: int, sorting: str | None, filters: dict | None) -> dict[str, Any]:
    params: dict[str, Any] = {}
    if page > 1:
        params["page"] = page
    if sorting:
        params["sorting"] = sorting
    for key, value in (filters or {}).items():
        if value is not None and str(key) not in params:
            params[str(key)] = value
    return params


def _require_env(env: Any, what: str) -> dict:
    if not isinstance(env, dict):
        raise ParseError(f"{what}: envelope is not an object")
    return env


def listing(client, path: str, *, kind: str, slug: str | None = None,
            page: int = 1, sorting: str | None = None,
            filters: dict | None = None) -> dict:
    """Tile listing shared by brand, seller and highlight pages.

    Same controls as a category: `page`, `sorting`, and GET `filters`.
    """
    target = _site_path(str(path).strip(), keep_query=False)
    target = _with_slash(target)
    env = _require_env(
        _page_url(client, target, **_listing_query(page, sorting, filters)),
        kind,
    )
    info = env.get("pageInfo") if isinstance(env.get("pageInfo"), dict) else {}
    seo = env.get("seo") if isinstance(env.get("seo"), dict) else {}
    extras = _listing_extras(env)
    if not extras.get("next_url"):
        extras["next_url"] = _paginator_next(env)
    out = {
        "kind": kind,
        "slug": slug,
        "path": target,
        "page": page,
        "sorting": sorting,
        "seo": seo.get("title"),
        "page_type": info.get("pageType"),
        "url": info.get("url"),
        "header": _shop_header(env),
        "results": _results_header(env),
        "products": _tiles(env),
        "links": _editorial_links(env),
        "widget_count": len(env.get("widgetStates") or {}),
        "pageInfo": env.get("pageInfo"),
    }
    out.update(extras)
    return out


def _slug_path(prefix: str, slug: str) -> str:
    token = str(slug).strip()
    if token.startswith("http://") or token.startswith("https://") or token.startswith("/"):
        return _with_slash(_site_path(token, keep_query=False))
    return f"/{prefix.strip('/')}/{token.strip('/')}/"


def brand(client, slug: str, page: int = 1, *,
          sorting: str | None = None, filters: dict | None = None) -> dict:
    """Brand listing, e.g. `apple-26303000`. Not the `/brand/` directory."""
    return listing(
        client, _slug_path("brand", slug), kind="brand", slug=str(slug).strip("/"),
        page=page, sorting=sorting, filters=filters,
    )


def seller(client, slug: str, page: int = 1, *,
           sorting: str | None = None, filters: dict | None = None) -> dict:
    """Seller shop, e.g. `ozon` or `mvideo-1865500`. Not the `/seller/` index."""
    return listing(
        client, _slug_path("seller", slug), kind="seller", slug=str(slug).strip("/"),
        page=page, sorting=sorting, filters=filters,
    )


def highlight(client, slug: str, page: int = 1, *,
              sorting: str | None = None, filters: dict | None = None) -> dict:
    """Highlight (promo) listing, e.g. `apple-4442805`. `/highlight/` itself 404s."""
    return listing(
        client, _slug_path("highlight", slug), kind="highlight", slug=str(slug).strip("/"),
        page=page, sorting=sorting, filters=filters,
    )


def brands(client) -> dict:
    """Brand directory (`/brand/`). Groups are alphabetical, not product tiles."""
    env = _require_env(_page_url(client, "/brand/"), "brands")
    widget = _widget(env, "brandListResults") or {}
    groups: list[dict] = []
    raw_items = widget.get("items")
    if isinstance(raw_items, list):
        for item in raw_items:
            if not isinstance(item, dict):
                continue
            brands_out: list[dict] = []
            raw_brands = item.get("brands")
            if isinstance(raw_brands, list):
                for brand_row in raw_brands:
                    if not isinstance(brand_row, dict):
                        continue
                    title = brand_row.get("title")
                    link = brand_row.get("link")
                    if not isinstance(title, str) and not isinstance(link, str):
                        continue
                    brands_out.append({
                        "title": title if isinstance(title, str) else None,
                        "url": link if isinstance(link, str) else None,
                    })
            groups.append({
                "name": item.get("name") if isinstance(item.get("name"), str) else None,
                "url": item.get("link") if isinstance(item.get("link"), str) else None,
                "brands": brands_out,
            })
    seo = env.get("seo") if isinstance(env.get("seo"), dict) else {}
    info = env.get("pageInfo") if isinstance(env.get("pageInfo"), dict) else {}
    return {
        "seo": seo.get("title"),
        "page_type": info.get("pageType"),
        "groups": groups,
        "n_groups": len(groups),
        "n_brands": sum(len(group["brands"]) for group in groups),
        "links": _editorial_links(env),
        "pageInfo": env.get("pageInfo"),
        "widget_count": len(env.get("widgetStates") or {}),
    }


def _mall_shops(env: dict) -> list[dict]:
    out: list[dict] = []
    for widget in _widgets(env, "mallFeed"):
        cards = widget.get("cards")
        if not isinstance(cards, list):
            continue
        for card in cards:
            if not isinstance(card, dict):
                continue
            header = card.get("header") if isinstance(card.get("header"), dict) else {}
            logo = header.get("logoImage") if isinstance(header.get("logoImage"), dict) else {}
            image = logo.get("backgroundImage")
            action = header.get("action") if isinstance(header.get("action"), dict) else {}
            link = action.get("link") if isinstance(action.get("link"), str) else None
            goods_node = card.get("goods") if isinstance(card.get("goods"), dict) else {}
            goods: list[dict] = []
            raw_goods = goods_node.get("items")
            if isinstance(raw_goods, list):
                for item in raw_goods:
                    if not isinstance(item, dict):
                        continue
                    rec = parse_tile(item)
                    if rec.get("sku") or rec.get("name") or rec.get("url"):
                        goods.append(rec)
            out.append({
                "name": _text_of(header.get("title")),
                "url": link,
                "logo": image if isinstance(image, str) else None,
                "badges": _badge_texts(header.get("badges")),
                "products": goods,
            })
    return out


def sellers(client, cursor: str | None = None) -> dict:
    """Seller directory (`/seller/`). The next scroll is `cursor`=`next_url`.

    Shop cards are `mallFeed`. This is not a logged-in favourites list.
    """
    path = _site_path(str(cursor).strip(), keep_query=True) if cursor else "/seller/"
    env = _require_env(_page_url(client, path), "sellers")
    seo = env.get("seo") if isinstance(env.get("seo"), dict) else {}
    info = env.get("pageInfo") if isinstance(env.get("pageInfo"), dict) else {}
    shops = _mall_shops(env)
    return {
        "seo": seo.get("title"),
        "page_type": info.get("pageType"),
        "url": info.get("url"),
        "shops": shops,
        "n": len(shops),
        "next_url": _paginator_next(env) or _next_url(env),
        "pageInfo": env.get("pageInfo"),
        "widget_count": len(env.get("widgetStates") or {}),
    }


def similar(client, url_or_sku: str) -> dict:
    """Similar-items modal (`/modal/similar-products?product_id=`).

    The payload's first tab is the analogs grid. The second tab title
    ("Похожие по фото") has no separate URL in the widget, so it is listed
    but not fetched. Bottom shelves are a different layout slice; use
    `page()` with `layout_container=BottomShelfs` when a parent paginator
    published that URL.
    """
    raw = str(url_or_sku).strip()
    sku = _sku_from_text(raw) or raw.strip("/")
    if not sku or not sku.isdigit():
        raise ParseError("similar: need a numeric SKU or a product URL containing one")
    env = _require_env(
        _page_url(client, f"/modal/similar-products?product_id={sku}"),
        "similar",
    )
    tabs_w = _widget(env, "webMobTabs") or {}
    tabs: list[str] = []
    for tab in tabs_w.get("tabs") or []:
        if isinstance(tab, dict) and isinstance(tab.get("title"), str):
            tabs.append(tab["title"])
    params = tabs_w.get("params") if isinstance(tabs_w.get("params"), dict) else {}
    info = env.get("pageInfo") if isinstance(env.get("pageInfo"), dict) else {}
    products = _tiles(env)
    return {
        "sku": sku,
        "tabs": tabs,
        "active_index": params.get("activeIndex"),
        "products": products,
        "n": len(products),
        "next_url": _paginator_next(env),
        "page_type": info.get("pageType"),
        "pageInfo": env.get("pageInfo"),
        "widget_count": len(env.get("widgetStates") or {}),
    }


def _gallery_media(raw: Any) -> list[dict]:
    if not isinstance(raw, list):
        return []
    out: list[dict] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        size = item.get("size") if isinstance(item.get("size"), dict) else {}
        author = item.get("author") if isinstance(item.get("author"), dict) else {}
        name = author.get("name") if isinstance(author.get("name"), str) else None
        out.append({
            "type": item.get("type") if isinstance(item.get("type"), str) else None,
            "url": item.get("url") if isinstance(item.get("url"), str) else None,
            "alt": item.get("alt") if isinstance(item.get("alt"), str) else None,
            "rating": item.get("rating"),
            "uuid": item.get("uuid") if isinstance(item.get("uuid"), str) else None,
            "review_uuid": item.get("reviewUuid") if isinstance(item.get("reviewUuid"), str) else None,
            "author": name,
            "width": size.get("width"),
            "height": size.get("height"),
        })
    return out


def media(client, url_or_sku: str) -> dict:
    """Review photo/video tab (`/product/<slug>/videos/`, `webReviewGallery`).

    Paging fields are `total` / `page` (`rgPage`) / `per_page`. This SKU's
    gallery fits on one page (14 items, per_page 15). A query name for
    page 2 is not proven, so this method does not invent one — follow
    `next_url` when the paginator publishes it.
    """
    path = _tab_path(url_or_sku, "videos")
    env = _require_env(_page_url(client, path), "media")
    widget = _widget(env, "webReviewGallery") or {}
    paging = widget.get("paging") if isinstance(widget.get("paging"), dict) else {}
    info = env.get("pageInfo") if isinstance(env.get("pageInfo"), dict) else {}
    seo = env.get("seo") if isinstance(env.get("seo"), dict) else {}
    items = _gallery_media(widget.get("media"))
    return {
        "sku": _sku_of(env, _sku_from_text(path)),
        "seo": seo.get("title"),
        "total": paging.get("total"),
        "page": paging.get("rgPage"),
        "per_page": paging.get("perPage"),
        "media": items,
        "n": len(items),
        "next_url": _paginator_next(env),
        "page_type": info.get("pageType"),
        "pageInfo": env.get("pageInfo"),
        "widget_count": len(env.get("widgetStates") or {}),
    }


def features(client, url_or_sku: str) -> dict:
    """Full characteristic table from `/product/<slug>/features/`.

    One GET. `product()` already loads the same rows from layout page 2;
    this is the public tab URL and does not fetch the rest of the card.
    """
    path = _tab_path(url_or_sku, "features")
    env = _require_env(_page_url(client, path), "features")
    widget = _widget(env, "webCharacteristics") or {}
    rows = _characteristic_rows(widget)
    total = widget.get("totalCount")
    if not isinstance(total, int):
        total = len(rows)
    price = _price_block(env)
    seo = env.get("seo") if isinstance(env.get("seo"), dict) else {}
    info = env.get("pageInfo") if isinstance(env.get("pageInfo"), dict) else {}
    return {
        "sku": _sku_of(env, _sku_from_text(path)),
        "seo": seo.get("title"),
        "total": total,
        "characteristics": rows,
        "n": len(rows),
        "price": price,
        "is_available": price.get("is_available") if isinstance(price, dict) else None,
        "page_type": info.get("pageType"),
        "pageInfo": env.get("pageInfo"),
        "widget_count": len(env.get("widgetStates") or {}),
    }


def _variant_tabs(env: dict) -> tuple[list[dict], Any]:
    widget = _widget(env, "webReviewsVariantMode") or {}
    tabs_w = widget.get("tabs") if isinstance(widget.get("tabs"), dict) else {}
    out: list[dict] = []
    for tab in tabs_w.get("tabs") or []:
        if not isinstance(tab, dict):
            continue
        common = tab.get("common") if isinstance(tab.get("common"), dict) else {}
        action = common.get("action") if isinstance(common.get("action"), dict) else {}
        link = action.get("link") if isinstance(action.get("link"), str) else None
        title = tab.get("title") if isinstance(tab.get("title"), str) else None
        out.append({"title": title, "url": link})
    return out, tabs_w.get("selectedTabIndex")


def _context_stats(env: dict) -> list[dict]:
    widget = _widget(env, "contextQuestionsStatistic") or {}
    raw = widget.get("questions")
    if not isinstance(raw, list):
        return []
    out: list[dict] = []
    for question in raw:
        if not isinstance(question, dict):
            continue
        answers: list[dict] = []
        for answer in question.get("answers") or []:
            if not isinstance(answer, dict):
                continue
            answers.append({
                "title": answer.get("answerTitle") if isinstance(answer.get("answerTitle"), str) else None,
                "percentage": answer.get("percentage"),
            })
        out.append({
            "title": question.get("questionTitle") if isinstance(question.get("questionTitle"), str) else None,
            "popular": question.get("popularAnswerTitle") if isinstance(question.get("popularAnswerTitle"), str) else None,
            "answers": answers,
        })
    return out


def _histogram(env: dict) -> tuple[Any, Any, list[dict]]:
    widget = _widget(env, "webReviewProductScore") or {}
    rows: list[dict] = []
    raw = widget.get("score")
    if isinstance(raw, list):
        for row in raw:
            if not isinstance(row, dict):
                continue
            rows.append({"title": row.get("title"), "value": row.get("value")})
    return widget.get("totalScore"), widget.get("reviewsCount"), rows


def _photo_strip(env: dict) -> list[dict]:
    widget = _widget(env, "webListPhotos") or {}
    raw = widget.get("mediaContent")
    if not isinstance(raw, list):
        return []
    out: list[dict] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        preview = item.get("previewUrl")
        out.append({
            "type": item.get("type") if isinstance(item.get("type"), str) else None,
            "preview_url": preview if isinstance(preview, str) else None,
            "uuid": item.get("uuid") if isinstance(item.get("uuid"), str) else None,
        })
    return out


def review_stats(client, url_or_sku: str, variant: str = "all") -> dict:
    """Histogram and buyer-context stats from the reviews fragment.

    `variant="all"` is `reviewsVariantMode=2` (every variant). `variant="this"`
    is `reviewsVariantMode=1` (this SKU only). Proven on the pdp-part URL,
    which is a GET and not the reviews list (`reviews()` still owns `?page=`).
    """
    raw = str(url_or_sku).strip()
    sku = _sku_from_text(raw) or raw.strip("/")
    if not sku or not str(sku).isdigit():
        raise ParseError("review_stats: need a numeric SKU or a product URL containing one")
    mode = "1" if str(variant).strip().lower() in {"this", "1", "variant"} else "2"
    path = f"/product/{sku}/reviews/pdp-part?oos_search=false&reviewsVariantMode={mode}"
    env = _require_env(_page_url(client, path), "review_stats")
    total_score, reviews_count, histogram = _histogram(env)
    tabs, selected = _variant_tabs(env)
    info = env.get("pageInfo") if isinstance(env.get("pageInfo"), dict) else {}
    return {
        "sku": sku,
        "variant": "this" if mode == "1" else "all",
        "total_score": total_score,
        "reviews_count": reviews_count,
        "histogram": histogram,
        "context": _context_stats(env),
        "photos": _photo_strip(env),
        "tabs": tabs,
        "selected_tab": selected,
        "page_type": info.get("pageType"),
        "pageInfo": env.get("pageInfo"),
        "widget_count": len(env.get("widgetStates") or {}),
    }


def availability(client, url_or_sku: str) -> dict:
    """Price availability from the product card. Delivery slots are not here.

    `webDelivery` on screen 1 is an empty object for this anonymous session
    (no dates, no pickup points). Filling it is suspected to be a POST to
    `widget/json/v2`, which this client does not call. `is_available` is
    `webPrice.isAvailable`; `offer_available` is `webSale.offer.isAvailable`.
    """
    path = _product_path(url_or_sku)
    env = _require_env(_page_url(client, path, __rr="1"), "availability")
    price = _price_block(env) or {}
    sale = _widget(env, "webSale") or {}
    offer = sale.get("offer") if isinstance(sale.get("offer"), dict) else {}
    delivery = _widget(env, "webDelivery")
    empty = not isinstance(delivery, dict) or len(delivery) == 0
    public = None
    if isinstance(delivery, dict) and not empty:
        public = {
            key: value for key, value in delivery.items()
            if key not in ("trackingInfo", "cellTrackingInfo", "testInfo")
        }
    info = env.get("pageInfo") if isinstance(env.get("pageInfo"), dict) else {}
    return {
        "sku": _sku_of(env, _sku_from_text(path)),
        "is_available": price.get("is_available"),
        "price": price.get("price"),
        "original_price": price.get("original_price"),
        "offer_available": offer.get("isAvailable"),
        "delivery_empty": empty,
        "delivery": public,
        "page_type": info.get("pageType"),
        "pageInfo": env.get("pageInfo"),
        "widget_count": len(env.get("widgetStates") or {}),
    }


def _scalar_sku(value: Any) -> Any:
    text = str(value).strip()
    if text.isdigit():
        return int(text)
    return text


def _location_row(node: Any) -> dict | None:
    """Public fields only. Tokens and nested tracking stay out."""
    if not isinstance(node, dict):
        return None
    wanted = (
        "areaId", "id", "name", "fullName", "city", "region", "country",
        "type", "timezone", "fias", "uid",
    )
    out: dict[str, Any] = {}
    for key in wanted:
        value = node.get(key)
        if isinstance(value, (str, int, float)) and not isinstance(value, bool):
            out[key] = value
    if out:
        return out
    for key, value in node.items():
        if key.lower() in ("token", "usertoken", "cookie"):
            continue
        if isinstance(value, (str, int, float)) and not isinstance(value, bool):
            out[key] = value
    return out or None


def location_current(client) -> dict:
    """Current delivery area. GET `/api/location/v2/current`. No `ip` is sent."""
    url = f"{client.base}/api/location/v2/current"
    response = client.transport.request(
        "GET", url, headers=client.signer.headers("GET", url),
    )
    payload = response.json()
    row = _location_row(payload) if isinstance(payload, dict) else None
    return {"location": row, "raw_type": type(payload).__name__}


def location_search(client, text: str, limit: int = 10) -> dict:
    """Location suggest. GET `/api/location/v2/search?query=`.

    The site keeps the first 10 rows. `limit` is capped at 10 for the same
    reason. This does not call `POST /api/location/v2/user/location`.
    """
    query = str(text).strip()
    if not query:
        raise ParseError("location_search: empty query")
    cap = 10 if limit is None or limit > 10 or limit < 1 else int(limit)
    url = f"{client.base}/api/location/v2/search?query={quote(query, safe='')}"
    response = client.transport.request(
        "GET", url, headers=client.signer.headers("GET", url),
    )
    payload = response.json()
    rows = payload if isinstance(payload, list) else []
    locations = []
    for item in rows[:cap]:
        row = _location_row(item)
        if row:
            locations.append(row)
    return {"query": query, "locations": locations, "n": len(locations)}


def _comment_row(raw: Any) -> dict | None:
    if not isinstance(raw, dict):
        return None
    content = raw.get("content") if isinstance(raw.get("content"), dict) else {}
    text = content.get("comment") or content.get("text")
    if not isinstance(text, str):
        for key in ("comment", "text", "message"):
            if isinstance(raw.get(key), str):
                text = raw[key]
                break
    if not isinstance(text, str):
        text = None
    return {
        "uuid": raw.get("uuid"),
        "author": _author_name(raw.get("author")),
        "text": text,
        "created_at": raw.get("createdAt") or raw.get("publishedAt"),
        "parent_uuid": raw.get("parentUuid") if isinstance(raw.get("parentUuid"), str) else None,
        "root_parent_uuid": raw.get("rootParentUuid") if isinstance(raw.get("rootParentUuid"), str) else None,
    }


def review_comments(client, review_uuid: str, sku: str, *,
                    root_sku: str | None = None, limit: int = 10,
                    offset: int = 0) -> dict:
    """Comments on one review.

    This is the only POST in the library. The site loads them with
    `POST /api/composer-api.bx/_action/rpGetCommentsByReviewUuid` and a JSON
    body `{reviewUuid, sku, rootSku, limit, offset}` (`loadMoreComments` in
    `rp-product-web-list-reviews-v3.js`). The action name is a getter: it
    does not create, vote, or delete. `limit` defaults to 10, matching the
    widget. `root_sku` defaults to `sku` (the page SKU when a review is
    about another variant).
    """
    uuid = str(review_uuid).strip()
    if not uuid:
        raise ParseError("review_comments: empty review uuid")
    sku_text = str(sku).strip()
    if not sku_text:
        raise ParseError("review_comments: empty sku")
    root = str(root_sku).strip() if root_sku else sku_text
    body = {
        "reviewUuid": uuid,
        "sku": _scalar_sku(sku_text),
        "rootSku": _scalar_sku(root),
        "limit": int(limit),
        "offset": int(offset),
    }
    url = f"{client.base}{COMPOSER}/_action/rpGetCommentsByReviewUuid"
    response = client.transport.request(
        "POST", url, json_body=body, headers=client.signer.headers("POST", url),
    )
    payload = response.json()
    raw_comments: Any = None
    if isinstance(payload, dict):
        raw_comments = payload.get("comments")
    elif isinstance(payload, list):
        raw_comments = payload
    comments: list[dict] = []
    if isinstance(raw_comments, list):
        for item in raw_comments:
            row = _comment_row(item)
            if row is not None:
                comments.append(row)
    return {
        "review_uuid": uuid,
        "sku": sku_text,
        "root_sku": root,
        "limit": body["limit"],
        "offset": body["offset"],
        "comments": comments,
        "n": len(comments),
    }
