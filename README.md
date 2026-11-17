# ozon-client

Unofficial, reverse-engineered Python client for the Ozon web catalogue
(`ozon.by` / `www.ozon.ru`) — a library **and** a CLI.

Built from live traffic analysis, not from guesswork. Everything documented
below was verified against the real site.

---

## Why it looks like this

Ozon's public product pages are not served as plain HTML — the server returns
a **layout envelope** and the frontend renders it. Anyone writing a client has
to talk to that envelope API:

```
GET /api/entrypoint-api.bx/page/json/v2?url=/search/?text=...
```

That endpoint is behind Ozon's antibot. The recon that produced this client
established the following, and the design follows directly from it:

| Finding | Consequence for the client |
|---|---|
| **Hybrid / Method 4** — cold clients are challenged; the clearance is the cookie jar | There is no HMAC and no bearer token. A browser must mint cookies once (CDP, not `document.cookie`). `curl_cffi` then replays that jar on the same IP with no live page. A cold client is still 403. See [Browser-free mode](#browser-free-mode) and `audit/antibot_probe.md`. |
| Antibot verdict is a **403 with `x-o3-*` headers + an incident id**, body is masked HTML | Errors are parsed into typed exceptions carrying the incident id instead of being swallowed. |
| Response is `{"layout": [...], "widgetStates": {"<widget>-<id>-default-N": "<json string>"}}` | Parsers walk `widgetStates`, not a flat JSON tree. Widget values are **JSON-encoded strings** and must be double-decoded. |
| Product tiles live under `tileGridDesktop-*` → `items[]` → `mainState[]` atoms | There is no `{"name":…, "price":…}` object. Price/name/rating are recovered from atom text. |
| Pagination is `?page=N`; `layout_page_index` is **ignored** | Clients use `page=N`. |
| Reviews live at `/reviews/<sku>/`; `/product/reviews/<sku>/` **404s** | The reviews path reflects what actually works. |
| `x-o3-parent-requestid` and `x-page-view-id` are stable for one document and rotate on navigation; `x-page-previous` is the previous page type | The signer follows that. The headers are fidelity, not the clearance. See [Anti-detection](#anti-detection). |

### The transport: browser oracle (default)

`OzonClient()` drives a **real Chrome** you already have open and makes
`fetch()` calls from inside the page. That path does not need `curl_cffi`.
Cookies, TLS and the challenge stay in the browser:

```
Python  ──CDP──▶  Chrome (warm session)  ──fetch()──▶  Ozon  ──▶  200 JSON
```

This is no longer the only path. It remains the default so existing
`OzonClient()` callers keep working without an extra dependency. The live
browser jar is also what the site itself refreshes; the cookie-jar transport
holds a snapshot until a 403 makes it re-read CDP.

### Browser-free mode

Proven on 2026-10-16 (`audit/antibot_probe.md`, variants B and C) on one
shared egress IP. A cold `curl_cffi` client got **403** with
`ozon-antibot: 1`. The same client, TLS profile, UA, headers and IP, plus
the CDP cookie jar, got **200** with the same payload class as an in-page
`fetch`. The earlier "non-portable clearance" conclusion was wrong.

```bash
pip install 'ozon-client[browserfree]'   # curl_cffi
# Chrome still has to be open once so the jar can be minted.
ozon --transport cookiejar search "iphone 17"
```

```python
from ozon_client import OzonClient
c = OzonClient(transport="cookiejar")   # or OZON_TRANSPORT=cookiejar
```

If `curl_cffi` is missing, `transport="cookiejar"` prints a fallback message
and uses `BrowserOracle`. Importing the package does not require `curl_cffi`.

The jar is bound to the UA of the browser that minted it. curl_cffi
0.15.0 cannot impersonate Chrome/153 (newest desktop profile:
`chrome146`). Profile-matching hints 403; the minting UA on that same
TLS profile returns 200. The cookie-jar default is therefore the minting
UA, and the TLS/UA mismatch is a known ceiling. See
[Anti-detection](#anti-detection).

**Cookie-jar wire defaults.**

- `curl_cffi` session, HTTP/2, impersonating the newest **desktop** Chrome
  profile the installed library ships. Resolved at runtime (curl_cffi 0.15.0
  → `chrome146`; there is no `chrome153` profile). Not pinned to a literal
  that will rot. TLS stays on that profile either way.
- UA, `sec-ch-ua`, `sec-ch-ua-mobile` and `sec-ch-ua-platform` taken from
  the live browser that minted the jar (`ua_source="browser"`, also
  spelled `auto`). On this host that is Chrome/153 on Linux. `ua_source="profile"`
  is opt-in and sends the profile's own Chrome/146 / macOS hints. A 403
  with `ozon-antibot: 1` on those hints is retried **once** with the live
  UA, then the session cools down.
- Headers: `accept: application/json`,
  `accept-language: ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7`,
  `content-type: application/json`, `priority: u=1, i`, a referer from the
  navigation story (home until a document has been fetched), `sec-fetch-dest: empty`,
  `sec-fetch-mode: cors`, `sec-fetch-site: same-origin`, plus the `x-o3-*`
  and `x-page-*` headers from `BrowserSessionSigner`.
- Cookie **names** only (this client never writes the values):
  `__Secure-access-token`, `abt_data`, `__Secure-ab-group`,
  `__Secure-user-id`, `__Secure-ext_xcid`, `xcid`, `cookie_settings`,
  `__Secure-ETC`, `__Secure-refresh-token`.

A warm browser is required **once** to mint that jar. `document.cookie` is
the wrong handoff: it only exposes `__Secure-ab-group` and `xcid`. The
other seven are HttpOnly. `abt_data` on this profile is a **partitioned**
cookie (`topLevelSite` = the Ozon origin, `hasCrossSiteAncestor` false).
`Network.getCookies` for `https://ozon.by/` omitted it when the attached
tab was not on ozon; `Network.getAllCookies` returned it. The transport
keeps that first-party cookie plus the eight unpartitioned names, and
drops every other site's cookies.

On a challenge the jar is re-read from CDP and the request is retried
**once**, after exponential backoff. If that challenge was a 403 with
`ozon-antibot: 1` and the call had used profile hints, the retry sends
the minting browser's UA instead. A second consecutive challenge, a
third challenge in the session, or a `429` cools the session down; later
calls raise and do not send. It is not retried in a loop.

#### Checked through the client (2026-10-16)

`OzonClient(transport="cookiejar")` on this host, seven GETs, every status
200. Impersonation profile `chrome146`. UA client hints came from the live
Chrome/153 page. This is the same IP as the probe, not a second IP, and not
a leave-one-out.

| method | HTTP | sanity |
|---|---|---|
| `search("iphone 17")` | 200 | 8 tiles; first SKU `3756385046` at `5 358,40 BYN` |
| `product("3094054833")` | 200, 200 | price `5 017,63 BYN`, 29 characteristics, `reviews_count` 47, description HTML 1254 chars |
| `category("elektronika-15500")` | 200 | 8 tiles |
| `reviews("3094054833", sort="score_desc")` | 200 | total 47, 30 on the page, active sort `score_desc`, score 4.7 |
| `questions("3094054833")` | 200, 200 | `n` 10, `total` 35 (the extra GET resolves the bare SKU) |

`product` calls the entrypoint twice: screen 2 is where the characteristic
table lives. No method fell back to `BrowserOracle`. That run used the
live Chrome/153 UA. That is the current cookie-jar default
(`ua_source="browser"`, also spelled `auto`): the UA of the browser that
minted the jar. It is what passes.

#### Profile hints are opt-in, and they 403 here

`ua_source="profile"` (Chrome/146 UA, `sec-ch-ua` 146, platform `macOS`,
TLS still `chrome146`, same nine-cookie jar) is not the default. Sent at
`search` on this host it returned **403** with `ozon-antibot: 1`, incident
`fab_20261016114137_01M528914ZZJMH5VATWFBH85YH`. The jar is UA-bound, so
those hints do not pass while the minting browser is Chrome/153. On a 403
while profile hints are in use, the client retries **once** with the
minting UA, then cools the session down. It does not retry again. The
same search, same jar, same TLS profile, with that Chrome/153 Linux UA,
returned **200**.

UA/TLS consistency is **not** achievable here. The live browser is
Chrome/153; the newest curl_cffi desktop profile is `chrome146`. The
client chooses the UA that passes over the UA that matches the TLS
profile. That is a known detectable inconsistency, not a solved problem.
Detail: [ANTI-DETECTION.md](ANTI-DETECTION.md).

The browser oracle, same IP, same afternoon: `search` 8 tiles,
`category` 8 tiles, `product` price `5 000,40 BYN` (the earlier
`5 017,63 BYN` has moved), 29 characteristics, `reviews_count` 47,
`reviews` total 47, `questions` `n` 10 / `total` 35, `summary` 200.
`questions` after `product` was 1 wire GET; the slug-resolution GET was
served from the 90s cache.

#### Untested — do not assume these work

- Which subset of the nine names is sufficient. No leave-one-out was run.
- Plain `requests` or `httpx` (no TLS impersonation) plus the same jar.
- Whether the jar works from a different IP. The proof is same-IP only.
  The probe's egress was a Dutch address (`83.142.30.241`, `loc=NL`), not
  the RU/BY residential exits mentioned in older notes.
- Operational TTL. Declared `Expires` is about a year for `abt_data` and
  the auth cookies, about 31 days for `cookie_settings`, and `xcid` is a
  session cookie in Chrome. No delayed replay was done. Do not treat the
  year-long `Expires` as a measured clearance lifetime.
- `requests` with no jar, and `curl_cffi` from a RU/BY residential exit,
  were not retested on 2026-10-16. Those older 403 notes are not overturned.

---

## Install

```bash
cd ozon-client
python3 -m venv .venv && source .venv/bin/activate
pip install -e .
```

That gives you the `ozon` command. Without installing, run the CLI as a module:

```bash
PYTHONPATH=src python3 -m ozon_client <command>
```

Requires Python 3.10+. Dependencies are `typer` and `rich` for the CLI. The
library core stays importable without `curl_cffi`. Browser-free mode is an
optional extra: `pip install 'ozon-client[browserfree]'`.

---

## Quickstart

**1. Start a Chrome with a debug port** (or reuse the one from recon):

```bash
google-chrome --remote-debugging-port=9222 --user-data-dir=/tmp/ozon-profile
```

**2. Warm the session** — land on the origin so the antibot clears:

```bash
ozon warmup
```

**3. Use it:**
```bash
ozon status                           # is the session usable?
ozon search "iphone 17"               # product table
ozon search "iphone 17" -p 2          # page 2
ozon product 3503914313               # product card
ozon category elektronika-15500 -p 2  # category listing
ozon reviews 3030630669               # reviews (30/page)
ozon cart                             # cart page (read-only)
```

Every command takes `--json` for machine consumption:

```bash
ozon search "наушники" --json | jq '.products[0]'
```

> If a call reports `fetch failed in page`, the browser tab navigated away or
> the session expired. `ozon warmup` restores it — that is the designed
> recovery, and it is what the CLI tells you to run.

Browser-free mode is opt-in and still needs that Chrome **once** to mint
cookies: `ozon --transport cookiejar search "iphone 17"`. Cookie names, the
exact header set, and what is **not** proven are in
[Browser-free mode](#browser-free-mode).

---

## Library

```python
from ozon_client import OzonClient

c = OzonClient()                       # default transport: browser oracle
# c = OzonClient(transport="cookiejar")  # curl_cffi; Chrome mints cookies once

c.warmup()                             # establish clearance
assert c.ready()                       # probe the cheapest gated endpoint

r = c.search("iphone 17", page=2)
for p in r["products"]:
    print(p["sku"], p["name"], p["price"], p["rating"], p["reviews"])

card = c.product("3094054833")          # price, description_html, characteristics
print(card["price"]["price"], card["heading"], len(card["characteristics"]))
revs = c.reviews("3094054833", sort="score_desc")
print(revs["total"], revs["score"], revs["sort"], revs["sortings"])
qs = c.questions("3094054833", qsort="usefulness_desc")
print(qs["n"], qs["total"], qs["questions"][0]["text"])
```

`OzonClient` is a context manager and uses **relative API paths only** — the
only absolute host is the configured `--base`.

### Return shapes

`search` (and `category`, which has `category` instead of `query` / `page` /
`location`):

```python
{"query", "page", "seo", "location", "pageInfo",
 "products": [{"sku", "name", "price", "original_price", "discount",
               "rating", "reviews", "url", "images"}],
 "widget_count",
 "filters": [{"title", "filters": [{"type", "key", "title"}]}],
 "sort_options": [{"name", "link", "is_selected"}],
 "active_filters": [{"key", "name", "ftype",
                     "values": [{"title", "disable_uri"}]}],
 "next_url"}
```

`price` on a tile is the `priceV2` entry with `textStyle == "PRICE"`.
`original_price` and `discount` come from the same atom. Search tiles often
carry a second `priceV2` that is only an installment (`363 BYN × 12 мес`,
`styleType=ACTUAL_PRICE`); that atom loses to the sale price. If the tile
has no `priceV2` at all, `price` falls back to the currency-text heuristic
and the two new fields are `None`.

`product`:

```python
{"sku", "seo", "title", "heading", "description", "description_html",
 "price": {"price", "original_price", "show_original_price",
           "is_available", "disclaimer"},   # dict, not a string
 "original_price",                            # flat alias of price.original_price
 "gallery": {"cover_image", "images": [{"src", "alt"}], "video_cover"},
 "gallery_images",                            # flat alias of gallery.images
 "short_characteristics": [{"id", "name", "values", "hint"}],
 "characteristics": [{"key", "name", "values", "copy_text", "hint"}],
 "brand": {"name", "url", "trust"},
 "seller": {"name", "url", "rating", "trust_factors"},
 "seller_rating",                             # flat alias of seller.rating
 "review_score": {"total_score", "reviews_count", "url"},
 "reviews_count",                             # flat alias of review_score.reviews_count
 "question_count": {"text", "count", "url"},
 "aspects": [{"name", "key", "type",
              "variants": [{"sku", "link", "text", "price", "active",
                            "availability"}]}],
 "location", "tiles", "pageInfo", "widget_count"}
```

The current price string is `price["price"]` (for example `"5 017,63 BYN"`).
`original_price`, `gallery_images`, `seller_rating`, and `reviews_count` are
flat aliases of the nested fields; the nested objects stay. Listings use
`active_filters` (plural), not `active_filter`.

`title` / `description` stay the SEO strings. `heading` is
`webProductHeading`. `description_html` is `webDescription.richAnnotation`
and `characteristics` is the full `webCharacteristics` table — both live on
layout page 2. The client follows `paginator.nextPage` once
(`layout_container=pdpPage2column&layout_page_index=2`; `start_page_id` is
kept). A `tab` parameter on that URL is stripped before the request: `?tab=`
returns screen 1 and would silently drop the description and the
characteristics. If that fetch fails, those two fields are `None` and
`product()` still returns.

`reviews`:

```python
{"sku", "seo", "total", "score", "sort",
 "sortings": [{"name", "value", "active"}],
 "paging": {"page", "per_page", "has_next"},
 "reviews": [{"uuid", "author", "published_at", "rating", "title", "text",
              "positive", "negative", "photos", "videos", "usefulness",
              "comments_count", "itemId", "status", "is_edited"}]}
```

`sort` is a `webListReviews.sortings[].value` (`usefulness_desc`,
`score_desc`, `score_asc`).

`questions`:

```python
{"sku", "qsort",
 "questions": [{"uuid", "item_id", "author", "created_at", "text", "text_html",
                "answers": [{"uuid", "author", "created_at", "text",
                             "text_html", "reactions"}],
                "reactions", "product": {"name", "url", "image"}}],
 "sortings": [{"title", "value", "url"}],
 "total", "n", "pageInfo", "widget_count"}
```

`qsort` is `created_at_desc`, `usefulness_desc`, `has_answers_desc` or
`has_answers_asc`. `text` is plain; `text_html` keeps the raw markup. A bare
SKU is resolved through the product page to `/product/<slug>/questions/`.
Vote and create actions in the payload are not called.

---

## Architecture

```
src/ozon_client/
  client.py     facade — the public entry point
  catalog.py    search / product / category / reviews / questions + tile parsers
  session.py    summary / cart / favourites / address-bar / menu
  http.py       BrowserOracle — CDP transport, response model, error mapping
  cookiejar.py  CookieJarTransport — curl_cffi replay of the CDP cookie jar
  auth.py       Signer — x-o3-* headers for both transports
  throttle.py   token-bucket rate limiter
  exceptions.py typed, actionable error hierarchy
```

Two deliberate seams:

- **`auth.py` is pluggable.** It supplies the `x-o3-*` headers. The
  clearance itself is the cookie jar (Hybrid / Method 4), not a signed
  header. `signer_for(6)` still returns those headers and `signer_for(0)`
  returns none — the integer is a historical selector, not a "non-portable
  clearance" finding. A future bearer or HMAC signer can drop in beside them.
- **The transports own the wire.** Domain modules never touch CDP or curl.
  `OzonClient(transport="browser"|"cookiejar")` picks one (default
  `browser`). Retry, error mapping and rate limiting live on the transport.
  A 403 from the antibot is not retried in a loop. Cookie-jar mode re-mints
  from CDP once, then cools down the same way the browser oracle does.

---

## Anti-detection

This client is meant to run from **one fixed IP**, slowly, looking like one
browser. It is not a rotator and it does not solve challenges itself.
Detail, including what is still obvious to a detector:
[ANTI-DETECTION.md](ANTI-DETECTION.md).

**One client story, with one hole we cannot close.** `OzonClient()` stays
on the in-page browser. That path is real Chrome: TLS, UA, cookies, and
JS all belong to the same process. Cookie-jar mode is opt-in. Its TLS
profile is still the newest curl_cffi desktop Chrome (`chrome146` on
0.15.0), but its UA defaults to the browser that minted the jar
(Chrome/153 here). Matching the profile instead 403s. `x-page-view-id`
and `x-o3-parent-requestid` stay put for one document (a PDP layout slice
included) and rotate on the next document. `x-page-previous` is the
previous page type (`home`, `search`, `pdp`, …) or empty on the first view.

**Randomized.** The gap between requests is the token wait plus
`uniform(0.35, 1.15)` seconds, so it is not a metronome. Page-view ids are
fresh per document. Nothing else is randomized: no proxy, no UA lottery.

**Low-and-slow.** `OzonClient()` is 0.5 request/s, burst 1 (serialized).
`burst > 1` is how you opt into a short burst; do not do that on one IP.
`ozon --rate` still defaults to 2 because that flag is on the CLI; jitter
and burst 1 still apply. `warmup()` visits home, then an optional search,
then a deep URL. Call it before product, reviews, or questions. The
cookie-jar referer follows that trail.

**Fewer GETs, no batch POST.** `product()` is still two entrypoint GETs:
screen 1 has the price, screen 2 has the description and the full
characteristic table. `questions(sku)` still resolves the slug from the
product document, then fetches the questions document.
`POST /api/composer-api.bx/widget/json/v2/batch` is not used — it is a
POST, and the inventory does not show it is read-only. A 90-second
in-memory GET cache skips a document this process already fetched, so
`questions()` after `product()` for the same SKU does not repeat the
product GET.

**Challenges stop the session.** JSON descriptor, `ozon-antibot`, or
masked HTML with an incident id counts even when the status is not 403.
One retry, then a cool-down. If that 403 carried `ozon-antibot: 1` and
the request was using profile hints, the single retry switches to the
minting browser's UA. It does not retry again. No hammering.

---

## Rate limiting

Both transports share a token bucket (`throttle.py`). Library default is
**0.5 req/s, burst 1**, plus a random pause on every take. Reassigning
`client.throttle` also repoints the transport, so a shared budget really
is shared:

```python
from ozon_client.throttle import TokenBucket
shared = TokenBucket(rate=0.5, burst=1)
a = OzonClient(); a.throttle = shared
b = OzonClient(); b.throttle = shared      # same bucket, same budget
```

`TokenBucket(rate=0)` disables limiting and jitter (CDP cookie reads, and
the one-shot CLI commands that pass `--rate 0`). `burst > 1` is the
opt-in for a short burst. The old 2 req/s burst 8 setting is how the
2026-10-15 ladder was shaped; it is not the default anymore.

`429` raises `RateLimited` (with `retry_after` when sent) and cools the
session down — it is not retried. `5xx` and connection failures retry with
exponential backoff and jitter. A challenge is not retried in a loop.
Cookie-jar mode re-reads the jar once, then stops.

---

## Errors

Errors are typed so a caller (human or agent) can recover without reading
tracebacks:

| Exception | Meaning | Recovery |
|---|---|---|
| `AntibotBlocked` | 403 from the antibot | `ozon warmup`, then retry. Carries `incident_id`. |
| `RateLimited` | 429 | Lower `--rate`; honour `retry_after`. |
| `AuthRequired` | 401/403 on a gated endpoint | Log in inside the warm browser profile. |
| `NotFound` | 404 | Check the slug/SKU. |
| `TransportError` | CDP unreachable / browser gone | Start Chrome with `--remote-debugging-port=9222`. |
| `ParseError` | Response shape changed | The envelope format moved; update the parser. |

The CLI turns each into a one-line diagnostic plus the exact next command.

---

## Scope: read-only, by design

**Every method in this client is a read.** There are no mutating commands —
not because writes were hard, but because they were out of scope and carry
real-world consequences (placing orders, spending money, altering accounts).

If write support is added later it must be:

- **plan-by-default** — print the intended mutation and require an explicit
  `--execute` flag to send anything;
- confined to `session.py` behind a clearly named `mutations.py` boundary;
- never reachable from an unattended scheduled run.

---

## Scope limits

- **Cookie-jar mode still needs Chrome once.** The clearance travels in the
  cookie jar on the same IP (`audit/antibot_probe.md`), but a cold client
  cannot mint it. The default transport is the in-page browser oracle, which
  needs Chrome on every call. A different IP, plain `requests`, and the real
  lifetime of the jar are untested — see
  [Browser-free mode](#browser-free-mode).
- **Parsers are heuristic where the API has no flat fields.** Tile name and
  rating are recovered from `mainState` atom text. Price prefers the
  `priceV2` atom (`textStyle=PRICE`, plus `ORIGINAL_PRICE` and `discount`)
  and only falls back to the currency-token heuristic when that atom is
  absent — so an installment line (`363 BYN × 12 мес`) does not beat the
  real price. A decimal rating is preferred over a bare integer (a lone `1`
  is usually a quantity); a token is a name only if it is not noise
  ("отзыв", "хит", …). Tile shelves named `tileScrollDesktop`, `skuGrid`
  and `skuShelfGoods` are parsed alongside `tileGrid*`. Layout changes will
  move fields — `widget_count` is returned on every response to make that
  observable.
- **`--base` is untested against `www.ozon.ru`.** All verification was done on
  `ozon.by`. The RU host should work — the API surface is the same — but the
  currency/price parsing was tuned for BYN.
- One Chrome tab at a time; the oracle reuses the active tab rather than
  opening new ones per request.

---

## Verification status

All read paths were exercised against the live site and return real data:

| Path | Result |
|---|---|
| `search` | 8 tiles/page. Price is the sale `priceV2` (`3 939,38 BYN`, original `11 576,75 BYN`, `−65%`), not the `× 12 мес` installment atom. Filters, six sort options, active filters and `next_url` are returned |
| `search --page 2/3` | distinct SKUs per page |
| `product` | SKU `3094054833`: price `5 017,63 BYN`, heading, 12 gallery images, `description_html` (1254 chars), 29 characteristics. A failed page-2 fetch leaves `description_html` and `characteristics` as `None` |
| `category` + pagination | tiles keep `price` / `original_price` / `discount`; filters and sort options too |
| `reviews` | 30/page with photos, usefulness, `itemId`, status. `sort=score_asc` is active and the first reviews are 1★ |
| `questions` | SKU `3094054833`: `n=10`, `total=35`, answers present, plain `text` plus `text_html`. No vote/create call |
| `cart` / `favorites` / `menu` / `summary` | 200, envelopes parsed |

---

## Endpoint inventory

Machine-readable list: [`endpoint_inventory.json`](endpoint_inventory.json). One object per distinct endpoint (method, path template, params, purpose, response shape, plus source / implemented / verified / write).

| | count |
|---|---|
| Total endpoints | 106 |
| Implemented in `src/ozon_client/` | 4 |
| Verified live (response body in `audit/raw/` or the fetch logs) | 1 |
| Writes | 72 |

All 105 paths from `audit/bundle_strings.json` are in the file. The extra row is `POST /api/composer-api.bx/_action/v2/addressBookBarTooltip`, which the client already calls and which is not a string in the scanned bundles. Page URLs are not separate endpoints: `GET /api/entrypoint-api.bx/page/json/v2` is one row, and the observed page types are in its `purpose`.

`verified_live` is stricter than the table above. `summary`, `menu`, and the address-bar tooltip returned 200 when exercised, but those bodies were not saved under `audit/raw/` or the fetch logs, so only the entrypoint GET is `verified_live: true`.

---

## Page coverage

Full table, return shapes, and the live proof log: [`COVERAGE.md`](COVERAGE.md).

`OzonClient.page(url)` is the escape hatch: any public path through `GET /api/entrypoint-api.bx/page/json/v2`, with `widgetStates` double-decoded. CLI: `ozon page <url> --json`.

Specialized reads added on top of that GET (login, cart, favourites, orders, and every write stay out):

| method | what it returns |
|---|---|
| `brand` / `seller` / `highlight` | tiles, filters, sort options, active filters, `next_url`, shop header when present. `page`, `sorting`, `filters` match search |
| `brands` / `sellers` | `/brand/` directory and `/seller/` shop cards. Sellers paginate with `cursor=next_url` |
| `similar` | analogs modal for a SKU |
| `media` | review photo/video tab |
| `features` | characteristic table (`/features/`) |
| `review_stats` | star histogram and buyer-context stats (`variant="all"` or `"this"`) |
| `availability` | `webPrice.isAvailable`. `webDelivery` is empty without a POST this client does not send |
| `search` / `category` | optional `sorting` and `filters` (GET only). Return keys unchanged |
| `questions` | optional `cursor` (`next_url` from the previous page; not `?page=`) |
| `reviews` | `page=N` already worked; page 2 re-checked (17 of 47) |

The inventory counts above are unchanged: these parsers are still the one entrypoint row (`implemented` and `verified_live` were already true). Sixteen live GETs on 2026-10-16 all returned HTTP 200. Reference SKU `3094054833` came back with 29 characteristics, score 4.7 / 47 reviews, 35 questions, and price `5 000,40 BYN` (the earlier `5 017,63 BYN` figure had moved).
