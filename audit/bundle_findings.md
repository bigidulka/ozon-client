# Bundle findings

What the static bundles on the seven catalogue page types contain,
compared with what `ozon_client` already calls.

## Coverage

- Downloaded bundles: 315 (all HTTP 200, all under 15 MB).
- API paths reconstructed: 105.
- `_action` names: 93.
- Widget registry keys (`name:{content:`): 1223.
- Header names (`x-o3-*`, `x-page-*`, `x-client-*`, `x-requested-*`): 21.
- Query-parameter names: 29.
- Sort / filter / tab identifiers: 29.
- GraphQL operation names: **none**. No `graphql`, `__typename`, or `operationName` string in any loaded bundle.
- `x-client-*`: **none**.
- `x-requested-*`: **none**.

Paths are reconstructed the way `AbstractApiService.callApi` builds them
(`main.js`: `getBrowserApiUrl` defaults the gateway to `api`, so the
prefix is `/api/` + `servicePath` + optional `/v{serviceVersion}` + `path`).
Each row in `bundle_strings.json` cites the local file under `audit/bundles/`.

## What the client already uses

| Call | In these bundles? |
|---|---|
| `GET /api/entrypoint-api.bx/page/json/v2?url=` | Yes. `ComposerService.jsonGet`, default version 2 switches service path to `entrypoint-api.bx`. Source: `main.js`. |
| `GET /api/composer-api.bx/_action/summaryV2` | Yes. `host.js`, `bx-fe__common-feature-cart__1.7.8__index.js`. |
| `GET /api/composer-api.bx/_action/v2/shellHorizontalMenuGetChildV1` | Yes. `cms-desktop-horizontal-menu.js` (`cmsShellHorizontalMenuGetChildV1`, query key `menuId`). |
| `POST /api/composer-api.bx/_action/v2/addressBookBarTooltip` | **Not a string in the loaded bundles.** The action name was not found. The address-bar widget that did load is `addressBookMap-all-addressbook-bar.js` / registry key `addressBookBarWeb` (`cart-checkout-geo.js`). |
| Page composer targets `/`, `/search/`, `/category/...`, `/product/...`, `/reviews/<sku>/`, `/cart`, `/my/favorites/`, `/searchSuggestions/search/` | These are page URLs passed as the `url` query of `page/json/v2`, not separate endpoints. `/search/` itself is not hard-coded; search UI lives in `search-desktop-search-bar-desktop.js`. |
| Headers `x-o3-app-name`, `x-o3-app-version`, `x-o3-manifest-version`, `x-o3-parent-requestid`, `x-page-view-id`, `x-page-previous` | Yes, as one enum in `main.js`. |

`layout_page_index` is **not** ignored by the frontend: `main.js` reads it
(`searchParams.get("layout_page_index")`) and `composer-all-paginator.js` /
`catalog-all-infinite-virtual-paginator.js` send `layout_container`.
`start_page_id` is a string in `composer-all-paginator.js`. The client’s note
that `layout_page_index` is ignored matches server behaviour observed live,
not the bundle (the bundle still supplies it).

Strings the client sends that **do not appear** in these bundles:
`from_global`, `__rr`, `prv`, `set_sm`. They are page-level query keys,
not literals in the JS that was loaded.

## Headers present in bundles

- `x-o3-all-notification-off` — `notification-service.js`
- `x-o3-app-name` — `main.js`
- `x-o3-app-version` — `main.js`
- `x-o3-auto-modal-off` — `main.js`
- `x-o3-autostart-video-off` — `pdp-desktop-gallery-v6.js`
- `x-o3-debug-toolbar` — `host.js`, `main.js`
- `x-o3-disable-placements` — `main.js`
- `x-o3-manifest-version` — `main.js`
- `x-o3-meshversion` — `main.js`
- `x-o3-otm-version` — `main.js`
- `x-o3-parent-requestid` — `main.js`
- `x-o3-prefetch` — `main.js`
- `x-o3-sitespeed-enable` — `main.js`
- `x-o3-timezone` — `main.js`
- `x-o3-trace-id` — `main.js`
- `x-o3-tracker-manager` — `main.js`
- `x-o3-tracker-metrics` — `main.js`
- `x-o3-ui-tests` — `main.js`, `pdp-all-description-v3.js`, `vendor-vue.js`
- `x-o3-vue-devtools` — `main.js`
- `x-page-previous` — `main.js`
- `x-page-view-id` — `main.js`

## Query parameters present in bundles

- `ai_mode` — `search-desktop-search-bar-desktop.js`
- `code` — `autosplit-teams_udm_components_enter-otp_v2_index_vue-teams_udm_components_submit-button_index_vue.js`
- `filter` — `1.0.4.js`, `catalog-all-search-results-filters-active.js`, `popper.js`, `vendor-vue.js`
- `filters` — `common-desktop-filters.js`, `search-desktop-search-bar-desktop.js`, `vendor-vue.js`
- `fragmented` — `main.js`
- `from` — `autosplit-teams_common_components_filters-color-icon_index_vue-teams_common_components_filter-7c3b30.js`, `bx-fe__ui-kit-range__5.4.6__index.js`, `main.js`, `pdp-desktop-gallery-v6.js`
- `helpCenter` — `main.js`
- `id` — `pdp-all-sharing-button-v3.js`, `pdp-mobile-add-to-cart-v10.js`, `sdk.js`
- `layout_container` — `catalog-all-infinite-virtual-paginator.js`, `composer-all-paginator.js`
- `layout_page_index` — `main.js`
- `list` — `bx-fe__common-feature-favorites__1.4.10__index.js`, `bx-fe__common-feature-favorites__1.4.12__index.js`, `bx-fe__ui-kit-ds-dropdown-content__5.5.6__index.js`, `bx-fe__ui-kit-ds-select__5.6.7__index.js`
- `menuId` — `catalog-menu-all-horizontal-category-menu-v1.js`, `cms-desktop-catalog-menu.js`
- `miniapp` — `bx-fe__common-feature-cart__1.7.8__index.js`, `host.js`
- `mwId` — `main.js`
- `page` — `cpm-ozon@5.9.6.js`, `host.js`, `main.js`, `pdp-desktop-gallery-v6.js`
- `page_changed` — `vendor-core.js`
- `product_id` — `pdp-all-sharing-button-v3.js`, `pdp-mobile-add-to-cart-v10.js`, `pdp-mobile-product-main.js`
- `redirect_query` — `search-desktop-search-bar-desktop.js`
- `refresh` — `cart-all-master.js`
- `returnUrl` — `udm-desktop-profile-menu-anonymous.js`
- `rgPage` — `rp-product-all-list-photos-v2.js`, `rp-product-desktop-web-review-gallery-v2.js`, `rp-product-web-list-reviews-v3.js`
- `sku` — `navi-commons.js`
- `sort` — `vendor-vue.js`
- `start_page_id` — `composer-all-paginator.js`
- `sw-prefetch` — `main.js`
- `tab` — `bx-fe__ui-kit-button__5.4.3__index.js`, `bx-fe__ui-kit-button__5.4.5__index.js`, `bx-fe__ui-kit-ds-select__5.6.7__index.js`, `cart-all-master.js`
- `text` — `addressBookMap-all-addressbook-bar.js`, `autosplit-teams_udm_components_form-field_index_vue.js`, `autosplit-teams_udm_components_form-field_phone_vue.js`, `bx-fe__common-atom-ds-button__3.14.2__index.js`
- `url` — `1.0.4.js`, `bx-fe__common-component-adv-badge__3.8.2__index.js`, `bx-fe__common-component-adv-badge__3.9.0__index.js`, `bx-fe__common-component-adv-info__3.7.3__index.js`
- `widgetStateId` — `main.js`

Single-letter `?e=` / `?n=` matches from minified code were dropped as false positives.

## Sort, filter, and tab identifiers

Review list sort values (string literals, not yet passed by `reviews()`):

- `score_asc` — `rp-product-all-web-question-count-v2.js`, `rp-product-all-web-single-product-score.js`, `rp-product-desktop-web-review-gallery-v2.js`, `rp-product-web-list-reviews-v3.js`
- `score_desc` — `rp-product-all-web-question-count-v2.js`, `rp-product-all-web-single-product-score.js`, `rp-product-desktop-web-review-gallery-v2.js`, `rp-product-web-list-reviews-v3.js`
- `usefulness_desc` — `rp-product-all-web-question-count-v2.js`, `rp-product-all-web-single-product-score.js`, `rp-product-desktop-web-review-gallery-v2.js`, `rp-product-web-list-reviews-v3.js`

Filter *types* (not filter ids):

- `RESPONSE_FILTER_TYPE_BOOL` — `catalog-all-search-results-filters-active.js`, `search-desktop-search-bar-desktop.js`
- `RESPONSE_FILTER_TYPE_COLOR` — `catalog-all-search-results-filters-active.js`, `search-desktop-search-bar-desktop.js`
- `RESPONSE_FILTER_TYPE_INVALID` — `catalog-all-search-results-filters-active.js`, `search-desktop-search-bar-desktop.js`
- `RESPONSE_FILTER_TYPE_MULTI` — `catalog-all-search-results-filters-active.js`, `search-desktop-search-bar-desktop.js`
- `RESPONSE_FILTER_TYPE_RADIO` — `catalog-all-search-results-filters-active.js`, `search-desktop-search-bar-desktop.js`
- `RESPONSE_FILTER_TYPE_RANGE` — `catalog-all-search-results-filters-active.js`, `search-desktop-search-bar-desktop.js`
- `RESPONSE_FILTER_TYPE_RATING` — `catalog-all-search-results-filters-active.js`, `search-desktop-search-bar-desktop.js`

Product-page section / tab widgets. The lazy chunks `pdp-all-tabs`,
`pdp-mob-tabs-v1`, and `rp-product-all-product-tabs-v1` are **referenced** from
`pdp.js` / `rp-product.js` but were **not** in the initial load, so the
tab-key enum inside them was not downloaded. What *is* in the loaded files:

- `characteristics` (pdp_section) — `pdp-all-description-v3.js`, `pdp-all-short-characteristics-v1.js`, `pdp-desktop-product-mini-v1.js`, `pdp-mobile-characteristics-v7.js`
- `description-tab` (pdp_section) — `pdp-all-description-v3.js`
- `rich-annotation` (pdp_section) — `pdp-all-description-v3.js`
- `rich-content` (pdp_section) — `pdp-all-description-v3.js`, `vendor-pdp-rich-annotation-renderer.js`
- `search-sortings` (sort_control) — `catalog-desktop-search-results-sort-v2.js`
- `searchResultsV2` (listing_widget) — `catalog-all-infinite-virtual-paginator.js`, `catalog-search.js`, `search-desktop-search-bar-desktop.js`
- `section-description` (pdp_section) — `pdp-all-description-v3.js`
- `short-characteristics` (pdp_section) — `pdp-all-short-characteristics-v1.js`
- `tileGridDesktop` (listing_widget) — `catalog-all-infinite-virtual-paginator.js`, `entry.products.js`, `search-desktop-search-bar-desktop.js`
- `webListQuestions` (tab_widget) — `rp-product.js`
- `webListReviews` (tab_widget) — `rp-product-web-list-reviews-v3.js`, `rp-product.js`
- `webMobTab` (tab_widget) — `pdp.js`
- `webMobTabs` (tab_widget) — `pdp.js`
- `webProductTabs` (tab_widget) — `rp-product.js`
- `webQuestionCount` (tab_widget) — `rp-product.js`
- `webReviewTabs` (tab_widget) — `rp-product.js`
- `webReviewsTitle` (tab_widget) — `rp-product.js`
- `webTabs` (tab_widget) — `favorites-mobile-tabs.js`, `pdp.js`
- `webUgcNavTabs` (tab_widget) — `rp-product.js`

There is no literal `"specs"` tab key. Characteristics are the widget
`webShortCharacteristics` / `webCharacteristics` (registry in `pdp.js`) and
the section string `characteristics` in `pdp-all-description-v3.js` and
`pdp-desktop-product-mini-v1.js`. Questions are `webQuestionCount` /
`webListQuestions` (`rp-product.js`), not a `questions` query value.

## Widget names

The full registry is 1223 keys in `bundle_strings.json` → `widgets`.
Catalogue-relevant ones the client already knows by state prefix, confirmed
as registry keys:

- `tileGridDesktop` — `entry.products.js`
- `tileGrid2` — `entry.products.js`
- `skuGrid` — `entry.products.js`
- `searchResultsV2` — `catalog-search.js`
- `filters` — `catalog-search.js`, `entry.common.js`, `travel__entry.travel.js`
- `searchResultsFiltersActive` — `catalog-search.js`
- `searchResultsSort` — `catalog-search.js`
- `suggestedTapTags` — `catalog-search.js`
- `tagList` — `entry.common.js`, `travel__entry.travel.js`
- `webListReviews` — `rp-product-web-list-reviews-v3.js`, `rp-product.js`
- `webReviewsTitle` — `rp-product.js`
- `webReviewSort` — `rp-product.js`
- `webQuestionCount` — `rp-product.js`
- `webListQuestions` — `rp-product.js`
- `webDescription` — `pdp.js`
- `webShortCharacteristics` — `pdp.js`
- `webCharacteristics` — `pdp.js`
- `webGallery` — `pdp.js`
- `addressBookBarWeb` — `cart-checkout-geo.js`
- `headerCartIcon` — **not** a registry key in the loaded bundles.
- `emptyCart` — `cart-checkout-geo.js`
- `favoriteCounter` — `favorites-my-profile-wallet.js`
- `horizontalMenu` — `catalog-menu-cms-lottery-shell-uw.js`
- `catalogMenu` — `catalog-menu-cms-lottery-shell-uw.js`
- `paginator` — `host.js`
- `infiniteVirtualPaginator` — `catalog-search.js`

`reviewsTitleWidget` is the Vue `name` in `rp-product-all-reviews-title.js`;
the composer key is `webReviewsTitle`. `data-widget="webListReviews"` is
a literal in `rp-product-web-list-reviews-v3.js`.

Cart also loaded every `entry.travel.js` split (avia, hotels, railway, tours, …).
Those files contribute a large share of the 1k+ registry keys (travel checkout
widgets). They are real strings, not catalogue endpoints.

## Endpoints and actions the client does not call

### Read-shaped, worth a catalogue client knowing about

These are absent from `session.py` / `catalog.py`. Method and path are the
bundle’s own `fetch` / `actionGet` / `actionPost` literals.

- `POST /api/composer-api.bx/_action/favoriteCheckItems` — `bx-fe__common-feature-favorites__1.4.10__index.js`, `bx-fe__common-feature-favorites__1.4.12__index.js`
- `POST /api/composer-api.bx/_action/favoriteCountItems` — `bx-fe__common-feature-favorites__1.4.10__index.js`, `bx-fe__common-feature-favorites__1.4.12__index.js`
- `POST /api/composer-api.bx/_action/favoriteGetSharedItems` — `bx-fe__common-feature-favorites__1.4.10__index.js`, `bx-fe__common-feature-favorites__1.4.12__index.js`
- `POST /api/composer-api.bx/_action/favoriteGetSharedItemsV2/{param}` (path template) — `bx-fe__common-feature-favorites__1.4.10__index.js`, `bx-fe__common-feature-favorites__1.4.12__index.js`
- `GET /api/composer-api.bx/_action/favoriteLists` — `bx-fe__common-feature-favorites__1.4.10__index.js`, `bx-fe__common-feature-favorites__1.4.12__index.js`
- `POST /api/composer-api.bx/_action/favoriteListsBySku` — `bx-fe__common-feature-favorites__1.4.10__index.js`, `bx-fe__common-feature-favorites__1.4.12__index.js`
- `GET /api/composer-api.bx/_action/favoriteSuggestListTitle` — `bx-fe__common-feature-favorites__1.4.10__index.js`, `bx-fe__common-feature-favorites__1.4.12__index.js`
- `GET /api/composer-api.bx/_action/pdpGetStarsBalance?product_id={param}` (path template) — `pdp-all-sharing-button-v3.js`, `pdp-mobile-add-to-cart-v10.js`
- `GET /api/composer-api.bx/_action/summary` — `bx-fe__common-feature-cart__1.7.8__index.js`, `host.js`
- `POST /api/composer-api.bx/_action/translateProductAttributesAction` — `pdp-all-sharing-button-v3.js`, `pdp-mobile-add-to-cart-v10.js`
- `GET /api/composer-api.bx/_action/v2/catalogMenuItemV1` — `catalog-menu-all-horizontal-category-menu-v1.js`
- `GET /api/composer-api.bx/_action/v2/catalogMenuServicesV1` — `catalog-menu-all-horizontal-category-menu-v1.js`
- `GET /api/composer-api.bx/_action/v2/categoryChildV3` — `cms-desktop-catalog-menu.js`
- `POST /api/composer-api.bx/_action/v2/getSearchTapTags` — `search-desktop-search-bar-desktop.js`
- `GET /api/composer-api.bx/_action/v2/getServicesV1` — `cms-desktop-catalog-menu.js`
- `GET /api/composer-api.bx/_action/v2/horizontalContentV1` — `catalog-menu-all-horizontal-category-menu-v1.js`
- `POST /api/composer-api.bx/_action/v2/pdpViewProduct?product_id={param}` (path template) — `pdp-mobile-add-to-cart-v10.js`, `pdp-mobile-product-main.js`
- `GET /api/composer-api.bx/page/json/v{n}?url={param}` (path template) — `main.js`
- `POST /api/composer-api.bx/page/json/v{n}?url={param}` (path template) — `main.js`
- `POST /api/composer-api.bx/widget/json/v2` — `main.js`
- `POST /api/composer-api.bx/widget/json/v2/batch` — `main.js`
- `POST /api/entrypoint-api.bx/page/json/v2?url={param}` — `main.js`
- `GET /api/location/v2/areas/{param}` (path template) — `pdp-desktop-sale-v12.js`
- `GET /api/location/v2/current` — `pdp-desktop-sale-v12.js`
- `GET /api/location/v2/search` — `pdp-desktop-sale-v12.js`

Notes on the most useful ones:

- `POST /api/composer-api.bx/widget/json/v2` and `.../v2/batch` (`main.js`, `ComposerService.widget` / `widgetBatch`). This is how the site refreshes one widget (`widgetStateId` query) without refetching the whole page. The client only uses `entrypoint-api.bx/page/json/v2`.
- `POST /api/entrypoint-api.bx/page/json/v2` (`ComposerService.jsonPost` in `main.js`). Same URL as the client’s GET, but POST. Not used.
- `POST /api/composer-api.bx/_action/v2/getSearchTapTags` (`search-desktop-search-bar-desktop.js`). Suggest/tap tags. The client only loads `/searchSuggestions/search/` through the page composer.
- Menu siblings of the one menu call the client makes: `GET .../v2/categoryChildV3` (`cms-desktop-catalog-menu.js`), `GET .../v2/catalogMenuItemV1`, `GET .../v2/catalogMenuServicesV1`, `GET .../v2/horizontalContentV1` (`catalog-menu-all-horizontal-category-menu-v1.js`), `GET .../v2/getServicesV1` (`cms-desktop-catalog-menu.js`).
- `GET /api/location/v2/current` and `GET /api/location/v2/search` (`pdp-desktop-sale-v12.js`, `LocationService`, `serviceVersion` 2). `POST /api/location/v2/user/location` is the write that sets the area; not a catalogue read.
- Favorites reads the client does not use (it only opens `/my/favorites/`): `GET .../_action/favoriteLists`, `GET .../_action/favoriteSuggestListTitle` (`bx-fe__common-feature-favorites__1.4.10__index.js` and `1.4.12`). `POST favoriteCountItems` / `favoriteCheckItems` are counts, still POSTs.
- `GET .../_action/summary` (v1) still sits next to `summaryV2` in `host.js`.
- `GET .../_action/pdpGetStarsBalance?product_id=` (`pdp-mobile-add-to-cart-v10.js`).
- Review sort is not a separate endpoint. `webListReviews` takes sort ids `usefulness_desc`, `score_asc`, `score_desc` (`rp-product-web-list-reviews-v3.js`). `reviews()` does not send them.

`addressBookBarTooltip` remains a live-traffic endpoint with **no** bundle
source in this set. Do not treat it as confirmed by these files.

### Write actions present in the bundles (client correctly does not call them)

Listed so they are not mistaken for missing catalogue reads. Not a usage guide.

- `POST /api/composer-api.bx/_action/addComment` — `rp-product-all-web-question-count-v2.js`, `rp-product-all-web-single-product-score.js`, `rp-product-desktop-web-review-gallery-v2.js`, `rp-product-web-list-reviews-v3.js`
- `POST /api/composer-api.bx/_action/changeEmailV2` — `udm-desktop-profile-menu-anonymous.js`
- `POST /api/composer-api.bx/_action/changePhoneDelayedV2` — `udm-desktop-profile-menu-anonymous.js`
- `POST /api/composer-api.bx/_action/changePhoneV2` — `udm-desktop-profile-menu-anonymous.js`
- `POST /api/composer-api.bx/_action/checkInn` — `udm-commons.js`
- `POST /api/composer-api.bx/_action/cmsGetPromoIQOS` — `cms-desktop-horizontal-menu.js`
- `POST /api/composer-api.bx/_action/createCommentV2` — `rp-product-all-web-question-count-v2.js`, `rp-product-all-web-single-product-score.js`, `rp-product-desktop-web-review-gallery-v2.js`, `rp-product-web-list-reviews-v3.js`
- `POST /api/composer-api.bx/_action/emailOtpEntry` — `udm-desktop-profile-menu-anonymous.js`
- `POST /api/composer-api.bx/_action/fastEntry` — `udm-desktop-profile-menu-anonymous.js`
- `POST /api/composer-api.bx/_action/fastEntryV3` — `udm-desktop-profile-menu-anonymous.js`
- `POST /api/composer-api.bx/_action/favoriteCopySharedList` — `bx-fe__common-feature-favorites__1.4.10__index.js`, `bx-fe__common-feature-favorites__1.4.12__index.js`
- `POST /api/composer-api.bx/_action/favoriteCreateList` — `bx-fe__common-feature-favorites__1.4.10__index.js`, `bx-fe__common-feature-favorites__1.4.12__index.js`
- `POST /api/composer-api.bx/_action/favoriteListRemove` — `bx-fe__common-feature-favorites__1.4.10__index.js`, `bx-fe__common-feature-favorites__1.4.12__index.js`
- `POST /api/composer-api.bx/_action/favoriteRenameList` — `bx-fe__common-feature-favorites__1.4.10__index.js`, `bx-fe__common-feature-favorites__1.4.12__index.js`
- `POST /api/composer-api.bx/_action/favoriteShareList` — `bx-fe__common-feature-favorites__1.4.10__index.js`, `bx-fe__common-feature-favorites__1.4.12__index.js`
- `POST /api/composer-api.bx/_action/formatPhoneNumber` — `autosplit-teams_udm_components_form-field_phone_vue.js`
- `POST /api/composer-api.bx/_action/getCompanyList` — `udm-commons.js`
- `POST /api/composer-api.bx/_action/getNextHammerWaveSecondsLeft` — `marketing-big-promo-counter-navbar-desktop.js`
- `POST /api/composer-api.bx/_action/getSecondsLeftForCampaign` — `marketing-big-promo-counter-navbar-desktop.js`
- `POST /api/composer-api.bx/_action/goCheckoutLite` — `pdp-mobile-one-click-button-v3.js`
- `POST /api/composer-api.bx/_action/loadComment` — `rp-product-all-web-question-count-v2.js`, `rp-product-all-web-single-product-score.js`, `rp-product-desktop-web-review-gallery-v2.js`, `rp-product-web-list-reviews-v3.js`
- `POST /api/composer-api.bx/_action/logout` — `udm-desktop-profile-menu-anonymous.js`
- `POST /api/composer-api.bx/_action/logoutOnAll` — `udm-commons.js`
- `POST /api/composer-api.bx/_action/minifyURL` — `pdp-all-sharing-button-v3.js`, `pdp-mobile-add-to-cart-v10.js`
- `POST /api/composer-api.bx/_action/ozonIdAuthToken` — `udm-commons.js`
- `POST /api/composer-api.bx/_action/ozonIdAuthUrl` — `udm-commons.js`
- `POST /api/composer-api.bx/_action/ozonidUnbindSeller` — `udm-commons.js`
- `POST /api/composer-api.bx/_action/patchUserAccount` — `udm-commons.js`
- `POST /api/composer-api.bx/_action/patchUserAccountV2` — `udm-commons.js`
- `POST /api/composer-api.bx/_action/putUserLegalDetails` — `udm-commons.js`
- `POST /api/composer-api.bx/_action/registerSearchEvent` — `search-desktop-search-bar-desktop.js`
- `POST /api/composer-api.bx/_action/registrationV1` — `udm-desktop-profile-menu-anonymous.js`
- `POST /api/composer-api.bx/_action/removeComment` — `rp-product-all-web-question-count-v2.js`, `rp-product-all-web-single-product-score.js`, `rp-product-desktop-web-review-gallery-v2.js`, `rp-product-web-list-reviews-v3.js`
- `POST /api/composer-api.bx/_action/removeReview` — `rp-product-all-web-question-count-v2.js`, `rp-product-all-web-single-product-score.js`, `rp-product-desktop-web-review-gallery-v2.js`, `rp-product-web-list-reviews-v3.js`
- `POST /api/composer-api.bx/_action/reportComment` — `rp-product-all-web-question-count-v2.js`, `rp-product-all-web-single-product-score.js`, `rp-product-desktop-web-review-gallery-v2.js`, `rp-product-web-list-reviews-v3.js`
- `POST /api/composer-api.bx/_action/reportReview` — `rp-product-all-web-question-count-v2.js`, `rp-product-all-web-single-product-score.js`, `rp-product-desktop-web-review-gallery-v2.js`, `rp-product-web-list-reviews-v3.js`
- `POST /api/composer-api.bx/_action/rpDeleteMyReviewV2` — `rp-product-all-web-question-count-v2.js`, `rp-product-all-web-single-product-score.js`, `rp-product-desktop-web-review-gallery-v2.js`, `rp-product-web-list-reviews-v3.js`
- `POST /api/composer-api.bx/_action/rpGetCommentsByReviewUuid` — `rp-product-all-web-question-count-v2.js`, `rp-product-all-web-single-product-score.js`, `rp-product-desktop-web-review-gallery-v2.js`, `rp-product-web-list-reviews-v3.js`
- `POST /api/composer-api.bx/_action/rpIgnoreItem` — `rp-product-all-web-question-count-v2.js`, `rp-product-all-web-single-product-score.js`, `rp-product-desktop-web-review-gallery-v2.js`, `rp-product-web-list-reviews-v3.js`
- `POST /api/composer-api.bx/_action/rpImageUpload` — `rp-product-all-web-question-count-v2.js`, `rp-product-all-web-single-product-score.js`, `rp-product-desktop-web-review-gallery-v2.js`, `rp-product-web-list-reviews-v3.js`
- … 29 more write-shaped paths are in `bundle_strings.json` → `actions`.

Review mutations encoded as action-name literals (same `_action` prefix,
`rp-product-web-list-reviews-v3.js` and siblings): `createCommentV2`,
`removeReview`, `rpDeleteMyReviewV2`, `rpGetCommentsByReviewUuid` (this one
is a read), `rpSetOpinionUsefulnessV2`, `v2/rpReportAbuseV2`, `voteReview`,
`reportReview`.

### Also fetched, not composer

- `POST /pop-stats-collector/api/v2/pop-stats/send` — `1.0.4.js` (CDN RUM).
- `POST {xapi}/api/logs-gateway/input` — `main.js` (`ClientLogger`). Host is the xapi gateway, not `ozon.by`.

## Gaps

- Search HTML was the brand-predicted category, not a raw `/search/?text=` document. Search bundles still loaded.
- Lazy widget chunks named from registries but not requested on first paint (for example `pdp-all-tabs`, `rp-product-web-review-sort-desktop`, `catalog-all-search-suggestions`) were not downloaded. Their names are in the parent bundles (`pdp.js`, `rp-product.js`, `catalog-search.js`) and therefore in `widgets`, but their bodies are absent.
- `addressBookBarTooltip`, `from_global`, `__rr`, `prv`, and `set_sm` are not in this bundle set.
