#!/usr/bin/env python3
"""Typer CLI for the unofficial Ozon catalogue client.

Read paths run freely. There are NO mutating commands in this client — every
method implemented is a read. If write endpoints are added later they must be
plan-by-default behind an explicit flag (see README).
"""
from __future__ import annotations

from __future__ import annotations

import json

import typer
from rich.console import Console
from rich.table import Table

from . import OzonClient
from .exceptions import (
    AntibotBlocked,
    AuthRequired,
    NotFound,
    OzonError,
    RateLimited,
    TransportError,
)

app = typer.Typer(
    help="Unofficial reverse-engineered Ozon catalogue client "
         "(browser oracle by default; --transport cookiejar for curl_cffi).",
    no_args_is_help=True,
)
console = Console()
err = Console(stderr=True)


_ACTIVE: list[OzonClient] = []
_TRANSPORT: str | None = None


def _client(base: str | None, cdp: str | None, rate: float) -> OzonClient:
    c = OzonClient(base=base, cdp=cdp, rate=rate, transport=_TRANSPORT)
    _ACTIVE.append(c)
    return c


@app.callback()
def _main(
    transport: str = typer.Option(
        None, "--transport",
        help="browser (default, in-page fetch) or cookiejar "
             "(curl_cffi replay of the CDP cookie jar)",
    ),
):
    """Close the CDP socket on exit, whoever exits."""
    global _TRANSPORT
    _TRANSPORT = transport
    import atexit

    def _shutdown():
        while _ACTIVE:
            try:
                _ACTIVE.pop().close()
            except Exception:
                pass

    atexit.register(_shutdown)


def _fail(e: Exception) -> None:
    """Structured, actionable errors — an agent driving this must recover."""
    if isinstance(e, TransportError):
        err.print(f"[red]transport:[/red] {e}")
        err.print("  → is Chrome running with --remote-debugging-port=9222?")
        err.print("  → run: ozon warmup")
    elif isinstance(e, AntibotBlocked):
        err.print(f"[red]antibot 403:[/red] incident={e.incident_id}")
        err.print("  → the browser session lost its clearance; run: ozon warmup")
    elif isinstance(e, RateLimited):
        err.print(f"[yellow]rate limited:[/yellow] retry_after={e.retry_after}")
        err.print("  → lower --rate (e.g. --rate 0.5) and retry")
    elif isinstance(e, AuthRequired):
        err.print(f"[yellow]auth required:[/yellow] {e}")
        err.print("  → log into Ozon in the warm browser profile, then retry")
    elif isinstance(e, NotFound):
        err.print(f"[yellow]not found:[/yellow] {e}")
        err.print("  → check the slug/SKU; category slugs look like 'elektronika-15500'")
    elif isinstance(e, OzonError):
        err.print(f"[red]error:[/red] {e}")
    else:
        err.print(f"[red]{type(e).__name__}:[/red] {e}")
    raise typer.Exit(1)


def _fmt(value):
    if isinstance(value, str) and len(value) > 240:
        return value[:240] + f"…<{len(value)} chars>"
    return value


def _emit(data, as_json: bool, title: str | None = None):
    if as_json:
        print(json.dumps(data, ensure_ascii=False, indent=2, default=str))
        return
    if title:
        console.print(f"[bold]{title}[/bold]")
    console.print(data if not isinstance(data, dict) else
                  "\n".join(f"  {k}: {_fmt(v)}" for k, v in data.items()
                            if k not in _SKIP_KEYS))


def _table(products: list[dict]):
    t = Table("SKU", "Name", "Price", "Rating", "Reviews")
    for p in products:
        t.add_row(str(p.get("sku") or ""),
                  (p.get("name") or "")[:58],
                  str(p.get("price") or ""),
                  str(p.get("rating") or ""),
                  str(p.get("reviews") or ""))
    console.print(t)

_SKIP_KEYS = {
    "products", "tiles", "comments", "widgetStates", "layout",
    "characteristics", "media", "questions", "groups", "shops",
    "histogram", "links", "photos", "context", "filters", "sort_options",
    "reviews",
}
_SORT_HELP = "score | new | price | price_desc | rating | discount"


def _parse_filters(pairs: list[str] | None) -> dict | None:
    if not pairs:
        return None
    out: dict[str, str] = {}
    for pair in pairs:
        if "=" not in pair:
            raise typer.BadParameter(f"filter must be key=value, got {pair!r}")
        key, value = pair.split("=", 1)
        key = key.strip()
        if not key:
            raise typer.BadParameter(f"filter must be key=value, got {pair!r}")
        out[key] = value
    return out


def _families(states: dict) -> list[str]:
    return sorted({str(key).split("-", 1)[0] for key in states})


@app.command()
def warmup(
    url: str = typer.Option(None, "--url", help="Page to land on"),
    cdp: str = typer.Option(None, "--cdp", help="CDP endpoint"),
    base: str = typer.Option(None, "--base", help="ozon.by | www.ozon.ru"),
):
    """Navigate the browser so cookies + antibot clearance are established."""
    c = _client(base, cdp, rate=0)
    try:
        info = c.warmup(url)
        console.print(f"[green]warmed[/green] {info}")
        ok = c.ready()
        console.print(f"session ready: [bold]{ok}[/bold]")
        if not ok:
            err.print("[yellow]session not warm — retry in a few seconds[/yellow]")
            raise typer.Exit(1)
    except Exception as e:
        _fail(e)


@app.command()
def status(
    cdp: str = typer.Option(None, "--cdp"),
    base: str = typer.Option(None, "--base"),
):
    """Report whether the current browser session can call the API."""
    c = _client(base, cdp, rate=0)
    try:
        c.transport.connect()
        console.print(f"page:   {c.page_url()}")
        console.print(f"base:   {c.base}")
        console.print(f"ready:  [bold]{c.ready()}[/bold]")
    except Exception as e:
        _fail(e)


@app.command()
def search(
    query: str = typer.Argument(..., help="search text"),
    page: int = typer.Option(1, "--page", "-p"),
    sorting: str = typer.Option(None, "--sorting", help=_SORT_HELP),
    filter_pair: list[str] = typer.Option(
        None, "--filter", help="GET filter key=value, repeatable (e.g. is_promo=t)",
    ),
    json_out: bool = typer.Option(False, "--json", help="emit raw JSON"),
    limit: int = typer.Option(10, "--limit", "-n"),
    cdp: str = typer.Option(None, "--cdp"),
    base: str = typer.Option(None, "--base"),
    rate: float = typer.Option(2.0, "--rate"),
):
    """Search the catalogue."""
    c = _client(base, cdp, rate)
    try:
        r = c.search(query, page=page, sorting=sorting, filters=_parse_filters(filter_pair))
    except Exception as e:
        _fail(e)
        return
    if json_out:
        print(json.dumps(r, ensure_ascii=False, indent=2, default=str))
        return
    console.print(f"[bold]{len(r['products'])} products[/bold] "
                  f"(page {page}, sorting={r.get('sort_options') and sorting}) · {r.get('seo')}")
    _table(r["products"][:limit])


@app.command()
def product(
    sku_or_url: str = typer.Argument(..., help="SKU or /product/... URL"),
    json_out: bool = typer.Option(False, "--json"),
    cdp: str = typer.Option(None, "--cdp"),
    base: str = typer.Option(None, "--base"),
    rate: float = typer.Option(2.0, "--rate"),
):
    """Fetch a product card."""
    c = _client(base, cdp, rate)
    try:
        r = c.product(sku_or_url)
    except Exception as e:
        _fail(e)
        return
    _emit(r, json_out, title=r.get("title"))


@app.command()
def category(
    slug: str = typer.Argument(..., help="e.g. elektronika-15500"),
    page: int = typer.Option(1, "--page", "-p"),
    sorting: str = typer.Option(None, "--sorting", help=_SORT_HELP),
    filter_pair: list[str] = typer.Option(None, "--filter", help="GET filter key=value"),
    limit: int = typer.Option(10, "--limit", "-n"),
    json_out: bool = typer.Option(False, "--json"),
    cdp: str = typer.Option(None, "--cdp"),
    base: str = typer.Option(None, "--base"),
    rate: float = typer.Option(2.0, "--rate"),
):
    """List products in a category."""
    c = _client(base, cdp, rate)
    try:
        r = c.category(slug, page=page, sorting=sorting, filters=_parse_filters(filter_pair))
    except Exception as e:
        _fail(e)
        return
    if json_out:
        print(json.dumps(r, ensure_ascii=False, indent=2, default=str))
        return
    console.print(f"[bold]{len(r['products'])} products[/bold] · {r.get('seo')}")
    _table(r["products"][:limit])


@app.command()
def reviews(
    sku: str = typer.Argument(..., help="product SKU"),
    page: int = typer.Option(1, "--page", "-p"),
    sort: str = typer.Option(None, "--sort",
                             help="usefulness_desc | score_desc | score_asc"),
    json_out: bool = typer.Option(False, "--json"),
    cdp: str = typer.Option(None, "--cdp"),
    base: str = typer.Option(None, "--base"),
    rate: float = typer.Option(2.0, "--rate"),
):
    c = _client(base, cdp, rate)
    try:
        r = c.reviews(sku, page=page, sort=sort)
    except Exception as e:
        _fail(e)
        return
    if json_out:
        print(json.dumps(r, ensure_ascii=False, indent=2, default=str))
        return
    console.print(f"[bold]{len(r['reviews'])} reviews[/bold] "
                  f"(total={r.get('total')}, score={r.get('score')}, "
                  f"sort={r.get('sort')}) · sku {sku}")
    for rv in r["reviews"][:10]:
        console.print(f"  [cyan]{rv.get('rating')}★[/cyan] "
                      f"{rv.get('author') or 'anon'} · {rv.get('published_at') or ''}")
        body = (rv.get("text") or rv.get("title") or "")
        console.print("     " + body[:200])


@app.command()
def questions(
    sku_or_url: str = typer.Argument(..., help="SKU, slug, or /product/... URL"),
    qsort: str = typer.Option(
        None, "--qsort",
        help="created_at_desc | usefulness_desc | has_answers_desc | has_answers_asc",
    ),
    cursor: str = typer.Option(
        None, "--cursor",
        help="next_url from a previous questions response (page_key cursor)",
    ),
    json_out: bool = typer.Option(False, "--json"),
    cdp: str = typer.Option(None, "--cdp"),
    base: str = typer.Option(None, "--base"),
    rate: float = typer.Option(2.0, "--rate"),
):
    """Questions and answers (read-only — never votes or posts)."""
    c = _client(base, cdp, rate)
    try:
        r = c.questions(sku_or_url, qsort=qsort, cursor=cursor)
    except Exception as e:
        _fail(e)
        return
    if json_out:
        print(json.dumps(r, ensure_ascii=False, indent=2, default=str))
        return
    console.print(f"[bold]{r.get('n')} questions[/bold] "
                  f"(total={r.get('total')}, qsort={r.get('qsort')})")
    for q in (r.get("questions") or [])[:10]:
        console.print(f"  [cyan]{q.get('author') or 'anon'}[/cyan] · "
                      f"{q.get('created_at') or ''}")
        console.print("     " + (q.get("text") or "")[:200])
        for ans in (q.get("answers") or [])[:2]:
            console.print(f"       ↳ {ans.get('author') or ''}: "
                          f"{(ans.get('text') or '')[:160]}")


@app.command("summary")
def summary_cmd(
    json_out: bool = typer.Option(False, "--json"),
    cdp: str = typer.Option(None, "--cdp"),
    base: str = typer.Option(None, "--base"),
):
    """Cheapest gated call (session probe)."""
    c = _client(base, cdp, rate=0)
    try:
        _emit(c.summary(), json_out)
    except Exception as e:
        _fail(e)


@app.command()
def cart(
    json_out: bool = typer.Option(False, "--json"),
    cdp: str = typer.Option(None, "--cdp"),
    base: str = typer.Option(None, "--base"),
    rate: float = typer.Option(2.0, "--rate"),
):
    """Cart page (read-only)."""
    c = _client(base, cdp, rate)
    try:
        _emit(c.cart(), json_out)
    except Exception as e:
        _fail(e)


@app.command()
def favorites(
    json_out: bool = typer.Option(False, "--json"),
    cdp: str = typer.Option(None, "--cdp"),
    base: str = typer.Option(None, "--base"),
    rate: float = typer.Option(2.0, "--rate"),
):
    """Favourites page (read-only)."""
    c = _client(base, cdp, rate)
    try:
        _emit(c.favorites(), json_out)
    except Exception as e:
        _fail(e)


@app.command()
def menu(
    menu_id: int = typer.Option(237, "--menu-id"),
    json_out: bool = typer.Option(False, "--json"),
    cdp: str = typer.Option(None, "--cdp"),
    base: str = typer.Option(None, "--base"),
    rate: float = typer.Option(2.0, "--rate"),
):
    """Catalogue menu children."""
    c = _client(base, cdp, rate)
    try:
        _emit(c.menu_children(menu_id), json_out)
    except Exception as e:
        _fail(e)



@app.command()
def page(
    url: str = typer.Argument(..., help="site path or https://ozon.by/... URL"),
    json_out: bool = typer.Option(False, "--json", help="decoded envelope as JSON"),
    cdp: str = typer.Option(None, "--cdp"),
    base: str = typer.Option(None, "--base"),
    rate: float = typer.Option(2.0, "--rate"),
):
    """Fetch any public page. Widget states are double-decoded. GET only."""
    c = _client(base, cdp, rate)
    try:
        r = c.page(url)
    except Exception as e:
        _fail(e)
        return
    if json_out:
        print(json.dumps(r, ensure_ascii=False, indent=2, default=str))
        return
    info = r.get("pageInfo") if isinstance(r.get("pageInfo"), dict) else {}
    seo = r.get("seo") if isinstance(r.get("seo"), dict) else {}
    states = r.get("widgetStates") if isinstance(r.get("widgetStates"), dict) else {}
    console.print(f"pageType={info.get('pageType')} url={info.get('url')}")
    console.print(f"seo: {seo.get('title')}")
    console.print(f"widgets: {len(states)}")
    console.print("families: " + ", ".join(_families(states)))


def _run_listing(kind: str, slug: str, page_n: int, sorting, filter_pair, limit,
                 json_out, cdp, base, rate):
    c = _client(base, cdp, rate)
    try:
        r = getattr(c, kind)(slug, page=page_n, sorting=sorting,
                             filters=_parse_filters(filter_pair))
    except Exception as e:
        _fail(e)
        return
    if json_out:
        print(json.dumps(r, ensure_ascii=False, indent=2, default=str))
        return
    header = r.get("header") if isinstance(r.get("header"), dict) else {}
    console.print(f"[bold]{r.get('kind')}[/bold] {header.get('name') or slug} · "
                  f"{len(r.get('products') or [])} products · {r.get('seo')}")
    _table((r.get("products") or [])[:limit])


@app.command()
def brand(
    slug: str = typer.Argument(..., help="e.g. apple-26303000"),
    page: int = typer.Option(1, "--page", "-p"),
    sorting: str = typer.Option(None, "--sorting", help=_SORT_HELP),
    filter_pair: list[str] = typer.Option(None, "--filter", help="GET filter key=value"),
    limit: int = typer.Option(10, "--limit", "-n"),
    json_out: bool = typer.Option(False, "--json"),
    cdp: str = typer.Option(None, "--cdp"),
    base: str = typer.Option(None, "--base"),
    rate: float = typer.Option(2.0, "--rate"),
):
    """Brand listing (not the /brand/ directory — use `brands`)."""
    _run_listing("brand", slug, page, sorting, filter_pair, limit, json_out, cdp, base, rate)


@app.command()
def seller(
    slug: str = typer.Argument(..., help="e.g. ozon or mvideo-1865500"),
    page: int = typer.Option(1, "--page", "-p"),
    sorting: str = typer.Option(None, "--sorting", help=_SORT_HELP),
    filter_pair: list[str] = typer.Option(None, "--filter", help="GET filter key=value"),
    limit: int = typer.Option(10, "--limit", "-n"),
    json_out: bool = typer.Option(False, "--json"),
    cdp: str = typer.Option(None, "--cdp"),
    base: str = typer.Option(None, "--base"),
    rate: float = typer.Option(2.0, "--rate"),
):
    """Seller shop (not the /seller/ directory — use `sellers`)."""
    _run_listing("seller", slug, page, sorting, filter_pair, limit, json_out, cdp, base, rate)


@app.command()
def highlight(
    slug: str = typer.Argument(..., help="e.g. apple-4442805"),
    page: int = typer.Option(1, "--page", "-p"),
    sorting: str = typer.Option(None, "--sorting", help=_SORT_HELP),
    filter_pair: list[str] = typer.Option(None, "--filter", help="GET filter key=value"),
    limit: int = typer.Option(10, "--limit", "-n"),
    json_out: bool = typer.Option(False, "--json"),
    cdp: str = typer.Option(None, "--cdp"),
    base: str = typer.Option(None, "--base"),
    rate: float = typer.Option(2.0, "--rate"),
):
    """Highlight / promo listing. /highlight/ with no slug 404s."""
    _run_listing("highlight", slug, page, sorting, filter_pair, limit, json_out, cdp, base, rate)


@app.command()
def brands(
    json_out: bool = typer.Option(False, "--json"),
    limit: int = typer.Option(15, "--limit", "-n"),
    cdp: str = typer.Option(None, "--cdp"),
    base: str = typer.Option(None, "--base"),
    rate: float = typer.Option(2.0, "--rate"),
):
    """Alphabetical brand directory (/brand/)."""
    c = _client(base, cdp, rate)
    try:
        r = c.brands()
    except Exception as e:
        _fail(e)
        return
    if json_out:
        print(json.dumps(r, ensure_ascii=False, indent=2, default=str))
        return
    console.print(f"[bold]{r.get('n_brands')} brands[/bold] in {r.get('n_groups')} groups · {r.get('seo')}")
    shown = 0
    for group in r.get("groups") or []:
        for row in group.get("brands") or []:
            if shown >= limit:
                return
            console.print(f"  {group.get('name')}: {row.get('title')}  {row.get('url')}")
            shown += 1


@app.command()
def sellers(
    cursor: str = typer.Option(None, "--cursor", help="next_url from a previous page"),
    json_out: bool = typer.Option(False, "--json"),
    limit: int = typer.Option(10, "--limit", "-n"),
    cdp: str = typer.Option(None, "--cdp"),
    base: str = typer.Option(None, "--base"),
    rate: float = typer.Option(2.0, "--rate"),
):
    """Seller directory (/seller/), mallFeed shop cards."""
    c = _client(base, cdp, rate)
    try:
        r = c.sellers(cursor=cursor)
    except Exception as e:
        _fail(e)
        return
    if json_out:
        print(json.dumps(r, ensure_ascii=False, indent=2, default=str))
        return
    console.print(f"[bold]{r.get('n')} shops[/bold] · {r.get('seo')}")
    for shop in (r.get("shops") or [])[:limit]:
        console.print(f"  {shop.get('name')}  {shop.get('url')}  "
                      f"({len(shop.get('products') or [])} tiles)")


@app.command()
def similar(
    sku: str = typer.Argument(..., help="SKU or product URL"),
    limit: int = typer.Option(10, "--limit", "-n"),
    json_out: bool = typer.Option(False, "--json"),
    cdp: str = typer.Option(None, "--cdp"),
    base: str = typer.Option(None, "--base"),
    rate: float = typer.Option(2.0, "--rate"),
):
    """Similar items modal. Photo-similar tab has no separate URL."""
    c = _client(base, cdp, rate)
    try:
        r = c.similar(sku)
    except Exception as e:
        _fail(e)
        return
    if json_out:
        print(json.dumps(r, ensure_ascii=False, indent=2, default=str))
        return
    console.print(f"[bold]{r.get('n')} similar[/bold] tabs={r.get('tabs')}")
    _table((r.get("products") or [])[:limit])


@app.command()
def media(
    sku: str = typer.Argument(..., help="SKU, slug, or product URL"),
    limit: int = typer.Option(8, "--limit", "-n"),
    json_out: bool = typer.Option(False, "--json"),
    cdp: str = typer.Option(None, "--cdp"),
    base: str = typer.Option(None, "--base"),
    rate: float = typer.Option(2.0, "--rate"),
):
    """Review photos and videos (the Фото и видео tab)."""
    c = _client(base, cdp, rate)
    try:
        r = c.media(sku)
    except Exception as e:
        _fail(e)
        return
    if json_out:
        print(json.dumps(r, ensure_ascii=False, indent=2, default=str))
        return
    console.print(f"[bold]{r.get('n')} media[/bold] total={r.get('total')} "
                  f"page={r.get('page')} per_page={r.get('per_page')}")
    for item in (r.get("media") or [])[:limit]:
        console.print(f"  {item.get('type')} {item.get('rating')}★ {item.get('author') or ''} "
                      f"{(item.get('url') or '')[:80]}")


@app.command()
def features(
    sku: str = typer.Argument(..., help="SKU, slug, or product URL"),
    json_out: bool = typer.Option(False, "--json"),
    cdp: str = typer.Option(None, "--cdp"),
    base: str = typer.Option(None, "--base"),
    rate: float = typer.Option(2.0, "--rate"),
):
    """Characteristic table from the features tab."""
    c = _client(base, cdp, rate)
    try:
        r = c.features(sku)
    except Exception as e:
        _fail(e)
        return
    if json_out:
        print(json.dumps(r, ensure_ascii=False, indent=2, default=str))
        return
    console.print(f"[bold]{r.get('n')} characteristics[/bold] total={r.get('total')} "
                  f"sku={r.get('sku')}")
    for row in (r.get("characteristics") or [])[:12]:
        console.print(f"  {row.get('name')}: {', '.join(row.get('values') or [])}")


@app.command("review-stats")
def review_stats_cmd(
    sku: str = typer.Argument(..., help="SKU or product URL"),
    variant: str = typer.Option("all", "--variant", help="all | this"),
    json_out: bool = typer.Option(False, "--json"),
    cdp: str = typer.Option(None, "--cdp"),
    base: str = typer.Option(None, "--base"),
    rate: float = typer.Option(2.0, "--rate"),
):
    """Star histogram and buyer-context stats (reviews fragment)."""
    c = _client(base, cdp, rate)
    try:
        r = c.review_stats(sku, variant=variant)
    except Exception as e:
        _fail(e)
        return
    if json_out:
        print(json.dumps(r, ensure_ascii=False, indent=2, default=str))
        return
    console.print(f"score={r.get('total_score')} reviews={r.get('reviews_count')} "
                  f"variant={r.get('variant')}")
    for row in r.get("histogram") or []:
        console.print(f"  {row.get('title')}: {row.get('value')}")


@app.command()
def availability(
    sku: str = typer.Argument(..., help="SKU, slug, or product URL"),
    json_out: bool = typer.Option(False, "--json"),
    cdp: str = typer.Option(None, "--cdp"),
    base: str = typer.Option(None, "--base"),
    rate: float = typer.Option(2.0, "--rate"),
):
    """Price availability. Delivery widget is empty without a POST we do not send."""
    c = _client(base, cdp, rate)
    try:
        r = c.availability(sku)
    except Exception as e:
        _fail(e)
        return
    _emit(r, json_out, title=f"sku {r.get('sku')}")


@app.command()
def location(
    json_out: bool = typer.Option(False, "--json"),
    cdp: str = typer.Option(None, "--cdp"),
    base: str = typer.Option(None, "--base"),
):
    """Current delivery area (GET /api/location/v2/current)."""
    c = _client(base, cdp, rate=0)
    try:
        _emit(c.location_current(), json_out)
    except Exception as e:
        _fail(e)


@app.command("location-search")
def location_search_cmd(
    text: str = typer.Argument(..., help="city or region text"),
    limit: int = typer.Option(10, "--limit", "-n"),
    json_out: bool = typer.Option(False, "--json"),
    cdp: str = typer.Option(None, "--cdp"),
    base: str = typer.Option(None, "--base"),
    rate: float = typer.Option(2.0, "--rate"),
):
    """Search delivery areas (GET /api/location/v2/search). Does not set one."""
    c = _client(base, cdp, rate)
    try:
        r = c.location_search(text, limit=limit)
    except Exception as e:
        _fail(e)
        return
    if json_out:
        print(json.dumps(r, ensure_ascii=False, indent=2, default=str))
        return
    console.print(f"[bold]{r.get('n')} locations[/bold] · {r.get('query')}")
    for row in r.get("locations") or []:
        console.print(f"  {row.get('name') or row.get('fullName') or row}  "
                      f"areaId={row.get('areaId')}")


@app.command("review-comments")
def review_comments_cmd(
    review_uuid: str = typer.Argument(..., help="review uuid"),
    sku: str = typer.Option(..., "--sku", help="review itemId / page SKU"),
    root_sku: str = typer.Option(None, "--root-sku", help="page SKU if the review is another variant"),
    limit: int = typer.Option(10, "--limit", "-n"),
    offset: int = typer.Option(0, "--offset"),
    json_out: bool = typer.Option(False, "--json"),
    cdp: str = typer.Option(None, "--cdp"),
    base: str = typer.Option(None, "--base"),
    rate: float = typer.Option(2.0, "--rate"),
):
    """Read comments on a review. Catalogue POST getter; does not create or vote."""
    c = _client(base, cdp, rate)
    try:
        r = c.review_comments(review_uuid, sku, root_sku=root_sku, limit=limit, offset=offset)
    except Exception as e:
        _fail(e)
        return
    if json_out:
        print(json.dumps(r, ensure_ascii=False, indent=2, default=str))
        return
    console.print(f"[bold]{r.get('n')} comments[/bold] · {review_uuid}")
    for row in (r.get("comments") or [])[:10]:
        console.print(f"  {row.get('author') or ''}: {(row.get('text') or '')[:160]}")

if __name__ == "__main__":
    app()
