# Ozon.by page inventory

Live audit against `https://ozon.by` on 2026-10-16. Transport: warm Chrome on CDP `:9222`, in-page `fetch()` via `OzonClient` / `catalog._page_url` (GET `/api/entrypoint-api.bx/page/json/v2?url=…` only). Rate stayed at the client default (2 req/s). No cart writes, no login, no orders.

Dumps: `audit/raw/<pagetype>.json`. Each file is the decoded envelope with widget values JSON-decoded. Lists are cut to 2 items, strings to 220 chars, depth to 7 — enough to see shape, not a full catalogue. Untruncated key inventories for the widgets that matter are in `audit/shapes_detail.json`. Machine-readable family → dumps map: `audit/widget_index.json` (133 families, 56 dumps).

Widget keys look like `<family>-<id>-<container>-<n>` (`…-default-1`, or `…-pdpPage2column-2`, `…-homeBLR-2`). The family is the name before the numeric id.

## How to reproduce

```bash
cd ozon-client
PYTHONPATH=src python3 -m ozon_client warmup
PYTHONPATH=src python3 audit/_fetch.py <pagetype> '<path-including-query>'
```

`_fetch.py` only GETs the entrypoint. Examples that match the dumps (SKU/slug below is the iPhone 17 Pro card used throughout: `3094054833`):

```bash
PYTHONPATH=src python3 audit/_fetch.py home '/' '__rr=1'
PYTHONPATH=src python3 audit/_fetch.py search '/search/' 'text=iphone 17' 'from_global=true'
PYTHONPATH=src python3 audit/_fetch.py category '/category/elektronika-15500/'
PYTHONPATH=src python3 audit/_fetch.py product '/product/apple-smartfon-iphone-17-pro-esim-12-512-gb-esim-siniy-3094054833/' '__rr=1'
PYTHONPATH=src python3 audit/_fetch.py product_reviews '/product/apple-smartfon-iphone-17-pro-esim-12-512-gb-esim-siniy-3094054833/reviews/'
PYTHONPATH=src python3 audit/_fetch.py reviews_sku '/reviews/3094054833/'
PYTHONPATH=src python3 audit/_fetch.py cart '/cart'
PYTHONPATH=src python3 audit/_fetch.py favorites '/my/favorites/'
```

Layout-page URLs are not stable across sessions (`start_page_id`, `sh`). Take `paginator.nextPage` from the parent dump and pass that path back to `_fetch.py`. The ones captured this session are stored as `path` inside each raw dump.

Extra read-only composer calls already in the client, exercised once: `summary()` (GET `_action/summaryV2` → `{}`), `menu_children(237)` (GET `shellHorizontalMenuGetChildV1`), `address_bar()` (POST `addressBookBarTooltip`, empty JSON, the one POST the client already owns). Also one GET not in the client: `_action/v2/horizontalContentV1?menuId=56` → `{data:{items,hoverColor,menuId}}`.

## Envelope

Every successful page shared the same top-level keys: `layout`, `widgetStates`, `browser`, `client`, `layoutTrackingInfo`, `location`, `seo`, `shared`, `segments`, `pageInfo`, `pageToken`, `serverTiming`, `userToken`, `experimentsConfig`, `requestID`, `trackingTokenAliases`, `verticalInfo`, `resolveParams`, `isPrefetched`. `pageInfo.pageType` is the site's own type (`home`, `category`, `pdp`, `pdp_reviews`, `product_question`, `brand`, `highlight`, `seller`, `entry_point_seller`, `cart`, `account`, `communications`, `selections`, `search_suggestions`, `modal`, `static_page`, `review`). Pagination is **not** an envelope field; it is `paginator.nextPage` or `infiniteVirtualPaginator.nextPage`.

## Search is not its own page

`/search/?text=iphone+17&from_global=true` and `/search/?text=фен&from_global=true` both come back as `pageType=category` with a rewritten URL (`/category/smartfony-15502/apple-26303000/?…&text=iphone+17` and `/category/feny-10739/?…&text=фен`). The entrypoint follows category prediction. There is no distinct `pageType=search` in these responses. `categoryBrandList` appears only on the "фен" prediction.

## Page types

| page type | URL template | site pageType | raw dump | distinctive widgets | tabs / subtabs |
|---|---|---|---|---|---|
| home | /?__rr=1 | home | home.json | shell + tileGridDesktop + advBanner + seasonWidget + bigPromoCounterNavbar | paginator nextPage layout_container=homeBLR&layout_page_index=2 |
| home_p2 | /?__rr=1&layout_container=homeBLR&layout_page_index=2&start_page_id=… | home | home_p2.json | footer (deferred) | scroll paginator, not ?page= |
| search (predicted) | /search/?text=…&from_global=true → category URL | category | search.json, search_plain.json | filtersDesktop, searchResultsSort, searchResultsFiltersActive, tileGridDesktop, tagListModal, infiniteVirtualPaginator | sort=?sorting=; brand facet is a path segment /category/<cat>/<brand-id>/; filters modal /modal/allFilters/<listing path> |
| category | /category/<slug-id>/ | category | category.json | + horizontalCategoryMenu, objectLine, objectThumbnailList, resultsHeader | ?page=N works; ?sorting=score|new|price|price_desc|rating|discount; ?is_promo=t bool filter |
| category_page2 | /category/<slug>/?page=2 | category | category_page2.json | same listing widgets, fewer chrome shelves | proved distinct page |
| brand | /brand/<slug-id>/ and ?all_items=true | brand | brand.json, brand_all.json | bannerCarousel, sellerTransparency, sharingLink, filters, tiles | same listing controls as category |
| brand index | /brand/ | static_page | brands_index.json | brandListCaption, brandListFilter, brandListResults, objectThumbnailList | directory, not a brand PDP |
| highlight | /highlight/<slug-id>/ | highlight | highlight.json, highlight_apple.json | banner, filters, tiles, objectLine | /highlight/ index 404 |
| seller index | /seller/ | entry_point_seller | seller_index.json | mallFeed, favoriteSellerBrandTagList, textWidget | directory of shops |
| seller shop | /seller/<slug-or-id>/ | seller | seller_ozon.json, seller_shop.json | sellerTransparency, banner, promoCarousel (ozon), objectLine, filters, tiles | category facet /seller/?category_id=N on the index |
| product (PDP screen 1) | /product/<slug-sku>/ | pdp | product.json | webPrice, webGallery, webAspects, webShortCharacteristics, webProductHeading, webCurrentSeller, webBrand, webDetailSKU, webMarketingLabels, webAddToCart, webQuestionCount, webReviewProductScore, webListPhotos, webDelivery (empty) | ?tab=reviews|questions|description|characteristics does NOT change the widget set (client scroll hint). Description/specs are the next layout page. |
| product layout p2 | same PDP + layout_container=pdpPage2column&layout_page_index=2&start_page_id=… | pdp | product_pdp2.json | webDescription, webCharacteristics (full), webHashtags, webProducerInfo, webAttachments, webFeedbackForm, webAnchor, tileScrollDesktop | URL is paginator.nextPage on the PDP |
| product reviews shelf | layout_container=pdpReviews&layout_page_index=2 | pdp | pdp_reviews_layout.json | webReviewTabs, webAsyncContainer, webCreateQuestion, webPDPListQuestions (empty placeholder) | reviews body is async GET defaultUrl |
| reviews pdp-part | /product/<sku>/reviews/pdp-part | pdp_reviews | reviews_pdp_part.json | webReviewProductScore (histogram), webReviewsVariantMode, contextQuestionsStatistic, webListPhotos | subtabs: reviewsVariantMode=2 all, =1 this variant |
| product bottom shelves | layout_container=BottomShelfs&layout_page_index=3 | pdp | pdp_bottom.json | tileGridDesktop | recs |
| product analogs shelf | layout_container=pdp-web-second-analogs-shelf&layout_page_index=3 | pdp | pdp_analogs.json | tileScrollDesktop | similar items |
| features | /product/<slug>/features/ | pdp_reviews | features.json | webCharacteristics (totalCount 29), webProductTabs | tab Характеристики |
| reviews (canonical) | /product/<slug>/reviews/ | pdp_reviews | product_reviews.json, reviews_sort_score.json | webListReviews, webProductTabs, webReviewGallery, reviewsTitle, createReviewButton, tagListModal | ?page=N&sort=usefulness_desc|score_desc|score_asc |
| reviews (legacy path) | /reviews/<sku>/ | review | reviews_sku.json | webListReviews, reviewsTitle, webReviewGallery — no webProductTabs | works; /product/reviews/<sku>/ is 404 |
| questions | /product/<slug>/questions/ | product_question | product_questions.json | webPDPListQuestions, webCreateQuestion, webProductTabs | ?qsort=created_at_desc|usefulness_desc|has_answers_desc|has_answers_asc |
| question detail | /product/<slug>/question/<uuid> | product_question | question_detail.json | NO question/answer widget — only PDP mini chrome | body unresolved; see gaps |
| videos | /product/<slug>/videos/ | pdp_reviews | videos.json | webReviewGallery (media), webProductTabs | tab Фото и видео |
| similar modal | /modal/similar-products?product_id=<sku> | modal | similar_modal.json | webMobTabs (Аналоги / Похожие по фото), tileGridDesktop | tabs present; second tab has no separate URL in the payload |
| filters modal | /modal/allFilters/<listing path> | modal | filters_modal.json | filtersDesktop, searchResultsFiltersActive | full filter sheet |
| cart | /cart | cart | cart.json | emptyCart, master, recom paginator | read-only |
| favorites | /my/favorites/ | account | favorites.json | tabs, tileGridDesktop, statusWidget | tabs link to selections / lists / sellers |
| selections | /selections/list | selections | selections.json | tabs, statusWidget | Подборки |
| wishlists | /my/favorites/lists | account | favorites_lists.json | tabs, buttonWidget, statusWidget | Вишлисты |
| fav sellers | /my/favorites/sellers | account | favorites_sellers.json | tabs, mallFeed | Магазины и Бренды |
| account home | /my/main | account | my_main.json | login, menu, serviceMenu (anonymous) | menu links |
| orders | /my/orderlist/ | account | my_orders.json | loginButton, myGuest | anonymous gate, no order rows |
| chat | /my/chat/ | communications | my_chat.json | loginButton, myGuest | anonymous gate |
| points | /my/points/ | account | my_points.json | loginButton, myGuest | anonymous gate |
| faq | /my/questions/ | account | my_questions.json | title, customHtml FAQ, menu | not product Q&A |
| cookies | /my/cookies | account | my_cookies.json | gdprCookiesManagement, menu | account settings, anonymous |
| compare | /product/compare | static_page | compare.json | webCompare (empty state) | /compare 404s |
| buy again | /buyAgain | static_page | buy_again.json | skuGrid, skuShelfGoods | Для меня |
| business | /business | static_page | business.json | customHtml only | landing |
| pickup map | /info/map/ | static_page | info_map.json | addressEditMap, cityFilter, countryList, addressEditForm | store locator |
| search suggest | /searchSuggestions/search/?text=&from_global=true | search_suggestions | search_suggest.json | webSuggestions | composer page, not a public HTML route |
| address modal | /modal/addressbook?set_sm=1 | modal | address_modal.json | commonAddressBook | also POST addressBookBarTooltip already in client |
| currency modal | /modal/selectLanguageCurrency | modal | currency_modal.json | currencyLanguageSelector | read |
| lower price modal | /modal/web_pdp_lower_price?product_id=<sku> | modal | lower_price_modal.json | webPriceDecreasedFullView | read |
| seller rating modal | /modal/shop-in-shop-rating-popover | modal | seller_rating_modal.json | banner, textBlock, buttonWidget | read |


### Product tabs (resolved)

`webProductTabs` on the features/reviews/questions/videos pages (not on PDP screen 1) is four real paths:

| tab | counter (this SKU) | URL |
|---|---|---|
| Характеристики | — | `/product/<slug>/features` |
| Отзывы | 47 | `/product/<slug>/reviews` |
| Вопросы | 35 | `/product/<slug>/questions` |
| Фото и видео | 14 | `/product/<slug>/videos` |

`?tab=reviews|questions|description|characteristics` on the PDP itself was fetched. `pageInfo.url` keeps the param, but the widget set is identical to screen 1 (49 families). Those params are scroll hints, not data endpoints.

Description text is **not** a path. It is `webDescription.richAnnotation` (HTML, `richAnnotationType=HTML`) on the next layout slice:

`/product/<slug>/?__rr=1&layout_container=pdpPage2column&layout_page_index=2&sh=…&start_page_id=…`

That same slice carries the full `webCharacteristics` (29 rows, `totalCount`), hashtags, producer info, attachments, feedback form, and a `tileScrollDesktop` shelf. `webShortCharacteristics` on screen 1 is only the first 5 rows plus anchors `section-description` / `section-characteristics`.

### Reviews subtabs (resolved)

- List page: `/product/<slug>/reviews/?page=N&sort=<value>`. Sort values from `webListReviews.sortings`: `usefulness_desc` (новые и полезные, default), `score_desc`, `score_asc`. `paging.perPage=30`, `paging.total=47`. `page=2` returns data without requiring `page_key` (the next button also sends `page_key`).
- Legacy `/reviews/<sku>/` still returns `webListReviews` (`pageType=review`) but without `webProductTabs`. `/product/reviews/<sku>/` is **404** (`audit/raw/reviews_legacy.error.json`).
- Embedded in the PDP: `layout_container=pdpReviews` exposes `webAsyncContainer.defaultUrl=/product/<sku>/reviews/pdp-part`. That fragment has `webReviewsVariantMode` subtabs, proved:
  - all variants: `…/reviews/pdp-part?oos_search=false&reviewsVariantMode=2` (default)
  - this variant: `…/reviews/pdp-part?oos_search=false&reviewsVariantMode=1` (`selectedTabIndex=1`, title "Этот вариант товара (6)")
- Histogram lives on the fragment's `webReviewProductScore.score[]` (`{title,value}` per star), not on the flat `totalScore`.
- Buyer context stats: `contextQuestionsStatistic.questions[]`.

### Questions subtabs (resolved as a page, not as an in-PDP swap)

`/product/<slug>/questions/?qsort=` with `webPDPListQuestions.sorting.options`:

| title | qsort |
|---|---|
| Сначала новые | `created_at_desc` |
| Сначала полезные | `usefulness_desc` |
| Сначала с ответом | `has_answers_desc` |
| Сначала без ответа | `has_answers_asc` |

`created_at_desc` was fetched and returned 10 questions with answers. Further pages use `paginator.nextPage` (`page_key`, `layout_page_index`), not a bare `?page=`.

### Listing sort and filters (resolved)

`searchResultsSort` options, proved on `/category/elektronika-15500/`:

| name | query |
|---|---|
| Популярные | `sorting=score` (default) |
| Новинки | `sorting=new` |
| Дешевле | `sorting=price` |
| Дороже | `sorting=price_desc` |
| С высоким рейтингом | `sorting=rating` |
| С большими скидками | `sorting=discount` |

Same six links exist on highlight, brand, and seller listings. `sorting=price` was fetched (`category_sorted.json`).

`filtersDesktop.sections[].filters[]` keys on electronics: `category` (categoryFilter), `is_promo` (bool), `delivery` (checkboxes), `currency_price` (range), `brand` (checkboxes), `brandcertified`, `is_official_brand_seller`, `type`, `exactmodels`, `country`, `color` (colorFilter), `isdiscount`, `seller`. Bool form proved: `?is_promo=t` comes back with `searchResultsFiltersActive.activeFilters[].key=is_promo`. Brand facet is a **path**, not a query: `/category/<cat>/<brand-id>/` (the predicted search URL). Full sheet: `/modal/allFilters/<listing path>`.

`horizontalCategoryMenu` on the category page is the subcategory strip (Бытовая техника, Телефоны и смарт-часы, …) — separate category URLs, not query params.

### Favourites tabs (resolved)

`tabs` widget, four redirects:

| title | URL |
|---|---|
| Избранное | `/my/favorites` (current) |
| Подборки | `/selections/list` |
| Вишлисты | `/my/favorites/lists` |
| Магазины и Бренды | `/my/favorites/sellers` |

### Account menu (resolved)

From `menu` on `/my/main` (anonymous):

- Пункты выдачи → `/info/map`
- Сравнение товаров → `/product/compare` (`/compare` 404s; page is `webCompare`)
- Ozon для бизнеса → `/business`
- Для меня → `/buyAgain` (`skuGrid`, `skuShelfGoods`)
- Настройки cookies → `/my/cookies` (`gdprCookiesManagement`)
- Help links leave the site for `docs.ozon.ru` (not entrypoint pages).

`/my/orderlist/`, `/my/chat/`, `/my/points/` return only `loginButton` + `myGuest`. No order/chat/points records without a session.

### Shell widgets shared by almost every page

`header`, `headerIcon`, `searchBarDesktop`, `catalogMenu`, `horizontalMenu`, `footer`, `addressBookBarWeb`, `selectedCurrencyLanguage`, `profileMenuAnonymous`, `favoriteCounter`, `orderInfo`, `orderTracking`, `tapTags`, `separator`, `container`, `column`, `row`, `wallpaper`. Home screen 1 omits `footer`; it arrives on `layout_container=homeBLR&layout_page_index=2`.

## Widget family → dumps

Family = widget key with `-<id>-<container>-<n>` stripped. Dump stems are `audit/raw/<stem>.json`. `product_tab_*` dumps are the no-op `?tab=` fetches (same families as `product`).

| family | dumps | page dumps |
|---|---|---|
| `addressBookBarWeb` | 41 | brand, brand_all, brands_index, buy_again, cart, category, category_page2, category_promo, category_sorted, compare, favorites, favorites_lists, favorites_sellers, features, highlight, highlight_apple, home, info_map, my_chat, my_cookies, my_main, my_orders, my_points, my_questions, product, product_questions, product_reviews, product_tab_characteristics, product_tab_description, product_tab_questions, product_tab_reviews, question_detail, reviews_sku, reviews_sort_score, search, search_plain, selections, seller_index, seller_ozon, seller_shop, videos |
| `addressEditForm` | 1 | info_map |
| `addressEditLayout` | 1 | info_map |
| `addressEditLayoutContainer` | 1 | info_map |
| `addressEditLayoutLeft` | 1 | info_map |
| `addressEditLayoutWrapper` | 1 | info_map |
| `addressEditMap` | 1 | info_map |
| `advBanner` | 1 | home |
| `banner` | 4 | highlight, seller_ozon, seller_rating_modal, seller_shop |
| `bannerCarousel` | 3 | brand, brand_all, seller_ozon |
| `bigPromoCounterNavbar` | 1 | home |
| `bigPromoPDP` | 5 | product, product_tab_characteristics, product_tab_description, product_tab_questions, product_tab_reviews |
| `brandListCaption` | 1 | brands_index |
| `brandListFilter` | 1 | brands_index |
| `brandListResults` | 2 | brands_index, info_map |
| `breadCrumbs` | 12 | features, product, product_questions, product_reviews, product_tab_characteristics, product_tab_description, product_tab_questions, product_tab_reviews, question_detail, reviews_sku, reviews_sort_score, videos |
| `buttonWidget` | 2 | favorites_lists, seller_rating_modal |
| `caption` | 1 | my_main |
| `catalogMenu` | 41 | brand, brand_all, brands_index, buy_again, cart, category, category_page2, category_promo, category_sorted, compare, favorites, favorites_lists, favorites_sellers, features, highlight, highlight_apple, home, info_map, my_chat, my_cookies, my_main, my_orders, my_points, my_questions, product, product_questions, product_reviews, product_tab_characteristics, product_tab_description, product_tab_questions, product_tab_reviews, question_detail, reviews_sku, reviews_sort_score, search, search_plain, selections, seller_index, seller_ozon, seller_shop, videos |
| `categoryBrandList` | 1 | search_plain |
| `cityFilter` | 1 | info_map |
| `column` | 38 | brand, brand_all, cart, category, category_page2, category_promo, category_sorted, compare, favorites, features, highlight, highlight_apple, lower_price_modal, my_cookies, my_main, my_questions, pdp_bottom, pdp_reviews_layout, product, product_pdp2, product_questions, product_reviews, product_tab_characteristics, product_tab_description, product_tab_questions, product_tab_reviews, question_detail, reviews_pdp_part, reviews_sku, reviews_sort_score, reviews_variant_this, search, search_plain, search_suggest, seller_ozon, seller_rating_modal, seller_shop, videos |
| `commonAddressBook` | 1 | address_modal |
| `container` | 42 | brand, brand_all, brands_index, buy_again, cart, category, category_page2, category_promo, category_sorted, compare, favorites, favorites_lists, favorites_sellers, features, highlight, highlight_apple, home, info_map, my_chat, my_cookies, my_main, my_orders, my_points, my_questions, product, product_pdp2, product_questions, product_reviews, product_tab_characteristics, product_tab_description, product_tab_questions, product_tab_reviews, question_detail, reviews_sku, reviews_sort_score, search, search_plain, selections, seller_index, seller_ozon, seller_shop, videos |
| `contextQuestionsStatistic` | 2 | reviews_pdp_part, reviews_variant_this |
| `countryList` | 1 | info_map |
| `createReviewButton` | 4 | product_reviews, reviews_pdp_part, reviews_sort_score, reviews_variant_this |
| `currencyLanguageSelector` | 1 | currency_modal |
| `customHtml` | 7 | business, my_questions, product, product_tab_characteristics, product_tab_description, product_tab_questions, product_tab_reviews |
| `emptyCart` | 1 | cart |
| `favoriteCounter` | 41 | brand, brand_all, brands_index, buy_again, cart, category, category_page2, category_promo, category_sorted, compare, favorites, favorites_lists, favorites_sellers, features, highlight, highlight_apple, home, info_map, my_chat, my_cookies, my_main, my_orders, my_points, my_questions, product, product_questions, product_reviews, product_tab_characteristics, product_tab_description, product_tab_questions, product_tab_reviews, question_detail, reviews_sku, reviews_sort_score, search, search_plain, selections, seller_index, seller_ozon, seller_shop, videos |
| `favoriteSellerBrandTagList` | 1 | seller_index |
| `filtersDesktop` | 13 | brand, brand_all, category, category_page2, category_promo, category_sorted, filters_modal, highlight, highlight_apple, search, search_plain, seller_ozon, seller_shop |
| `footer` | 40 | brand, brand_all, brands_index, buy_again, cart, category, category_page2, category_promo, category_sorted, compare, favorites, favorites_lists, favorites_sellers, features, highlight, highlight_apple, home_p2, info_map, my_chat, my_cookies, my_main, my_orders, my_points, product, product_questions, product_reviews, product_tab_characteristics, product_tab_description, product_tab_questions, product_tab_reviews, question_detail, reviews_sku, reviews_sort_score, search, search_plain, selections, seller_index, seller_ozon, seller_shop, videos |
| `freshIsland` | 2 | my_cookies, my_main |
| `gdprCookiesManagement` | 1 | my_cookies |
| `header` | 41 | brand, brand_all, brands_index, buy_again, cart, category, category_page2, category_promo, category_sorted, compare, favorites, favorites_lists, favorites_sellers, features, highlight, highlight_apple, home, info_map, my_chat, my_cookies, my_main, my_orders, my_points, my_questions, product, product_questions, product_reviews, product_tab_characteristics, product_tab_description, product_tab_questions, product_tab_reviews, question_detail, reviews_sku, reviews_sort_score, search, search_plain, selections, seller_index, seller_ozon, seller_shop, videos |
| `headerIcon` | 41 | brand, brand_all, brands_index, buy_again, cart, category, category_page2, category_promo, category_sorted, compare, favorites, favorites_lists, favorites_sellers, features, highlight, highlight_apple, home, info_map, my_chat, my_cookies, my_main, my_orders, my_points, my_questions, product, product_questions, product_reviews, product_tab_characteristics, product_tab_description, product_tab_questions, product_tab_reviews, question_detail, reviews_sku, reviews_sort_score, search, search_plain, selections, seller_index, seller_ozon, seller_shop, videos |
| `homeButton` | 12 | brand, brand_all, category, category_page2, category_promo, category_sorted, highlight, highlight_apple, search, search_plain, seller_ozon, seller_shop |
| `horizontalCategoryMenu` | 1 | category |
| `horizontalMenu` | 41 | brand, brand_all, brands_index, buy_again, cart, category, category_page2, category_promo, category_sorted, compare, favorites, favorites_lists, favorites_sellers, features, highlight, highlight_apple, home, info_map, my_chat, my_cookies, my_main, my_orders, my_points, my_questions, product, product_questions, product_reviews, product_tab_characteristics, product_tab_description, product_tab_questions, product_tab_reviews, question_detail, reviews_sku, reviews_sort_score, search, search_plain, selections, seller_index, seller_ozon, seller_shop, videos |
| `infiniteVirtualPaginator` | 12 | brand, brand_all, category, category_page2, category_promo, category_sorted, highlight, highlight_apple, search, search_plain, seller_ozon, seller_shop |
| `island` | 12 | brand, brand_all, category, favorites, favorites_lists, favorites_sellers, my_cookies, my_main, my_questions, selections, seller_ozon, seller_shop |
| `login` | 1 | my_main |
| `loginButton` | 4 | my_chat, my_main, my_orders, my_points |
| `mallFeed` | 2 | favorites_sellers, seller_index |
| `master` | 2 | cart, info_map |
| `menu` | 3 | my_cookies, my_main, my_questions |
| `myGuest` | 3 | my_chat, my_orders, my_points |
| `objectBannerList` | 1 | seller_shop |
| `objectLine` | 3 | category, highlight, seller_shop |
| `objectThumbnailList` | 2 | brands_index, category |
| `orderInfo` | 41 | brand, brand_all, brands_index, buy_again, cart, category, category_page2, category_promo, category_sorted, compare, favorites, favorites_lists, favorites_sellers, features, highlight, highlight_apple, home, info_map, my_chat, my_cookies, my_main, my_orders, my_points, my_questions, product, product_questions, product_reviews, product_tab_characteristics, product_tab_description, product_tab_questions, product_tab_reviews, question_detail, reviews_sku, reviews_sort_score, search, search_plain, selections, seller_index, seller_ozon, seller_shop, videos |
| `orderTracking` | 41 | brand, brand_all, brands_index, buy_again, cart, category, category_page2, category_promo, category_sorted, compare, favorites, favorites_lists, favorites_sellers, features, highlight, highlight_apple, home, info_map, my_chat, my_cookies, my_main, my_orders, my_points, my_questions, product, product_questions, product_reviews, product_tab_characteristics, product_tab_description, product_tab_questions, product_tab_reviews, question_detail, reviews_sku, reviews_sort_score, search, search_plain, selections, seller_index, seller_ozon, seller_shop, videos |
| `pageHeader` | 1 | info_map |
| `pageHeaderLight` | 1 | info_map |
| `paginator` | 17 | cart, favorites, favorites_sellers, home, home_p2, pdp_reviews_layout, product, product_pdp2, product_questions, product_tab_characteristics, product_tab_description, product_tab_questions, product_tab_reviews, reviews_pdp_part, reviews_variant_this, seller_index, similar_modal |
| `pixel` | 6 | cart, product, product_tab_characteristics, product_tab_description, product_tab_questions, product_tab_reviews |
| `profileMenuAnonymous` | 41 | brand, brand_all, brands_index, buy_again, cart, category, category_page2, category_promo, category_sorted, compare, favorites, favorites_lists, favorites_sellers, features, highlight, highlight_apple, home, info_map, my_chat, my_cookies, my_main, my_orders, my_points, my_questions, product, product_questions, product_reviews, product_tab_characteristics, product_tab_description, product_tab_questions, product_tab_reviews, question_detail, reviews_sku, reviews_sort_score, search, search_plain, selections, seller_index, seller_ozon, seller_shop, videos |
| `promoCarousel` | 1 | seller_ozon |
| `resultsHeader` | 5 | category, category_page2, category_promo, category_sorted, highlight_apple |
| `reviewsTitle` | 3 | product_reviews, reviews_sku, reviews_sort_score |
| `row` | 38 | brand, brand_all, cart, category, category_page2, category_promo, category_sorted, compare, favorites, features, highlight, highlight_apple, lower_price_modal, my_cookies, my_main, my_questions, pdp_bottom, pdp_reviews_layout, product, product_pdp2, product_questions, product_reviews, product_tab_characteristics, product_tab_description, product_tab_questions, product_tab_reviews, question_detail, reviews_pdp_part, reviews_sku, reviews_sort_score, reviews_variant_this, search, search_plain, search_suggest, seller_ozon, seller_rating_modal, seller_shop, videos |
| `searchBarDesktop` | 41 | brand, brand_all, brands_index, buy_again, cart, category, category_page2, category_promo, category_sorted, compare, favorites, favorites_lists, favorites_sellers, features, highlight, highlight_apple, home, info_map, my_chat, my_cookies, my_main, my_orders, my_points, my_questions, product, product_questions, product_reviews, product_tab_characteristics, product_tab_description, product_tab_questions, product_tab_reviews, question_detail, reviews_sku, reviews_sort_score, search, search_plain, selections, seller_index, seller_ozon, seller_shop, videos |
| `searchResultsFiltersActive` | 13 | brand, brand_all, category, category_page2, category_promo, category_sorted, filters_modal, highlight, highlight_apple, search, search_plain, seller_ozon, seller_shop |
| `searchResultsSort` | 12 | brand, brand_all, category, category_page2, category_promo, category_sorted, highlight, highlight_apple, search, search_plain, seller_ozon, seller_shop |
| `seasonWidget` | 1 | home |
| `selectedCurrencyLanguage` | 41 | brand, brand_all, brands_index, buy_again, cart, category, category_page2, category_promo, category_sorted, compare, favorites, favorites_lists, favorites_sellers, features, highlight, highlight_apple, home, info_map, my_chat, my_cookies, my_main, my_orders, my_points, my_questions, product, product_questions, product_reviews, product_tab_characteristics, product_tab_description, product_tab_questions, product_tab_reviews, question_detail, reviews_sku, reviews_sort_score, search, search_plain, selections, seller_index, seller_ozon, seller_shop, videos |
| `sellerTransparency` | 4 | brand, brand_all, seller_ozon, seller_shop |
| `seoPageBanner` | 1 | info_map |
| `separator` | 42 | brand, brand_all, brands_index, cart, category, category_page2, category_promo, category_sorted, favorites, favorites_lists, favorites_sellers, features, highlight, highlight_apple, home, info_map, lower_price_modal, my_main, pdp_analogs, pdp_reviews_layout, product, product_pdp2, product_questions, product_reviews, product_tab_characteristics, product_tab_description, product_tab_questions, product_tab_reviews, question_detail, reviews_pdp_part, reviews_sku, reviews_sort_score, reviews_variant_this, search, search_plain, selections, seller_index, seller_ozon, seller_rating_modal, seller_shop, similar_modal, videos |
| `serviceMenu` | 1 | my_main |
| `sharingLink` | 4 | brand, brand_all, seller_ozon, seller_shop |
| `skuGrid` | 1 | buy_again |
| `skuShelfGoods` | 1 | buy_again |
| `statusWidget` | 4 | favorites, favorites_lists, favorites_sellers, selections |
| `stickyContainer` | 2 | cart, product_pdp2 |
| `tabs` | 4 | favorites, favorites_lists, favorites_sellers, selections |
| `tagListModal` | 7 | features, product_questions, product_reviews, reviews_sort_score, search, search_plain, videos |
| `tapTags` | 41 | brand, brand_all, brands_index, buy_again, cart, category, category_page2, category_promo, category_sorted, compare, favorites, favorites_lists, favorites_sellers, features, highlight, highlight_apple, home, info_map, my_chat, my_cookies, my_main, my_orders, my_points, my_questions, product, product_questions, product_reviews, product_tab_characteristics, product_tab_description, product_tab_questions, product_tab_reviews, question_detail, reviews_sku, reviews_sort_score, search, search_plain, selections, seller_index, seller_ozon, seller_shop, videos |
| `textBlock` | 8 | lower_price_modal, pdp_reviews_layout, product, product_tab_characteristics, product_tab_description, product_tab_questions, product_tab_reviews, seller_rating_modal |
| `textWidget` | 2 | favorites_sellers, seller_index |
| `tileGridDesktop` | 16 | brand, brand_all, category, category_page2, category_promo, category_sorted, favorites, highlight, highlight_apple, home, pdp_bottom, search, search_plain, seller_ozon, seller_shop, similar_modal |
| `tileScrollDesktop` | 2 | pdp_analogs, product_pdp2 |
| `title` | 1 | my_questions |
| `wallpaper` | 30 | brand, brand_all, cart, category, category_page2, category_promo, category_sorted, favorites, favorites_lists, favorites_sellers, features, home, my_chat, my_cookies, my_main, my_orders, my_points, my_questions, product_questions, product_reviews, question_detail, reviews_sku, reviews_sort_score, search, search_plain, selections, seller_index, seller_ozon, seller_shop, videos |
| `webAddToCart` | 12 | features, product, product_questions, product_reviews, product_tab_characteristics, product_tab_description, product_tab_questions, product_tab_reviews, question_detail, reviews_sku, reviews_sort_score, videos |
| `webAddToCompare` | 6 | product, product_pdp2, product_tab_characteristics, product_tab_description, product_tab_questions, product_tab_reviews |
| `webAddToFavorite` | 5 | product, product_tab_characteristics, product_tab_description, product_tab_questions, product_tab_reviews |
| `webAnchor` | 1 | product_pdp2 |
| `webAspects` | 5 | product, product_tab_characteristics, product_tab_description, product_tab_questions, product_tab_reviews |
| `webAsyncContainer` | 1 | pdp_reviews_layout |
| `webAttachments` | 1 | product_pdp2 |
| `webBrand` | 5 | product, product_tab_characteristics, product_tab_description, product_tab_questions, product_tab_reviews |
| `webCharacteristics` | 8 | features, product_pdp2, product_questions, product_reviews, question_detail, reviews_sku, reviews_sort_score, videos |
| `webCompare` | 1 | compare |
| `webCreateQuestion` | 2 | pdp_reviews_layout, product_questions |
| `webCurrentSeller` | 5 | product, product_tab_characteristics, product_tab_description, product_tab_questions, product_tab_reviews |
| `webDelivery` | 5 | product, product_tab_characteristics, product_tab_description, product_tab_questions, product_tab_reviews |
| `webDescription` | 1 | product_pdp2 |
| `webDetailSKU` | 5 | product, product_tab_characteristics, product_tab_description, product_tab_questions, product_tab_reviews |
| `webFeedbackForm` | 1 | product_pdp2 |
| `webGallery` | 5 | product, product_tab_characteristics, product_tab_description, product_tab_questions, product_tab_reviews |
| `webHashtags` | 1 | product_pdp2 |
| `webInstallmentPurchase` | 5 | product, product_tab_characteristics, product_tab_description, product_tab_questions, product_tab_reviews |
| `webListPhotos` | 9 | product, product_reviews, product_tab_characteristics, product_tab_description, product_tab_questions, product_tab_reviews, reviews_pdp_part, reviews_sort_score, reviews_variant_this |
| `webListReviews` | 3 | product_reviews, reviews_sku, reviews_sort_score |
| `webMarketingLabels` | 5 | product, product_tab_characteristics, product_tab_description, product_tab_questions, product_tab_reviews |
| `webMobTab` | 1 | similar_modal |
| `webMobTabs` | 1 | similar_modal |
| `webOneClickButton` | 5 | product, product_tab_characteristics, product_tab_description, product_tab_questions, product_tab_reviews |
| `webPDPListQuestions` | 2 | pdp_reviews_layout, product_questions |
| `webPdpGrid` | 14 | features, product, product_pdp2, product_questions, product_reviews, product_tab_characteristics, product_tab_description, product_tab_questions, product_tab_reviews, question_detail, reviews_sku, reviews_sort_score, similar_modal, videos |
| `webPrice` | 12 | features, product, product_questions, product_reviews, product_tab_characteristics, product_tab_description, product_tab_questions, product_tab_reviews, question_detail, reviews_sku, reviews_sort_score, videos |
| `webPriceDecreasedCompact` | 5 | product, product_tab_characteristics, product_tab_description, product_tab_questions, product_tab_reviews |
| `webPriceDecreasedFullView` | 1 | lower_price_modal |
| `webProducerInfo` | 1 | product_pdp2 |
| `webProductHeading` | 5 | product, product_tab_characteristics, product_tab_description, product_tab_questions, product_tab_reviews |
| `webProductMainWidget` | 5 | product, product_tab_characteristics, product_tab_description, product_tab_questions, product_tab_reviews |
| `webProductMini` | 7 | features, product_questions, product_reviews, question_detail, reviews_sku, reviews_sort_score, videos |
| `webProductTabs` | 5 | features, product_questions, product_reviews, reviews_sort_score, videos |
| `webQuestionCount` | 5 | product, product_tab_characteristics, product_tab_description, product_tab_questions, product_tab_reviews |
| `webReviewGallery` | 5 | product_pdp2, product_reviews, reviews_sku, reviews_sort_score, videos |
| `webReviewProductScore` | 9 | product, product_reviews, product_tab_characteristics, product_tab_description, product_tab_questions, product_tab_reviews, reviews_pdp_part, reviews_sort_score, reviews_variant_this |
| `webReviewTabs` | 1 | pdp_reviews_layout |
| `webReviewsVariantMode` | 2 | reviews_pdp_part, reviews_variant_this |
| `webSale` | 5 | product, product_tab_characteristics, product_tab_description, product_tab_questions, product_tab_reviews |
| `webSharingButton` | 5 | product, product_tab_characteristics, product_tab_description, product_tab_questions, product_tab_reviews |
| `webShortCharacteristics` | 5 | product, product_tab_characteristics, product_tab_description, product_tab_questions, product_tab_reviews |
| `webSingleProductScore` | 5 | product, product_tab_characteristics, product_tab_description, product_tab_questions, product_tab_reviews |
| `webStickyColumn` | 5 | product, product_tab_characteristics, product_tab_description, product_tab_questions, product_tab_reviews |
| `webStickyProducts` | 5 | product, product_tab_characteristics, product_tab_description, product_tab_questions, product_tab_reviews |
| `webSuggestions` | 1 | search_suggest |


## Unresolved (with reason)

| thing | why it is unresolved |
|---|---|
| Question thread at `/product/<slug>/question/<uuid>` | GET returns `pageType=product_question` but the only product widgets are mini-card chrome (`webProductMini`, `webPrice`, `webCharacteristics`). No question/answer widget. Filling it likely needs POST `/api/composer-api.bx/widget/json/v2` (seen in recon for `orderInfo`). Not called: it is not a composer action this client already uses, and it was not proven read-only. |
| In-PDP "Вопросы о товаре" subtab | `webReviewTabs` value is the string `questions`, not a URL. Re-fetching `layout_container=pdpReviews&tab=questions` returns the same 15 widgets and `webPDPListQuestions` stays `{}`. `/product/<sku>/questions/pdp-part` redirects to the full PDP (80 widgets), not a question list. The list itself **is** resolved at `/product/<slug>/questions/`. |
| PDP `webDelivery` | State is `{}` on screen 1. Delivery terms are not in the initial envelope. Same likely async widget POST; not called. |
| Similar-modal tab "Похожие по фото" | `webMobTabs.tabs` has two titles and no per-tab link. Both `webMobTab` states are `{}`. "Аналоги" content is the `tileGridDesktop` already in the modal payload. |
| `/premium/` | In-page `fetch` failed (`TypeError: Failed to fetch`) after a fresh `warmup`. No dump. See `audit/raw/premium.error.json`. |
| `getSearchTapTags` | Recon shows POST `/api/composer-api.bx/_action/v2/getSearchTapTags`. Not in our client. Not called. |
| `registerSearchEvent`, `setUserCookies` | POSTs from recon. Look like analytics / cookie writes. Not called. |
| Logged-in orders, chat, points, favourites contents | Anonymous session: login wall or empty counters. Widgets for a signed-in user were not observed. |
| Every checkbox filter value | Keys are listed above. Only `is_promo=t`, the six `sorting` values, brand-as-path, and `?page=` were fetched end-to-end. Other keys (`currency_price`, `color`, …) are present in `filtersDesktop` but each value URL was not individually fetched. |
| `/highlight/`, `/promo/`, `/special/`, `/info/dostavka/` | 404 on the entrypoint. Promo content is `/highlight/<slug-id>/`. Delivery help is `docs.ozon.ru`, not ozon.by. |


## Correction: `tab` and `layout_page_index` (re-tested)

Fresh PDP fetch of `/product/apple-smartfon-iphone-17-pro-esim-12-512-gb-esim-siniy-3094054833/?__rr=1` on the same session. Family = widget key with `-<id>-<container>-<n>` stripped. Symmetric difference is versus that screen-1 set. Full numbers are in `audit/tab_diff.json`.

| request | widgets | families | families only in screen 1 | families only in this response | webDescription | webCharacteristics |
|---|---|---|---|---|---|---|
| screen 1 | 80 | 49 | — | — | no | no |
| `?tab=reviews` | 80 | 49 | ∅ | ∅ | no | no |
| `?tab=questions` | 80 | 49 | ∅ | ∅ | no | no |
| `?tab=description` | 80 | 49 | ∅ | ∅ | no | no |
| `?tab=characteristics` | 80 | 49 | ∅ | ∅ | no | no |
| `?layout_page_index=2` alone | 80 | 49 | ∅ | ∅ | no | no |
| `layout_container=pdpPage2column&layout_page_index=2` (no `start_page_id`) | 33 | 17 | 42 shell/buy-box families | `webDescription`, `webCharacteristics`, `webAnchor`, `webAttachments`, `webFeedbackForm`, `webHashtags`, `webProducerInfo`, `webReviewGallery`, `tileScrollDesktop`, `stickyContainer` | yes | yes |
| `paginator.nextPage` from that same screen 1 (adds `start_page_id`) | 33 | 17 | same 42 | same 10 | yes | yes |

`?tab=` is echoed into `webProductMainWidget.url` and the anonymous-login return URL. Tracking keys and `paginator.nextPage`'s `start_page_id` change on every response. No other widget field changed. So the JS reading `tab` / `searchParams.get("layout_page_index")` is client routing. The server does not select description or characteristics from either param alone.

`layout_page_index` is not globally ignored. It does nothing without `layout_container`. The pair `layout_container=pdpPage2column&layout_page_index=2` is sufficient; `start_page_id` is optional. That pair is what screen-1 `paginator.nextPage` already contains (`layoutContainer` was `pdpPage2column`).
