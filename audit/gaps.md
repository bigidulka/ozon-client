# Parser gaps

What the live envelopes contain versus what `src/ozon_client/catalog.py` and `src/ozon_client/session.py` keep. Line numbers match the tree at audit time. "Parsed" means the field survives in the dict the public function returns, not merely that some code walks past it.

Dumps cited are under `audit/raw/`. The iPhone card used everywhere is SKU `3094054833`.

## What we already keep

| call | kept | source |
|---|---|---|
| `search` / `category` | `seo.title`, `pageInfo`, `widget_count`, tiles via `parse_tile` | `catalog.py:200-208`, `catalog.py:240-246` |
| `search` only | `location.current` | `catalog.py:204` |
| `product` | sku regex from the URL, `seo.title`, seo meta description, `location.current`, `tileGrid*` tiles (none on PDP screen 1), `pageInfo`, `widget_count` | `catalog.py:221-231` |
| `reviews` | `paging.page/perPage/nextButton`, `paging.total` or `reviewsTotal`, scalar `productScore`, and per review `uuid`, author first/last name, `publishedAt`, `content.score`, `content.comment` (via the `text` then `comment` fallback) | `catalog.py:268-324` |
| `summary`, `menu_children`, `address_bar` | raw JSON passthrough — not structured, but not dropped | `session.py:13-25`, `session.py:56-70` |
| `cart`, `favorites`, `search_suggest` | seo title and/or `widget_count` and (cart) `pageInfo` only | `session.py:35-39`, `session.py:50-53`, `session.py:80-83` |

## Tile records (`parse_tile`)

`_TILE_WIDGET_RE` is `^tileGrid\w*` (`catalog.py:27`). A live tile (`category.json`, `tileGridDesktop`) is:

```
sku, id, isAdult, brandLogo, tileImage, action{behavior,link,params},
mainState[ priceV2 | textDS | labelListV2 ],
multiButton.ozonButton.addToCart, topRightButtons[].favoriteProductMoleculeV2
```

`priceV2` is structured, not a flat string:

```
price[]: {text, textStyle: PRICE | ORIGINAL_PRICE}
discount: "−49%"
priceStyle.styleType: SALE_PRICE
```

`parse_tile` (`catalog.py:81-153`) keeps only `sku`, a heuristic `name`, one heuristic `price`, a heuristic `rating`, `reviews`, `action.link`, `tileImage.items[].image.link`. Thrown away:

| field | where | recommendation |
|---|---|---|
| `priceV2.price[]` split by `textStyle`, plus `discount` | every `tileGridDesktop` | Read the atom with `type=="priceV2"` instead of the longest currency regex (`catalog.py:102-111`). The regex can tie PRICE and ORIGINAL_PRICE on digit count and then depends on walk order. |
| `textDS.text` ("74 ед осталось") | tile `mainState` | Stock / urgency line. |
| `labelListV2` | tile `mainState` | Badges. `_NOISE_RE` (`catalog.py:70`) treats some badge words as noise and the name heuristic drops them. |
| `multiButton` delivery date / seller icon | tile | "23 октября" style promise. Not a price. |
| `isAdult`, `brandLogo`, `id` (separate from `sku`) | tile | Keep `isAdult` at least; it gates the image. |
| `topRightButtons` favorite state | tile | Read-only flag `isFav`. Do not call `favLink` (`favoriteBatchAddItems`) — that is a write. |
| `tileScrollDesktop` shelves | `product_pdp2.json`, `pdp_analogs.json` | Same item shape, **not** matched by `_TILE_WIDGET_RE`. Extend the regex or add `tileScroll`. |
| `skuGrid`, `skuShelfGoods` | `buy_again.json` | Different widget, same idea. `_tiles` (`catalog.py:174-188`) drops them. |

`search` / `category` also drop the whole non-tile payload: `filtersDesktop`, `searchResultsSort`, `searchResultsFiltersActive`, `resultsHeader`, `tagListModal`, `infiniteVirtualPaginator.nextPage`, `horizontalCategoryMenu`, `categoryBrandList`, `objectLine` / `objectThumbnailList`.

## Product card (`product()`)

`product()` never reads a `web*` widget. Screen 1 (`product.json`, 80 widgets) has the card; screen 2 (`product_pdp2.json`) has the description. Both are discarded except seo.

| record | widget | fields we drop | change |
|---|---|---|---|
| Price | `webPrice` | `price` ("5 017,63 BYN"), `originalPrice`, `showOriginalPrice`, `isAvailable`, `disclaimerPriceHeader` | Map these directly. There is no price in the seo object we return. |
| Title | `webProductHeading` / `webStickyProducts.name` | real heading; seo title is a "купить" marketing string | Prefer the heading widget. |
| SKU | `webDetailSKU.copyText`, `webProductMainWidget.sku` | explicit sku | Use this instead of the URL regex at `catalog.py:222`. |
| Short specs | `webShortCharacteristics.characteristics[]` | `{id, title.textRs[].content, values[].text}` (5 of N) | Parse the list. |
| Full specs | `webCharacteristics` on layout page 2 and on `/features/` | `totalCount` (29), `characteristics[].short[]` `{key,name,values[].text,copyText,hintText}` | Follow `paginator.nextPage` (`layout_container=pdpPage2column&layout_page_index=2`) or GET `/product/<slug>/features/`. |
| Description | `webDescription` on layout page 2 | `richAnnotation` (HTML), `richAnnotationType`, `params.anchor` | New field `description_html`. The seo meta description (`catalog.py:224-226`) is not this text. |
| Gallery | `webGallery` | `coverImage`, `images[]` `{src,alt}` (12), `videoCover`, `similarItemsURL` | Replace empty `tiles` on a PDP. |
| Variants | `webAspects.aspects[]` | `aspectName`, `aspectKey`, `variants[]` `{sku, price, link}` | This SKU had "Состояние товара"; color/size products have more. |
| Brand | `webBrand` | title link `/brand/apple-26303000/?all_items=true`, trust text | Small struct. |
| Seller | `webCurrentSeller` | name "Ozon Россия", rating "4.9", link `/seller/ozon/`, `trustFactors[]` | Small struct. Subscribe actions (`sisUnlike`) are writes — do not call. |
| Score | `webReviewProductScore`, `webSingleProductScore` | `totalScore` 4.7, `reviewsCount` 47, link to reviews | Surface on the card. |
| Questions | `webQuestionCount` | text "35 вопросов", link `/product/<slug>/questions/` | Count + URL. |
| Labels | `webMarketingLabels.labels[].badge` | text + highlight link | Optional. |
| Installment | `webInstallmentPurchase` | sku, link | Optional. |
| Price drop | `webPriceDecreasedCompact` | link `/modal/web_pdp_lower_price?product_id=` | Modal dump: `webPriceDecreasedFullView`. |
| Hashtags / producer / attachments | `webHashtags`, `webProducerInfo`, `webAttachments` | page 2 only | Optional. |
| Photos from reviews | `webListPhotos.mediaContent[]` | preview url, review uuid, `galleryParams` | Media strip on the card. |
| Delivery | `webDelivery` | state is `{}` | Nothing to parse until the async fill is understood. Do not POST `widget/json/v2` blindly. |
| Similar shelves | `tileScrollDesktop` / bottom `tileGridDesktop` | layout page 2 and `layout_container=BottomShelfs` / `pdp-web-second-analogs-shelf` | Reuse `parse_tile` after the regex fix. |

`product()` also does not follow `webProductTabs`. Those four URLs are a separate fetch (features, reviews, questions, videos). `?tab=` does not change the payload.

## Reviews (`reviews()`)

The parser only runs if some widget has a `reviews` array (`catalog.py:273`). That is `webListReviews`, and it works for both `/reviews/<sku>/` and `/product/<slug>/reviews/`. The canonical page is the latter (`pageType=pdp_reviews`); it also has tabs, photos, and the gallery. The client hardcodes the legacy path (`catalog.py:259`).

| live field | parsed? |
|---|---|
| `uuid`, `publishedAt` / `createdAt`, `author.firstName` | yes (`catalog.py:293-296`) |
| `content.score` | yes, as `rating` (`catalog.py:288`) |
| `content.comment` | yes, as `text`, only because `content.text` is absent (`catalog.py:286`) |
| `content.title` | always null — reviews have no title (`catalog.py:287`) |
| `content.positive`, `content.negative` | dropped |
| `content.photos[]`, `content.videos[]` | dropped (a sampled review had 1 photo) |
| `content.contextQuestions` | dropped |
| `usefulness` `{useful, unuseful, userSelection}` | dropped |
| `comments` `{list, totalCount}` | dropped |
| `status`, `statusId`, `isEdited`, `isAnonymous`, `Lang` | dropped |
| `itemId` + sibling `products{}` variant (color/sku the review is about) | dropped. Reviews are cross-variant; `itemId` is often not the page SKU. |
| `sharing.url` | dropped |
| `badge`, `badgeDelivery`, `reviewLabel`, `OrderType` | dropped |

Page-level fields also dropped:

| field | widget | notes |
|---|---|---|
| `sortings[]` `{name,value,active}` | `webListReviews` | `usefulness_desc`, `score_desc`, `score_asc`. `reviews()` has no `sort` argument. |
| `filters` `{withPhotos, withMedia}` | `webListReviews` | keys only; values were null on this SKU. |
| `paging.commonTotal`, `paging.links[].urlParams` | `webListReviews` | we keep page / per_page / has_next (`catalog.py:306-310`). |
| star histogram `score[]` `{title,value}` | `webReviewProductScore` on `reviews_pdp_part` | screen-1 widget is flatter (`totalScore`, `reviewsCount`). |
| `contextQuestionsStatistic` | pdp-part | "По мнению покупателей" percentages. |
| `webReviewsVariantMode` | pdp-part | subtab the client cannot request. |
| `webReviewGallery` `{media, reviews, paging, products}` | videos page and reviews page | the "Фото и видео" tab. |
| `products{}` map of variant cards | `webListReviews` | needed to label which color a review is for. |

`reviews()` never reads `webProductTabs`, so it cannot discover features/questions/videos.

## Questions — entire domain missing

No function, no CLI command. Live list widget `webPDPListQuestions` (`product_questions.json`):

```
sorting.value / sorting.options[] {title.text, value, url}
questions[] {
  questionUuid, itemId,
  author.name.text, createdAt.text,
  text.text,            # HTML, links to /product/<slug>/question/<uuid>
  answers[] {answerUuid, author, createdAt, text},
  reactions, actions, popoverMenu
}
questionAbuseReasons, answerAbuseReasons
```

Recommend `catalog.questions(client, sku_or_url, qsort="usefulness_desc")` that walks `webPDPListQuestions` only. Do not POST `createQuestionV2` — that widget action is a write.

The single-question URL returns no question body (see inventory "Unresolved"). Do not invent a parser for it until the read path is known.

## Listings we don't model

`search()` (`catalog.py:192-208`) and `category()` (`catalog.py:234-246`) ignore:

| widget | fields | recommendation |
|---|---|---|
| `filtersDesktop` | `sections[].filters[]` `{type,key}`, `applySearchFilters`, `showAllButton` | Return filter descriptors. Keys seen: category, is_promo, delivery, currency_price, brand, brandcertified, is_official_brand_seller, type, exactmodels, country, color, isdiscount, seller. Applying one is a GET (proved `?is_promo=t`). |
| `searchResultsFiltersActive` | `activeFilters[]` `{key,name,ftype,activeValues[].disableUri}` | Echo what is currently on. |
| `searchResultsSort` | `sortButton.options[]` `{name, action.link, isSelected}` | Six sorts, query `sorting=`. |
| `infiniteVirtualPaginator` | `nextPage`, `prevPage` (includes `paginator_token`, `search_page_state`, `layout_page_index`) | `?page=N` works (`category_page2.json`) but the tokenised next URL is what the site scrolls. Surface `next_url` too. |
| `resultsHeader` | counts / titles | Optional. |
| `tagListModal.tags[]` | seo tag links | Optional. |
| `horizontalCategoryMenu.items[]` | subcategory `{title, link}` | Category children. `menu_children` is a different menu (shell). |
| `categoryBrandList` | brand list on a predicted search | Optional. |

There is no `brand()`, `seller()`, or `highlight()` even though they are the same tile+filter envelope (`brand.json`, `seller_shop.json`, `highlight.json`) plus:

| widget | pages | fields |
|---|---|---|
| `sellerTransparency` | brand, seller | seller header block |
| `sharingLink` | brand, seller | share URL |
| `banner` / `bannerCarousel` / `promoCarousel` | brand, highlight, seller | promo creatives |
| `objectLine`, `objectBannerList`, `objectThumbnailList` | category, highlight, seller, brand index | editorial rows, not `tileGrid` |
| `mallFeed` | `/seller/`, favourites sellers | shop cards |
| `brandListFilter`, `brandListResults`, `brandListCaption` | `/brand/` | brand directory |

A single `listing(path)` that runs `_tiles` plus filter/sort extraction would cover search, category, brand, highlight, and seller. Today only two path templates exist.

## Session chrome

| function | drops | lines |
|---|---|---|
| `cart` | `emptyCart` (anonymous empty state), `master`, recommendation `paginator.nextPage` (`layout_page_index=2&paginator_token=`), any future cart line widgets | `session.py:35-39` |
| `favorites` | `tabs` (4 destinations), `tileGridDesktop` items, `statusWidget`, `paginator` for `layout_container=recoms_pagination_favorites_web` | `session.py:50-53` |
| `search_suggest` | `webSuggestions.items[]` (9 entries on "iphone") | `session.py:80-83` |
| `menu_children` | raw composer envelope `{trackingInfo, data}`; nothing in the library names the categories | `session.py:65-70` |
| `address_bar` | raw `{data:{tooltipBody, trackingInfo}}` | `session.py:56-62` |

No parser for `webCompare` (`compare.json`, empty anonymous state), `skuGrid` / `skuShelfGoods` (`buy_again.json`), `gdprCookiesManagement` (`my_cookies.json`), or the pickup-map widgets (`addressEditMap`, `cityFilter`, `countryList` in `info_map.json`).

`summary()` returning `{}` matches the anonymous probe. Not a gap.

## Client surface

`OzonClient` (`client.py:65-94`) exposes search, product, category, reviews, summary, cart, favorites, address_bar, menu_children, search_suggest. Missing read methods the site actually serves: home, brand, brand index, highlight, seller, seller index, features, questions, videos, compare, buy-again, filters. Each is a GET of a path already dumped.

## Do not parse by calling

These showed up as widget actions and are writes or unproven POSTs. Leave them out of the parser:

- `createQuestionV2`, `sisLike` / `sisUnlike`, `favoriteBatchAddItems` / `favoriteBatchDeleteItems`, add-to-cart / one-click button actions
- POST `/api/composer-api.bx/widget/json/v2` (recon sample was `orderInfo`; likely how empty `webDelivery` and the question-detail body fill in — not proven safe)
- POST `getSearchTapTags`, `registerSearchEvent`, `setUserCookies`

## Suggested order of parser work

1. `webPrice` + `webProductHeading` + `webGallery` + `webShortCharacteristics` inside `product()` — biggest user-visible hole, all on the first GET.
2. Follow PDP `paginator.nextPage` once and read `webDescription` + `webCharacteristics`.
3. Teach `parse_tile` to read `priceV2` by `textStyle`, and teach `_tiles` about `tileScrollDesktop`.
4. Extend `reviews()` to `content.positive/negative/photos`, `itemId`, `sortings`, and accept `/product/<slug>/reviews/`.
5. Add `questions()` over `webPDPListQuestions`.
6. Return `filtersDesktop` + `searchResultsSort` + active filters from `search` and `category`.
