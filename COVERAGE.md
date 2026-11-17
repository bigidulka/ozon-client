# Public read coverage

Coverage is page types rendered by one GET, not 106 separate endpoints.

```
GET /api/entrypoint-api.bx/page/json/v2?url=<encoded path>
```

`OzonClient.page(url)` double-decodes every `widgetStates` value and returns `layout`, `seo`, `pageInfo`, and `location`. Tokens (`userToken`, `pageToken`, `requestID`) are dropped. Specialized parsers below are thin views over that same GET, plus one approved POST (`review_comments`). No login, no cart or favourite writes.

Dumps cited are `audit/raw/`. Live checks on 2026-10-16 used the browser transport on CDP `:9222` (16 GETs, all HTTP 200). Reference SKU `3094054833`.

## Method counts

| surface | before | after |
|---|---|---|
| `OzonClient` data methods | 11 (`search`, `product`, `category`, `reviews`, `questions`, `summary`, `cart`, `favorites`, `address_bar`, `menu_children`, `search_suggest`) | 25 |
| CLI commands | 11 | 25 |
| `endpoint_inventory.json` rows with `implemented: true` | 4 | 5 |
| rows with `verified_live: true` | 1 | 2 |

Implemented rows: entrypoint GET (already verified), `summaryV2`, `shellHorizontalMenuGetChildV1`, `addressBookBarTooltip` (implemented, not re-verified here), and `rpGetCommentsByReviewUuid` (the new verified POST). `GET /api/location/v2/current` and `GET /api/location/v2/search` were called and returned **404** on `ozon.by`; those two flags stay false.

New client methods: `page`, `brand`, `seller`, `highlight`, `brands`, `sellers`, `similar`, `media`, `features`, `review_stats`, `availability`, `location_current`, `location_search`, `review_comments`.

`search` and `category` gained optional `sorting` and `filters` (default calls are unchanged). `questions` gained optional `cursor` and an extra `next_url` field. Existing keys on `search`, `product`, `category`, `reviews`, `questions`, and `summary` are otherwise the same.

## Page types

Parser column: a dedicated method, `page()` only, or out of scope. Login-gated rows were not implemented.

| page type | example URL | data widgets | parser |
|---|---|---|---|
| home | `/?__rr=1` | `tileGridDesktop`, `advBanner`, `seasonWidget`, `paginator` | `page()` |
| search (predicted category) | `/search/?text=iphone+17&from_global=true` | `tileGridDesktop`, `filtersDesktop`, `searchResultsSort`, `searchResultsFiltersActive`, `infiniteVirtualPaginator` | `search()` |
| category | `/category/elektronika-15500/` | same listing widgets, plus `horizontalCategoryMenu`, `objectLine`, `objectThumbnailList`, `resultsHeader` | `category()` |
| category page N | `/category/elektronika-15500/?page=2` | same | `category(page=2)` |
| brand shop | `/brand/apple-26303000/` | listing widgets, `sellerTransparency`, `bannerCarousel`, `sharingLink` | `brand()` |
| brand directory | `/brand/` | `brandListResults`, `brandListFilter`, `brandListCaption` | `brands()` |
| highlight | `/highlight/apple-4442805/` | listing widgets, sometimes `banner` / `objectLine` | `highlight()` |
| highlight index | `/highlight/` | none | **404** (audit). Do not call |
| seller shop | `/seller/ozon/` | listing widgets, `sellerTransparency`, `banner` | `seller()` |
| seller directory | `/seller/` | `mallFeed`, `paginator` | `sellers()` |
| product card | `/product/<slug-or-sku>/` | `webPrice`, `webGallery`, `webProductHeading`, `webShortCharacteristics`, `webCharacteristics` on layout page 2, `webDescription`, `webBrand`, `webCurrentSeller`, `webAspects`, `webReviewProductScore`, `webQuestionCount` | `product()` |
| features tab | `/product/<slug>/features/` | `webCharacteristics` (`totalCount`) | `features()` |
| reviews list | `/product/<slug>/reviews/?page=N&sort=` | `webListReviews` | `reviews()` |
| reviews legacy | `/reviews/<sku>/` | `webListReviews` (no tabs) | `reviews()` fallback on 404 |
| reviews fragment | `/product/<sku>/reviews/pdp-part?reviewsVariantMode=2` | `webReviewProductScore` histogram, `contextQuestionsStatistic`, `webReviewsVariantMode`, `webListPhotos` | `review_stats()` |
| questions | `/product/<slug>/questions/` | `webPDPListQuestions`, `paginator` (`page_key`) | `questions()` |
| question detail | `/product/<slug>/question/<uuid>` | PDP chrome only, no question body | **dead end** (audit). No parser |
| review media | `/product/<slug>/videos/` | `webReviewGallery` | `media()` |
| similar items | `/modal/similar-products?product_id=<sku>` | `webMobTabs`, `tileGridDesktop` | `similar()` |
| PDP layout slices | `?layout_container=pdpPage2column&layout_page_index=2` (also `BottomShelfs`, `pdp-web-second-analogs-shelf`) | description, full specs, shelves | `product()` follows page 2. Other slices: `page(next_url)` |
| filters modal | `/modal/allFilters/category/elektronika-15500/` | `filtersDesktop` | `page()`. Listing methods already return filter keys |
| availability | product screen 1 | `webPrice.isAvailable`, `webSale.offer`. `webDelivery` is `{}` | `availability()` |
| search suggestions | `/searchSuggestions/search/?text=` | `webSuggestions` | existing `search_suggest()` (seo + widget count only) |
| business landing | `/business` | `customHtml` | `page()` |
| pickup map | `/info/map/` | `addressEditMap`, `cityFilter`, `countryList` | `page()` |
| compare | `/product/compare` | `webCompare` empty when anonymous | `page()`. Not a catalogue |
| buy again | `/buyAgain` | `skuGrid`, `skuShelfGoods` (personalized; anonymous is thin) | `page()` |
| cart | `/cart` | `emptyCart` when anonymous | **out of scope** (account) |
| favourites | `/my/favorites/` | tiles only with a logged-in session | **out of scope** |
| selections | `/selections/list` | `statusWidget` | **out of scope** |
| wishlists | `/my/favorites/lists` | `statusWidget` | **out of scope** |
| favourite sellers | `/my/favorites/sellers` | `mallFeed` of the user's shops | **out of scope** |
| account home | `/my/main` | `login`, `menu` | **out of scope** |
| orders | `/my/orderlist/` | `loginButton`, `myGuest` | **login-gated**. No order rows |
| chat | `/my/chat/` | `loginButton`, `myGuest` | **login-gated** |
| points | `/my/points/` | `loginButton`, `myGuest` | **login-gated** |
| account FAQ | `/my/questions/` | `customHtml` (not product Q&A) | **out of scope** |
| cookie settings | `/my/cookies` | `gdprCookiesManagement` | **out of scope** |
| address modal | `/modal/addressbook?set_sm=1` | `commonAddressBook` | not implemented. Existing `address_bar()` is a POST and was not re-tested |
| currency modal | `/modal/selectLanguageCurrency` | `currencyLanguageSelector` | `page()` |
| lower-price modal | `/modal/web_pdp_lower_price?product_id=<sku>` | `webPriceDecreasedFullView` | `page()` |
| seller rating modal | `/modal/shop-in-shop-rating-popover` | `banner`, `textBlock` | `page()` |

`?tab=` on a product URL does not change the widget set. It is not sent.

## Return shapes

Tile (`products[]` on search, category, brand, seller, highlight, similar, and seller-directory cards):

```
{sku, name, price, original_price, discount, rating, reviews, url, images[]}
```

`page(url) -> {layout, widgetStates, seo, pageInfo, location}`

`widgetStates` values are objects (JSON strings decoded, up to three times). Keys stay `<family>-<id>-<container>-<n>`.

`brand` / `seller` / `highlight` / `catalog.listing`:

```
{
  kind, slug, path, page, sorting, seo, page_type, url,
  header: {name, logo, badges[], share_url} | null,
  results: {title, subtitle} | null,
  products: [tile],
  links: [{title, url, image, source}],
  filters: [{title, filters: [{type, key, title}]}],
  sort_options: [{name, link, is_selected}],
  active_filters: [{key, name, ftype, values: [{title, disable_uri}]}],
  next_url, widget_count, pageInfo
}
```

`sorting`: `score` (default), `new`, `price`, `price_desc`, `rating`, `discount`. `filters` is a dict of GET query pairs, e.g. `{"is_promo": "t"}`. `page` is `?page=N` (page 1 omits it).

`brands()`:

```
{seo, page_type, groups: [{name, url, brands: [{title, url}]}], n_groups, n_brands, links, pageInfo, widget_count}
```

`sellers(cursor=None)`:

```
{seo, page_type, url, shops: [{name, url, logo, badges[], products: [tile]}], n, next_url, pageInfo, widget_count}
```

Pass `next_url` back as `cursor`. There is no proven `?page=` on `/seller/`.

`similar(sku)`:

```
{sku, tabs[], active_index, products: [tile], n, next_url, page_type, pageInfo, widget_count}
```

Tabs seen live: `Аналоги`, `Похожие по фото`. Only the first tab has tiles. The second tab has no URL in the payload.

`media(sku)` — review photos and videos, not the PDP gallery (`product().gallery` is that):

```
{
  sku, seo, total, page, per_page,
  media: [{type, url, alt, rating, uuid, review_uuid, author, width, height}],
  n, next_url, page_type, pageInfo, widget_count
}
```

There is no `page` argument. `rgPage` is a field in the response, not a proven query parameter, and this SKU's gallery fits in one page (`14` ≤ `per_page` 15).

`features(sku)`:

```
{
  sku, seo, total, n,
  characteristics: [{key, name, values[], copy_text, hint}],
  price: {price, original_price, show_original_price, is_available, disclaimer} | null,
  is_available, page_type, pageInfo, widget_count
}
```

`review_stats(sku, variant="all"|"this")`:

```
{
  sku, variant, total_score, reviews_count,
  histogram: [{title, value}],
  context: [{title, popular, answers: [{title, percentage}]}],
  photos: [{type, preview_url, uuid}],
  tabs: [{title, url}], selected_tab, page_type, pageInfo, widget_count
}
```

`variant="all"` sends `reviewsVariantMode=2`. `variant="this"` sends `1`.

`availability(sku)`:

```
{sku, is_available, price, original_price, offer_available, delivery_empty, delivery, page_type, pageInfo, widget_count}
```

`delivery` is null while `webDelivery` is `{}`. Delivery slots were not pursued: the suspected fill is POST `widget/json/v2`, which stays a write.

`review_comments(review_uuid, sku, root_sku=None, limit=10, offset=0)` is the only POST added for catalogue reads (`rpGetCommentsByReviewUuid`). Body is `{reviewUuid, sku, rootSku, limit, offset}`. It does not create, vote, or delete. `address_bar()` was already a POST of an empty JSON body and was not changed.

```
{review_uuid, sku, root_sku, limit, offset, comments: [{uuid, author, text, created_at, parent_uuid, root_parent_uuid}], n}
```

`location_current()` and `location_search(text)` call `GET /api/location/v2/current` and `GET /api/location/v2/search?query=`. On `ozon.by` both returned HTTP 404 (2026-10-16). The methods are present and raise `NotFound`. Inventory flags were not set.

`questions(..., cursor=None)` adds `next_url` (paginator `nextPage`, includes `page_key`). Page 2 is `questions(sku, cursor=next_url)`, not `?page=`.

`search` / `category` return shapes are unchanged. New keyword-only arguments: `sorting`, `filters`.

`reviews(sku, page=N, sort=)` was already paginated (`?page=` and `sort=usefulness_desc|score_desc|score_asc`). Re-checked, not rewritten.

## CLI

```
ozon page /brand/apple-26303000/ --json
ozon search "iphone 17" --sorting price --filter is_promo=t
ozon category elektronika-15500 --page 2
ozon brand apple-26303000
ozon seller ozon
ozon highlight apple-4442805
ozon brands
ozon sellers
ozon similar 3094054833
ozon media 3094054833
ozon features 3094054833
ozon review-stats 3094054833 --variant all
ozon availability 3094054833
ozon questions <slug-or-url> --cursor '<next_url>'
ozon reviews 3094054833 --page 2
ozon review-comments <review-uuid> --sku 3094054833
ozon location
ozon location-search "Минск"
```

`--json` on `page` prints the decoded envelope. Without it, the command prints `pageType`, seo title, and widget families only.

## Live proof (2026-10-16)

All rows are one GET except where noted. Status is the entrypoint response.

| call | status | sanity |
|---|---|---|
| `page(/product/...3094054833/)` | 200 | `pageType=pdp`, 80 widgets, `webPrice` and `webGallery` present, `webDelivery` empty |
| `brand("apple-26303000")` | 200 | header `Apple`, 38 tiles, 6 sorts, 2 filter sections, `page_type=brand` |
| `seller("ozon")` | 200 | header `Ozon`, 38 tiles, `page_type=seller` |
| `highlight("apple-4442805")` | 200 | 8 tiles, 6 sorts, `page_type=highlight` |
| `brands()` | 200 | 58 groups, 1313 brands (first `İdea Derma`) |
| `sellers()` | 200 | 6 shops, first `lady & gentleman` → `/seller/lady-gentleman-city/`, 4 tiles on that card |
| `similar(3094054833)` | 200 | 15 tiles, tabs `Аналоги` / `Похожие по фото` |
| `media(3094054833)` | 200 | 14 items, `total=14`, `page=1`, `per_page=15`, first type `IMAGE` |
| `features(3094054833)` | 200 | 29 / `totalCount` 29, first row `Артикул`, price `5 000,40 BYN` |
| `review_stats(3094054833)` | 200 | score `4.7`, 47 reviews, 5 histogram rows, 3 context questions, 9 photos |
| `availability(3094054833)` | 200 | price `5 000,40 BYN`, `is_available=true`, `offer_available=true`, `delivery_empty=true` |
| `search("iphone 17", sorting="price", filters={"is_promo":"t"})` | 200 | 36 tiles, selected sort `Дешевле`, active keys `is_promo` and `brand` (brand is the site's category prediction, not a filter this call sent), first price `3 056,22 BYN` |
| `category("elektronika-15500", page=2)` | 200 | 8 tiles, `next_url` set |
| `reviews(3094054833, page=2)` | 200 | 17 reviews, `total=47`, `paging.page=2`, `has_next=false` (30 + 17) |
| `questions(<product questions url>)` | 200 | `n=10`, `total=35`, `next_url` set |
| `questions(cursor=next_url)` | 200 | `n=10`, first uuid differs from page 1. One extra GET |

Price drift, not a parser bug: SKU `3094054833` was `5 017,63 BYN` in the audit and is `5 000,40 BYN` live. Characteristic count (29), review total (47), and question total (35) still match. Do not treat the price change as a broken parser.

### Regression of the original six (default arguments)

| call | status | sanity |
|---|---|---|
| `search("iphone 17")` | 200 | 8 tiles, `filters` and `sort_options` still present |
| `product(3094054833)` | 200 | sku matches, price `5 000,40 BYN`, 29 characteristics, gallery present |
| `category("elektronika-15500")` | 200 | 8 tiles, `filters` present |
| `reviews(3094054833)` | 200 | 30 reviews, total 47, page 1, sort `usefulness_desc` |
| `questions(<questions url>)` | 200 | 10 questions, total 35, text present. No `cursor` |
| `summary()` | 200 | `{}` |
| `review_comments` (one review with `comments_count=1`) | 200 | 1 comment, author present, text present. The single POST |
| `location_current` / `location_search("Минск")` | 404 | `NotFound`. Flags left false |

## Dead ends (not guessed)

- `webDelivery` on the reference PDP is `{}` for this anonymous session. No dates, no pickup points. POST `/api/composer-api.bx/widget/json/v2` was not sent and will not be.
- Question-detail URLs do not contain the question body in the audited envelope.
- `/highlight/` with no slug is a 404 in the audit. Not re-fetched.
- Similar-modal tab "Похожие по фото" has no separate GET in the widget.
- Review-gallery paging fields are `total` / `rgPage` / `perPage`. No `page` argument: `rgPage` was not assumed to be a query parameter.
- `GET /api/location/v2/current` and `GET /api/location/v2/search?query=Минск` are HTTP 404 on `https://ozon.by`. Not marked implemented.
- Layout-slice URLs for bottom shelves and analogs still work as `page(url)` when you already have `paginator.nextPage`. `similar()` uses the stable modal URL instead of those session-tied slices.
- Login walls (`/my/orderlist/`, `/my/chat/`, `/my/points/`) return `loginButton` + `myGuest` only. Left unimplemented.
- Other read-shaped POSTs (`favoriteCheckItems`, campaign countdowns) stay out. Only `rpGetCommentsByReviewUuid` was added.

## Decisions

1. Delivery slots: no. `availability()` returning `delivery_empty=true` is the result.
2. Review-gallery pagination: no guessed `rgPage` query. `media()` returns `total` and `page` for the single page it fetched.
3. The catalogue POST added here is `review_comments` → `rpGetCommentsByReviewUuid` (`write: false`). `address_bar()` was already a POST and was left alone. No other POST was added.
4. Location GETs were added and called. Both 404 on `ozon.by`, so `implemented` / `verified_live` stay false on those rows.
