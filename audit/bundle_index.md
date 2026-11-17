# Bundle index

Static JS captured from ozon.by on 2026-10-16 via one CDP pass
(new tab, then closed) that recorded `document` script URLs and
`performance` resource entries. Files were then GET from `st.ozone.ru`
with urllib. No POSTs.

Page types and the URL that actually loaded:

- **home**: `https://ozon.by/?__rr=1` — Ozon Беларусь маркетплейс – миллионы товаров по выгодным ценам
- **search**: `https://ozon.by/category/smartfony-15502/apple-26303000/?brand_was_predicted=true&category_was_predicted=true&deny_category_prediction=true&from_global=true&text=iphone` — iphone - купить на OZON в Беларуси
- **category**: `https://ozon.by/category/elektronika-15500/` — Электроника купить на OZON по низкой цене
- **product**: `https://ozon.by/product/apple-smartfon-iphone-17-sim-esim-8-256-gb-nano-sim-zelenyy-2830520301/?sh=8XNzq49s8A` — Смартфон Apple iphone17 256 ГБ 8 ГБ Зеленый 6.3 MG6N4 купить c доставкой на OZON по низкой
- **reviews**: `https://ozon.by/reviews/2830520301/` — 656 отзыв на Apple Смартфон iPhone 17 SIM+eSIM 8/256 ГБ, Nano-SIM, зеленый от покупателей 
- **cart**: `https://ozon.by/cart` — OZON - Моя корзина
- **favorites**: `https://ozon.by/my/favorites/` — Избранное — OZON

Search note: requesting `https://ozon.by/search/?text=iphone&from_global=true`
was rewritten by the site to a predicted brand category
(`/category/smartfony-15502/apple-26303000/?text=iphone&...`).
That page still loaded the catalog-search microfrontend
(`catalog-search.js`, sort and active-filter bundles), so search widgets
are covered. A non-rewritten `/search/?text=` HTML document was not
snapshotted separately (CDP was used once).

Deduped bundles: **315**. Downloaded bytes: **4800995**.
None exceeded the 15 MB skip threshold. Basename collisions
(`index.js`, `entry.*.js`) are disambiguated with a parent-path prefix;
the original basename is kept as the suffix.

| URL | local file | bytes | page types |
|---|---|---:|---|
| `https://st.ozone.ru/assets/aeebf0af/composer-all-paginator.js` | `composer-all-paginator.js` | 42058 | cart, favorites, home, product |
| `https://st.ozone.ru/assets/aeebf0af/detached/black-friday/autosplit-teams_black-friday_components_counter-nav-bar_timer_index_vue.js` | `autosplit-teams_black-friday_components_counter-nav-bar_timer_index_vue.js` | 4291 | home |
| `https://st.ozone.ru/assets/aeebf0af/detached/black-friday/autosplit-teams_black-friday_components_pdp_index_vue.js` | `autosplit-teams_black-friday_components_pdp_index_vue.js` | 7087 | product |
| `https://st.ozone.ru/assets/aeebf0af/detached/black-friday/autosplit-teams_black-friday_components_timer-badge_index_vue.js` | `autosplit-teams_black-friday_components_timer-badge_index_vue.js` | 2876 | product |
| `https://st.ozone.ru/assets/aeebf0af/detached/black-friday/entry.marketing.js` | `black-friday__entry.marketing.js` | 19913 | home, product |
| `https://st.ozone.ru/assets/aeebf0af/detached/black-friday/marketing-big-promo-counter-navbar-desktop.js` | `marketing-big-promo-counter-navbar-desktop.js` | 4820 | home |
| `https://st.ozone.ru/assets/aeebf0af/detached/black-friday/marketing-big-promo-pdp-desktop.js` | `marketing-big-promo-pdp-desktop.js` | 6577 | product |
| `https://st.ozone.ru/assets/aeebf0af/detached/common/autosplit-teams_common_components_filters-color-icon_index_vue-teams_common_components_filter-7c3b30.js` | `autosplit-teams_common_components_filters-color-icon_index_vue-teams_common_components_filter-7c3b30.js` | 12040 | category, search |
| `https://st.ozone.ru/assets/aeebf0af/detached/common/autosplit-teams_common_components_filters-desktop-types-checkbox_index_vue-teams_common_compo-d37668.js` | `autosplit-teams_common_components_filters-desktop-types-checkbox_index_vue-teams_common_compo-d37668.js` | 18637 | category, search |
| `https://st.ozone.ru/assets/aeebf0af/detached/common/common-all-annotation.js` | `common-all-annotation.js` | 16295 | cart, product |
| `https://st.ozone.ru/assets/aeebf0af/detached/common/common-all-breadcrumbs.js` | `common-all-breadcrumbs.js` | 4215 | product, reviews |
| `https://st.ozone.ru/assets/aeebf0af/detached/common/common-all-results_header.js` | `common-all-results_header.js` | 928 | category |
| `https://st.ozone.ru/assets/aeebf0af/detached/common/common-all-status-widget.js` | `common-all-status-widget.js` | 4953 | favorites |
| `https://st.ozone.ru/assets/aeebf0af/detached/common/common-all-text-block.js` | `common-all-text-block.js` | 1484 | product |
| `https://st.ozone.ru/assets/aeebf0af/detached/common/common-desktop-filters.js` | `common-desktop-filters.js` | 94397 | category, search |
| `https://st.ozone.ru/assets/aeebf0af/detached/common/common-desktop-island.js` | `common-desktop-island.js` | 1877 | category, favorites |
| `https://st.ozone.ru/assets/aeebf0af/detached/common/entry.common.js` | `entry.common.js` | 57411 | cart, category, favorites, product, reviews, search |
| `https://st.ozone.ru/assets/aeebf0af/detached/csma/csma-desktop-service_elements-v2.js` | `csma-desktop-service_elements-v2.js` | 2093 | cart, category, favorites, home, product, reviews, search |
| `https://st.ozone.ru/assets/aeebf0af/detached/csma/entry.csma.js` | `csma__entry.csma.js` | 77117 | cart, category, favorites, home, product, reviews, search |
| `https://st.ozone.ru/assets/aeebf0af/detached/express/entry.express.js` | `entry.express.js` | 53683 | category, search |
| `https://st.ozone.ru/assets/aeebf0af/detached/express/express-all-home-button.js` | `express-all-home-button.js` | 2528 | category, search |
| `https://st.ozone.ru/assets/aeebf0af/detached/marketing-info/entry.marketing-info.js` | `entry.marketing-info.js` | 33957 | product |
| `https://st.ozone.ru/assets/aeebf0af/detached/marketing/entry.marketing.js` | `marketing__entry.marketing.js` | 52435 | home, product |
| `https://st.ozone.ru/assets/aeebf0af/detached/my-profile/entry.price-feedback.js` | `entry.price-feedback.js` | 17968 | product |
| `https://st.ozone.ru/assets/aeebf0af/detached/navi/autosplit-teams_navi_components_tile-grid-item_index_vue.js` | `autosplit-teams_navi_components_tile-grid-item_index_vue.js` | 38338 | cart, category, favorites, home, product, search |
| `https://st.ozone.ru/assets/aeebf0af/detached/navi/autosplit-teams_navi_components_tile-top-right-buttons_index_vue.js` | `autosplit-teams_navi_components_tile-top-right-buttons_index_vue.js` | 3754 | cart, category, favorites, home, product, search |
| `https://st.ozone.ru/assets/aeebf0af/detached/navi/autosplit-teams_navi_molecules_tile-add-to-cart-button_index_vue.js` | `autosplit-teams_navi_molecules_tile-add-to-cart-button_index_vue.js` | 15539 | cart, category, favorites, home, product, search |
| `https://st.ozone.ru/assets/aeebf0af/detached/navi/entry.products.js` | `entry.products.js` | 53267 | cart, category, favorites, home, product, search |
| `https://st.ozone.ru/assets/aeebf0af/detached/navi/navi-commons.js` | `navi-commons.js` | 18277 | cart, category, favorites, home, product, search |
| `https://st.ozone.ru/assets/aeebf0af/detached/navi/products-desktop-tile-grid-desktop.js` | `products-desktop-tile-grid-desktop.js` | 35558 | cart, category, favorites, home, search |
| `https://st.ozone.ru/assets/aeebf0af/detached/navi/products-desktop-tile-scroll-desktop.js` | `products-desktop-tile-scroll-desktop.js` | 34204 | product |
| `https://st.ozone.ru/assets/aeebf0af/detached/swa/entry.swa.js` | `entry.swa.js` | 18373 | cart, category, favorites, search |
| `https://st.ozone.ru/assets/aeebf0af/detached/swa/swa-tag-list-modal.js` | `swa-tag-list-modal.js` | 8981 | search |
| `https://st.ozone.ru/assets/aeebf0af/detached/udm/autosplit-teams_udm_components_authorization-service_index_vue.js` | `autosplit-teams_udm_components_authorization-service_index_vue.js` | 39242 | cart, category, favorites, home, product, reviews, search |
| `https://st.ozone.ru/assets/aeebf0af/detached/udm/autosplit-teams_udm_components_enter-otp_v2_index_vue-teams_udm_components_submit-button_index_vue.js` | `autosplit-teams_udm_components_enter-otp_v2_index_vue-teams_udm_components_submit-button_index_vue.js` | 8529 | cart, category, favorites, home, product, reviews, search |
| `https://st.ozone.ru/assets/aeebf0af/detached/udm/autosplit-teams_udm_components_form-field_index_vue.js` | `autosplit-teams_udm_components_form-field_index_vue.js` | 5408 | cart, category, favorites, home, product, reviews, search |
| `https://st.ozone.ru/assets/aeebf0af/detached/udm/autosplit-teams_udm_components_form-field_phone_vue.js` | `autosplit-teams_udm_components_form-field_phone_vue.js` | 4707 | cart, category, favorites, home, product, reviews, search |
| `https://st.ozone.ru/assets/aeebf0af/detached/udm/entry.csma.js` | `udm__entry.csma.js` | 53923 | cart, category, favorites, home, product, reviews, search |
| `https://st.ozone.ru/assets/aeebf0af/detached/udm/udm-commons.js` | `udm-commons.js` | 37643 | cart, category, favorites, home, product, reviews, search |
| `https://st.ozone.ru/assets/aeebf0af/detached/udm/udm-desktop-profile-menu-anonymous.js` | `udm-desktop-profile-menu-anonymous.js` | 21861 | cart, category, favorites, home, product, reviews, search |
| `https://st.ozone.ru/assets/aeebf0af/exposed-directives.js` | `exposed-directives.js` | 6056 | cart, category, favorites, home, product, reviews, search |
| `https://st.ozone.ru/assets/aeebf0af/host.js` | `host.js` | 73887 | cart, category, favorites, home, product, reviews, search |
| `https://st.ozone.ru/assets/aeebf0af/i18n-ru.js` | `i18n-ru.js` | 8765 | cart, category, favorites, home, product, reviews, search |
| `https://st.ozone.ru/assets/aeebf0af/layout-all-sticky-container.js` | `layout-all-sticky-container.js` | 1526 | cart, product |
| `https://st.ozone.ru/assets/aeebf0af/layout-desktop-grid.js` | `layout-desktop-grid.js` | 2647 | cart, category, favorites, home, product, reviews, search |
| `https://st.ozone.ru/assets/aeebf0af/main.js` | `main.js` | 158797 | cart, category, favorites, home, product, reviews, search |
| `https://st.ozone.ru/assets/aeebf0af/notification-service.js` | `notification-service.js` | 21348 | cart, category, favorites, home, product, reviews, search |
| `https://st.ozone.ru/assets/aeebf0af/push-modal.js` | `push-modal.js` | 4265 | cart, category, favorites, home, product, reviews, search |
| `https://st.ozone.ru/assets/aeebf0af/runtime.js` | `runtime.js` | 10374 | cart, category, favorites, home, product, reviews, search |
| `https://st.ozone.ru/assets/aeebf0af/vendor-core.js` | `vendor-core.js` | 88271 | cart, category, favorites, home, product, reviews, search |
| `https://st.ozone.ru/assets/aeebf0af/vendor-vue.js` | `vendor-vue.js` | 74679 | cart, category, favorites, home, product, reviews, search |
| `https://st.ozone.ru/s3/assets-24914/769a37c1/marketing-desktop-adv-banner-v4.js` | `marketing-desktop-adv-banner-v4.js` | 18658 | home |
| `https://st.ozone.ru/s3/assets-24914/769a37c1/microfront/rtb.js` | `rtb.js` | 26192 | category, home |
| `https://st.ozone.ru/s3/assets-27147/70dadc0d/catalog-menu-all-horizontal-category-menu-v1.js` | `catalog-menu-all-horizontal-category-menu-v1.js` | 21338 | category |
| `https://st.ozone.ru/s3/assets-27147/70dadc0d/cms-all-custom-html.js` | `cms-all-custom-html.js` | 6604 | product |
| `https://st.ozone.ru/s3/assets-27147/70dadc0d/cms-all-season-widget.js` | `cms-all-season-widget.js` | 9717 | home |
| `https://st.ozone.ru/s3/assets-27147/70dadc0d/cms-all-wallpaper.js` | `cms-all-wallpaper.js` | 2221 | cart, category, favorites, home, reviews, search |
| `https://st.ozone.ru/s3/assets-27147/70dadc0d/cms-desktop-catalog-menu.js` | `cms-desktop-catalog-menu.js` | 46709 | cart, category, favorites, home, product, reviews, search |
| `https://st.ozone.ru/s3/assets-27147/70dadc0d/cms-desktop-footer.js` | `cms-desktop-footer.js` | 16285 | cart, category, favorites, home, product, reviews, search |
| `https://st.ozone.ru/s3/assets-27147/70dadc0d/cms-desktop-header.js` | `cms-desktop-header.js` | 9353 | cart, category, favorites, home, product, reviews, search |
| `https://st.ozone.ru/s3/assets-27147/70dadc0d/cms-desktop-horizontal-menu.js` | `cms-desktop-horizontal-menu.js` | 10813 | cart, category, favorites, home, product, reviews, search |
| `https://st.ozone.ru/s3/assets-27147/70dadc0d/cms-desktop-selected-currency-language.js` | `cms-desktop-selected-currency-language.js` | 2015 | cart, category, favorites, home, product, reviews, search |
| `https://st.ozone.ru/s3/assets-27147/70dadc0d/cms-mobile-separator.js` | `cms-mobile-separator.js` | 1276 | cart, category, favorites, home, product, reviews, search |
| `https://st.ozone.ru/s3/assets-27147/70dadc0d/microfront/catalog-menu-cms-lottery-shell-uw.js` | `catalog-menu-cms-lottery-shell-uw.js` | 58811 | cart, category, favorites, home, product, reviews, search |
| `https://st.ozone.ru/s3/assets-27147/70dadc0d/uw-desktop-object-line.js` | `uw-desktop-object-line.js` | 15262 | category |
| `https://st.ozone.ru/s3/assets-27147/70dadc0d/uw-desktop-object-thumbnail-list.js` | `uw-desktop-object-thumbnail-list.js` | 8710 | category |
| `https://st.ozone.ru/s3/assets-27400/ed351a2a/addressBookMap-all-addressbook-bar.js` | `addressBookMap-all-addressbook-bar.js` | 38354 | cart, category, favorites, home, product, reviews, search |
| `https://st.ozone.ru/s3/assets-27400/ed351a2a/cart-all-emptyCart-2.js` | `cart-all-emptyCart-2.js` | 7661 | cart |
| `https://st.ozone.ru/s3/assets-27400/ed351a2a/cart-all-headerCartIcon-v2.js` | `cart-all-headerCartIcon-v2.js` | 2224 | cart, category, favorites, home, product, reviews, search |
| `https://st.ozone.ru/s3/assets-27400/ed351a2a/cart-all-master.js` | `cart-all-master.js` | 11616 | cart |
| `https://st.ozone.ru/s3/assets-27400/ed351a2a/microfront/cart-checkout-geo.js` | `cart-checkout-geo.js` | 92959 | cart, category, favorites, home, product, reviews, search |
| `https://st.ozone.ru/s3/assets-27497/0ba007aa/detached/avia/entry.travel.js` | `avia__entry.travel.js` | 37662 | cart |
| `https://st.ozone.ru/s3/assets-27497/0ba007aa/detached/b2b/entry.travel.js` | `b2b__entry.travel.js` | 32414 | cart |
| `https://st.ozone.ru/s3/assets-27497/0ba007aa/detached/hotels/entry.travel.js` | `hotels__entry.travel.js` | 56902 | cart |
| `https://st.ozone.ru/s3/assets-27497/0ba007aa/detached/marketing/entry.travel.js` | `marketing__entry.travel.js` | 19370 | cart |
| `https://st.ozone.ru/s3/assets-27497/0ba007aa/detached/railway/entry.travel.js` | `railway__entry.travel.js` | 38570 | cart |
| `https://st.ozone.ru/s3/assets-27497/0ba007aa/detached/seo/entry.travel.js` | `seo__entry.travel.js` | 42366 | cart |
| `https://st.ozone.ru/s3/assets-27497/0ba007aa/detached/services/entry.travel.js` | `services__entry.travel.js` | 30679 | cart |
| `https://st.ozone.ru/s3/assets-27497/0ba007aa/detached/tours/entry.travel.js` | `tours__entry.travel.js` | 32121 | cart |
| `https://st.ozone.ru/s3/assets-27497/0ba007aa/detached/travel/entry.travel.js` | `travel__entry.travel.js` | 182720 | cart |
| `https://st.ozone.ru/s3/assets-28467/4baf0530/microfront/pdp.js` | `pdp.js` | 74007 | product, reviews |
| `https://st.ozone.ru/s3/assets-28467/4baf0530/pdp-all-add-to-compare-v4.js` | `pdp-all-add-to-compare-v4.js` | 6871 | product |
| `https://st.ozone.ru/s3/assets-28467/4baf0530/pdp-all-aspects-v4.js` | `pdp-all-aspects-v4.js` | 67694 | product |
| `https://st.ozone.ru/s3/assets-28467/4baf0530/pdp-all-attachments.js` | `pdp-all-attachments.js` | 5177 | product |
| `https://st.ozone.ru/s3/assets-28467/4baf0530/pdp-all-current-seller-v5.js` | `pdp-all-current-seller-v5.js` | 20860 | product |
| `https://st.ozone.ru/s3/assets-28467/4baf0530/pdp-all-delivery-v7.js` | `pdp-all-delivery-v7.js` | 20148 | product |
| `https://st.ozone.ru/s3/assets-28467/4baf0530/pdp-all-description-v3.js` | `pdp-all-description-v3.js` | 16653 | product |
| `https://st.ozone.ru/s3/assets-28467/4baf0530/pdp-all-detail-sku-v2.js` | `pdp-all-detail-sku-v2.js` | 5903 | product |
| `https://st.ozone.ru/s3/assets-28467/4baf0530/pdp-all-hashtags-v1.js` | `pdp-all-hashtags-v1.js` | 2179 | product |
| `https://st.ozone.ru/s3/assets-28467/4baf0530/pdp-all-producer-info.js` | `pdp-all-producer-info.js` | 1631 | product |
| `https://st.ozone.ru/s3/assets-28467/4baf0530/pdp-all-product-heading-v3.js` | `pdp-all-product-heading-v3.js` | 2543 | product |
| `https://st.ozone.ru/s3/assets-28467/4baf0530/pdp-all-sharing-button-v3.js` | `pdp-all-sharing-button-v3.js` | 9910 | product |
| `https://st.ozone.ru/s3/assets-28467/4baf0530/pdp-all-short-characteristics-v1.js` | `pdp-all-short-characteristics-v1.js` | 7088 | product |
| `https://st.ozone.ru/s3/assets-28467/4baf0530/pdp-all-sticky-column-v1.js` | `pdp-all-sticky-column-v1.js` | 1657 | product |
| `https://st.ozone.ru/s3/assets-28467/4baf0530/pdp-all-sticky-product-v2.js` | `pdp-all-sticky-product-v2.js` | 12446 | product |
| `https://st.ozone.ru/s3/assets-28467/4baf0530/pdp-desktop-gallery-v6.js` | `pdp-desktop-gallery-v6.js` | 93609 | product |
| `https://st.ozone.ru/s3/assets-28467/4baf0530/pdp-desktop-product-mini-v1.js` | `pdp-desktop-product-mini-v1.js` | 4546 | reviews |
| `https://st.ozone.ru/s3/assets-28467/4baf0530/pdp-desktop-sale-v12.js` | `pdp-desktop-sale-v12.js` | 7488 | product |
| `https://st.ozone.ru/s3/assets-28467/4baf0530/pdp-mobile-add-to-cart-v10.js` | `pdp-mobile-add-to-cart-v10.js` | 36429 | reviews |
| `https://st.ozone.ru/s3/assets-28467/4baf0530/pdp-mobile-brand-v4.js` | `pdp-mobile-brand-v4.js` | 7697 | product |
| `https://st.ozone.ru/s3/assets-28467/4baf0530/pdp-mobile-characteristics-v7.js` | `pdp-mobile-characteristics-v7.js` | 18677 | product, reviews |
| `https://st.ozone.ru/s3/assets-28467/4baf0530/pdp-mobile-grid.js` | `pdp-mobile-grid.js` | 4887 | product, reviews |
| `https://st.ozone.ru/s3/assets-28467/4baf0530/pdp-mobile-one-click-button-v3.js` | `pdp-mobile-one-click-button-v3.js` | 4610 | product |
| `https://st.ozone.ru/s3/assets-28467/4baf0530/pdp-mobile-price-v6.js` | `pdp-mobile-price-v6.js` | 25788 | reviews |
| `https://st.ozone.ru/s3/assets-28467/4baf0530/pdp-mobile-product-main.js` | `pdp-mobile-product-main.js` | 2539 | product |
| `https://st.ozone.ru/s3/assets-28467/4baf0530/vendor-lodash.js` | `vendor-lodash.js` | 9489 | product, reviews |
| `https://st.ozone.ru/s3/assets-28467/4baf0530/vendor-pdp-rich-annotation-renderer.js` | `vendor-pdp-rich-annotation-renderer.js` | 47029 | product |
| `https://st.ozone.ru/s3/assets-28467/4baf0530/vendor-vue-lazy-hydration.js` | `vendor-vue-lazy-hydration.js` | 2791 | product, reviews |
| `https://st.ozone.ru/s3/assets-50156/3c1be439/favorites-all-favorite-counter-v2.js` | `favorites-all-favorite-counter-v2.js` | 1796 | cart, category, favorites, home, product, reviews, search |
| `https://st.ozone.ru/s3/assets-50156/3c1be439/favorites-mobile-tabs.js` | `favorites-mobile-tabs.js` | 3017 | favorites |
| `https://st.ozone.ru/s3/assets-50156/3c1be439/microfront/favorites-my-profile-wallet.js` | `favorites-my-profile-wallet.js` | 52088 | cart, category, favorites, home, product, reviews, search |
| `https://st.ozone.ru/s3/assets-66613/946cdcd4/catalog-all-infinite-virtual-paginator.js` | `catalog-all-infinite-virtual-paginator.js` | 32999 | category, search |
| `https://st.ozone.ru/s3/assets-66613/946cdcd4/catalog-all-search-results-filters-active.js` | `catalog-all-search-results-filters-active.js` | 7494 | category, search |
| `https://st.ozone.ru/s3/assets-66613/946cdcd4/catalog-desktop-search-results-sort-v2.js` | `catalog-desktop-search-results-sort-v2.js` | 2631 | category, search |
| `https://st.ozone.ru/s3/assets-66613/946cdcd4/microfront/catalog-search.js` | `catalog-search.js` | 76602 | cart, category, favorites, home, product, reviews, search |
| `https://st.ozone.ru/s3/assets-66613/946cdcd4/search-desktop-search-bar-desktop.js` | `search-desktop-search-bar-desktop.js` | 140588 | cart, category, favorites, home, product, reviews, search |
| `https://st.ozone.ru/s3/assets-75252/8f8da31d/microfront/rp-product.js` | `rp-product.js` | 58169 | product, reviews |
| `https://st.ozone.ru/s3/assets-75252/8f8da31d/rp-product-all-list-photos-v2.js` | `rp-product-all-list-photos-v2.js` | 9866 | product |
| `https://st.ozone.ru/s3/assets-75252/8f8da31d/rp-product-all-reviews-title.js` | `rp-product-all-reviews-title.js` | 8513 | reviews |
| `https://st.ozone.ru/s3/assets-75252/8f8da31d/rp-product-all-web-anchor.js` | `rp-product-all-web-anchor.js` | 606 | product |
| `https://st.ozone.ru/s3/assets-75252/8f8da31d/rp-product-all-web-question-count-v2.js` | `rp-product-all-web-question-count-v2.js` | 5226 | product |
| `https://st.ozone.ru/s3/assets-75252/8f8da31d/rp-product-all-web-single-product-score.js` | `rp-product-all-web-single-product-score.js` | 5820 | product |
| `https://st.ozone.ru/s3/assets-75252/8f8da31d/rp-product-desktop-web-review-gallery-v2.js` | `rp-product-desktop-web-review-gallery-v2.js` | 172042 | product, reviews |
| `https://st.ozone.ru/s3/assets-75252/8f8da31d/rp-product-web-list-reviews-v3.js` | `rp-product-web-list-reviews-v3.js` | 145737 | reviews |
| `https://st.ozone.ru/s3/client-metrics/cdn/1.0.4.js` | `1.0.4.js` | 70053 | favorites, home |
| `https://st.ozone.ru/s3/client-metrics/cpm-ozon@5.9.6.js` | `cpm-ozon@5.9.6.js` | 66327 | cart, category, favorites, home, product, reviews, search |
| `https://st.ozone.ru/s3/fe-icons/1.69.0/ic_m_box_filled.js` | `ic_m_box_filled.js` | 849 | cart, category, favorites, home, product, reviews, search |
| `https://st.ozone.ru/s3/fe-icons/1.69.0/ic_m_cancel_filled.js` | `ic_m_cancel_filled.js` | 582 | category, search |
| `https://st.ozone.ru/s3/fe-icons/1.69.0/ic_m_catalog_tile_filled.js` | `ic_m_catalog_tile_filled.js` | 738 | cart, category, favorites, home, product, reviews, search |
| `https://st.ozone.ru/s3/fe-icons/1.69.0/ic_m_chevron_left_filled.js` | `ic_m_chevron_left_filled.js` | 481 | search |
| `https://st.ozone.ru/s3/fe-icons/1.69.0/ic_m_chevron_up_filled.js` | `ic_m_chevron_up_filled.js` | 479 | category, search |
| `https://st.ozone.ru/s3/fe-icons/1.69.0/ic_m_flag_russia.js` | `ic_m_flag_russia.js` | 584 | cart, category, favorites, home, product, reviews, search |
| `https://st.ozone.ru/s3/fe-icons/1.69.0/ic_m_grocery_cart_filled.js` | `ic_m_grocery_cart_filled.js` | 777 | cart, category, favorites, home, product, reviews, search |
| `https://st.ozone.ru/s3/fe-icons/1.69.0/ic_m_heart_filled.js` | `ic_m_heart_filled.js` | 517 | cart, category, favorites, home, product, reviews, search |
| `https://st.ozone.ru/s3/fe-icons/1.69.0/ic_m_info_filled.js` | `ic_m_info_filled.js` | 456 | category, search |
| `https://st.ozone.ru/s3/fe-icons/1.69.0/ic_m_multicolor_heart.js` | `ic_m_multicolor_heart.js` | 1041 | cart, favorites, home, search |
| `https://st.ozone.ru/s3/fe-icons/1.69.0/ic_m_odnoklassniki_filled.js` | `ic_m_odnoklassniki_filled.js` | 1656 | cart, category, favorites, home, product, reviews, search |
| `https://st.ozone.ru/s3/fe-icons/1.69.0/ic_m_play_sign_filled.js` | `ic_m_play_sign_filled.js` | 401 | reviews |
| `https://st.ozone.ru/s3/fe-icons/1.69.0/ic_m_status_points_filled.js` | `ic_m_status_points_filled.js` | 581 | cart, favorites, search |
| `https://st.ozone.ru/s3/fe-icons/1.69.0/ic_m_telegram_filled.js` | `ic_m_telegram_filled.js` | 855 | cart, category, favorites, home, product, reviews, search |
| `https://st.ozone.ru/s3/fe-icons/1.69.0/ic_m_visually_impaired_filled.js` | `ic_m_visually_impaired_filled.js` | 1360 | cart, category, favorites, home, product, reviews, search |
| `https://st.ozone.ru/s3/fe-icons/1.69.0/ic_m_vk_filled.js` | `ic_m_vk_filled.js` | 793 | cart, category, favorites, home, product, reviews, search |
| `https://st.ozone.ru/s3/fe-icons/1.69.0/ic_s_anonymous_filled_compact.js` | `ic_s_anonymous_filled_compact.js` | 771 | cart, category, favorites, home, product, reviews, search |
| `https://st.ozone.ru/s3/fe-icons/1.69.0/ic_s_appliances_filled.js` | `ic_s_appliances_filled.js` | 873 | cart, category, favorites, home, product, reviews, search |
| `https://st.ozone.ru/s3/fe-icons/1.69.0/ic_s_car_filled.js` | `ic_s_car_filled.js` | 899 | cart, category, favorites, home, product, reviews, search |
| `https://st.ozone.ru/s3/fe-icons/1.69.0/ic_s_chevron_left.js` | `ic_s_chevron_left.js` | 466 | cart, favorites, home, search |
| `https://st.ozone.ru/s3/fe-icons/1.69.0/ic_s_chevron_right.js` | `ic_s_chevron_right.js` | 485 | cart, favorites, home, search |
| `https://st.ozone.ru/s3/fe-icons/1.69.0/ic_s_compare_default_filled.js` | `ic_s_compare_default_filled.js` | 770 | product |
| `https://st.ozone.ru/s3/fe-icons/1.69.0/ic_s_confirmed_filled_compact.js` | `ic_s_confirmed_filled_compact.js` | 535 | search |
| `https://st.ozone.ru/s3/fe-icons/1.69.0/ic_s_dialog_filled_compact.js` | `ic_s_dialog_filled_compact.js` | 551 | cart, favorites, home, search |
| `https://st.ozone.ru/s3/fe-icons/1.69.0/ic_s_food_recipes_filled.js` | `ic_s_food_recipes_filled.js` | 1345 | cart, category, favorites, home, product, reviews, search |
| `https://st.ozone.ru/s3/fe-icons/1.69.0/ic_s_goodness_filled.js` | `ic_s_goodness_filled.js` | 1112 | cart, category, favorites, home, product, reviews, search |
| `https://st.ozone.ru/s3/fe-icons/1.69.0/ic_s_grocery_cart_filled.js` | `ic_s_grocery_cart_filled.js` | 909 | cart, favorites, search |
| `https://st.ozone.ru/s3/fe-icons/1.69.0/ic_s_home_and_garden_filled.js` | `ic_s_home_and_garden_filled.js` | 853 | cart, category, favorites, home, product, reviews, search |
| `https://st.ozone.ru/s3/fe-icons/1.69.0/ic_s_hot_filled_compact.js` | `ic_s_hot_filled_compact.js` | 672 | search |
| `https://st.ozone.ru/s3/fe-icons/1.69.0/ic_s_kids_filled.js` | `ic_s_kids_filled.js` | 1306 | cart, category, favorites, home, product, reviews, search |
| `https://st.ozone.ru/s3/fe-icons/1.69.0/ic_s_kiosk_filled_compact.js` | `ic_s_kiosk_filled_compact.js` | 1309 | search |
| `https://st.ozone.ru/s3/fe-icons/1.69.0/ic_s_legal_entity_filled.js` | `ic_s_legal_entity_filled.js` | 1252 | cart, category, favorites, home, product, reviews, search |
| `https://st.ozone.ru/s3/fe-icons/1.69.0/ic_s_mobile_phone_filled.js` | `ic_s_mobile_phone_filled.js` | 681 | cart, category, favorites, home, product, reviews, search |
| `https://st.ozone.ru/s3/fe-icons/1.69.0/ic_s_ozon_circle_filled_compact.js` | `ic_s_ozon_circle_filled_compact.js` | 1353 | cart, favorites, home, search |
| `https://st.ozone.ru/s3/fe-icons/1.69.0/ic_s_questions_and_answers_filled.js` | `ic_s_questions_and_answers_filled.js` | 911 | product |
| `https://st.ozone.ru/s3/fe-icons/1.69.0/ic_s_special_luggage_filled.js` | `ic_s_special_luggage_filled.js` | 1577 | cart, category, favorites, home, product, reviews, search |
| `https://st.ozone.ru/s3/fe-icons/1.69.0/ic_s_star_filled.js` | `ic_s_star_filled.js` | 923 | product |
| `https://st.ozone.ru/s3/fe-icons/1.69.0/ic_s_star_filled_compact.js` | `ic_s_star_filled_compact.js` | 565 | cart, favorites, home, search |
| `https://st.ozone.ru/s3/frontend-ozon-ru-polyfills/1.1.0/polyfills.modern.js` | `polyfills.modern.js` | 34356 | cart, category, favorites, home, product, reviews, search |
| `https://st.ozone.ru/s3/ozon-tag-manager/1.1.33/sdk.js` | `sdk.js` | 10718 | cart, category, favorites, home, product, reviews, search |
| `https://st.ozone.ru/s3/shared-deps/%40bx-fe/common-atom-badge/3.9.0/index.js` | `bx-fe__common-atom-badge__3.9.0__index.js` | 6122 | cart, category, favorites, home, search |
| `https://st.ozone.ru/s3/shared-deps/%40bx-fe/common-atom-bullet-list/3.8.0/index.js` | `bx-fe__common-atom-bullet-list__3.8.0__index.js` | 1990 | product |
| `https://st.ozone.ru/s3/shared-deps/%40bx-fe/common-atom-button/3.11.0/index.js` | `bx-fe__common-atom-button__3.11.0__index.js` | 19980 | cart, category, favorites, home, product, reviews, search |
| `https://st.ozone.ru/s3/shared-deps/%40bx-fe/common-atom-cell/3.9.0/index.js` | `bx-fe__common-atom-cell__3.9.0__index.js` | 11005 | cart, category, favorites, home, search |
| `https://st.ozone.ru/s3/shared-deps/%40bx-fe/common-atom-circular-countdown/3.8.0/index.js` | `bx-fe__common-atom-circular-countdown__3.8.0__index.js` | 2412 | cart, category, favorites, home, product, reviews, search |
| `https://st.ozone.ru/s3/shared-deps/%40bx-fe/common-atom-ds-badge/3.10.2/index.js` | `bx-fe__common-atom-ds-badge__3.10.2__index.js` | 4152 | home, reviews |
| `https://st.ozone.ru/s3/shared-deps/%40bx-fe/common-atom-ds-badge/3.11.0/index.js` | `bx-fe__common-atom-ds-badge__3.11.0__index.js` | 4154 | cart, category, favorites, home, product, reviews, search |
| `https://st.ozone.ru/s3/shared-deps/%40bx-fe/common-atom-ds-button/3.14.2/index.js` | `bx-fe__common-atom-ds-button__3.14.2__index.js` | 16174 | cart, category, favorites, home, product, reviews, search |
| `https://st.ozone.ru/s3/shared-deps/%40bx-fe/common-atom-ds-button/3.15.0/index.js` | `bx-fe__common-atom-ds-button__3.15.0__index.js` | 16174 | cart, category, favorites, home, product, reviews, search |
| `https://st.ozone.ru/s3/shared-deps/%40bx-fe/common-atom-ds-cell/3.15.3/index.js` | `bx-fe__common-atom-ds-cell__3.15.3__index.js` | 11143 | home |
| `https://st.ozone.ru/s3/shared-deps/%40bx-fe/common-atom-ds-cell/3.16.0/index.js` | `bx-fe__common-atom-ds-cell__3.16.0__index.js` | 11811 | category, home |
| `https://st.ozone.ru/s3/shared-deps/%40bx-fe/common-atom-ds-cell/3.16.1/index.js` | `bx-fe__common-atom-ds-cell__3.16.1__index.js` | 11811 | cart, category, favorites, home, search |
| `https://st.ozone.ru/s3/shared-deps/%40bx-fe/common-atom-ds-count-picker/3.9.0/index.js` | `bx-fe__common-atom-ds-count-picker__3.9.0__index.js` | 3092 | reviews |
| `https://st.ozone.ru/s3/shared-deps/%40bx-fe/common-atom-ds-nav-tabs/3.8.2/index.js` | `bx-fe__common-atom-ds-nav-tabs__3.8.2__index.js` | 6511 | favorites |
| `https://st.ozone.ru/s3/shared-deps/%40bx-fe/common-atom-ds-notification-bar/3.12.0/index.js` | `bx-fe__common-atom-ds-notification-bar__3.12.0__index.js` | 4694 | cart, category, favorites, home, product, reviews, search |
| `https://st.ozone.ru/s3/shared-deps/%40bx-fe/common-atom-ds-price/3.10.0/index.js` | `bx-fe__common-atom-ds-price__3.10.0__index.js` | 2549 | cart, favorites, home, search |
| `https://st.ozone.ru/s3/shared-deps/%40bx-fe/common-atom-ds-tabs/3.12.2/index.js` | `bx-fe__common-atom-ds-tabs__3.12.2__index.js` | 8030 | favorites |
| `https://st.ozone.ru/s3/shared-deps/%40bx-fe/common-atom-icon/3.10.2/index.js` | `bx-fe__common-atom-icon__3.10.2__index.js` | 2406 | cart, category, favorites, home, product, reviews, search |
| `https://st.ozone.ru/s3/shared-deps/%40bx-fe/common-atom-icon/3.11.0/index.js` | `bx-fe__common-atom-icon__3.11.0__index.js` | 2406 | cart, category, favorites, home, product, reviews, search |
| `https://st.ozone.ru/s3/shared-deps/%40bx-fe/common-atom-image/3.9.0/index.js` | `bx-fe__common-atom-image__3.9.0__index.js` | 3564 | favorites, product, reviews |
| `https://st.ozone.ru/s3/shared-deps/%40bx-fe/common-atom-indicator/3.8.2/index.js` | `bx-fe__common-atom-indicator__3.8.2__index.js` | 3500 | cart, category, favorites, home, product, reviews, search |
| `https://st.ozone.ru/s3/shared-deps/%40bx-fe/common-atom-indicator/3.9.0/index.js` | `bx-fe__common-atom-indicator__3.9.0__index.js` | 3500 | cart, category, favorites, home, product, reviews, search |
| `https://st.ozone.ru/s3/shared-deps/%40bx-fe/common-atom-label-list/3.8.0/index.js` | `bx-fe__common-atom-label-list__3.8.0__index.js` | 2848 | cart, favorites, home, search |
| `https://st.ozone.ru/s3/shared-deps/%40bx-fe/common-atom-notification/3.8.0/index.js` | `bx-fe__common-atom-notification__3.8.0__index.js` | 4157 | cart, category, favorites, home, product, reviews, search |
| `https://st.ozone.ru/s3/shared-deps/%40bx-fe/common-atom-numbered-list/3.8.0/index.js` | `bx-fe__common-atom-numbered-list__3.8.0__index.js` | 1726 | product |
| `https://st.ozone.ru/s3/shared-deps/%40bx-fe/common-atom-rating-clickable/2.9.0/index.js` | `bx-fe__common-atom-rating-clickable__2.9.0__index.js` | 2015 | cart, favorites, home, search |
| `https://st.ozone.ru/s3/shared-deps/%40bx-fe/common-atom-text/3.10.0/index.js` | `bx-fe__common-atom-text__3.10.0__index.js` | 4687 | cart, category, favorites, home, product, reviews, search |
| `https://st.ozone.ru/s3/shared-deps/%40bx-fe/common-atom-text/3.9.2/index.js` | `bx-fe__common-atom-text__3.9.2__index.js` | 4619 | cart, category, favorites, home, product, reviews, search |
| `https://st.ozone.ru/s3/shared-deps/%40bx-fe/common-component-accessibility-button/1.5.19/index.js` | `bx-fe__common-component-accessibility-button__1.5.19__index.js` | 1909 | cart, category, favorites, home, product, reviews, search |
| `https://st.ozone.ru/s3/shared-deps/%40bx-fe/common-component-action-sheet/3.9.1/index.js` | `bx-fe__common-component-action-sheet__3.9.1__index.js` | 5338 | cart, category, favorites, home, search |
| `https://st.ozone.ru/s3/shared-deps/%40bx-fe/common-component-adult-text/3.8.0/index.js` | `bx-fe__common-component-adult-text__3.8.0__index.js` | 1544 | cart, favorites, home, search |
| `https://st.ozone.ru/s3/shared-deps/%40bx-fe/common-component-adv-badge-v2/3.8.3/index.js` | `bx-fe__common-component-adv-badge-v2__3.8.3__index.js` | 2871 | home |
| `https://st.ozone.ru/s3/shared-deps/%40bx-fe/common-component-adv-badge-v2/3.9.0/index.js` | `bx-fe__common-component-adv-badge-v2__3.9.0__index.js` | 2869 | category, home |
| `https://st.ozone.ru/s3/shared-deps/%40bx-fe/common-component-adv-badge/3.8.2/index.js` | `bx-fe__common-component-adv-badge__3.8.2__index.js` | 15865 | home |
| `https://st.ozone.ru/s3/shared-deps/%40bx-fe/common-component-adv-badge/3.9.0/index.js` | `bx-fe__common-component-adv-badge__3.9.0__index.js` | 15865 | category, home |
| `https://st.ozone.ru/s3/shared-deps/%40bx-fe/common-component-adv-info/3.7.3/index.js` | `bx-fe__common-component-adv-info__3.7.3__index.js` | 12811 | home |
| `https://st.ozone.ru/s3/shared-deps/%40bx-fe/common-component-adv-info/3.8.0/index.js` | `bx-fe__common-component-adv-info__3.8.0__index.js` | 12815 | category, home |
| `https://st.ozone.ru/s3/shared-deps/%40bx-fe/common-component-blocking-loader/1.4.9/index.js` | `bx-fe__common-component-blocking-loader__1.4.9__index.js` | 1955 | cart, category, favorites, home, product, reviews, search |
| `https://st.ozone.ru/s3/shared-deps/%40bx-fe/common-component-composer-link/1.5.10/index.js` | `bx-fe__common-component-composer-link__1.5.10__index.js` | 1878 | cart, category, favorites, home, product, reviews, search |
| `https://st.ozone.ru/s3/shared-deps/%40bx-fe/common-component-composer-link/1.5.9/index.js` | `bx-fe__common-component-composer-link__1.5.9__index.js` | 1876 | cart, category, favorites, home, product, reviews, search |
| `https://st.ozone.ru/s3/shared-deps/%40bx-fe/common-component-favorite-product-button-v2/1.12.0/index.js` | `bx-fe__common-component-favorite-product-button-v2__1.12.0__index.js` | 7405 | cart, favorites, home, search |
| `https://st.ozone.ru/s3/shared-deps/%40bx-fe/common-component-favorite-reserve-button/1.2.20/index.js` | `bx-fe__common-component-favorite-reserve-button__1.2.20__index.js` | 1809 | cart, favorites, home, search |
| `https://st.ozone.ru/s3/shared-deps/%40bx-fe/common-component-favorite-toggle-wishlist-button/1.2.22/index.js` | `bx-fe__common-component-favorite-toggle-wishlist-button__1.2.22__index.js` | 2384 | cart, favorites, home, search |
| `https://st.ozone.ru/s3/shared-deps/%40bx-fe/common-component-header/3.9.0/index.js` | `bx-fe__common-component-header__3.9.0__index.js` | 5030 | cart, category, favorites, home, search |
| `https://st.ozone.ru/s3/shared-deps/%40bx-fe/common-component-icon-header/1.2.15/index.js` | `bx-fe__common-component-icon-header__1.2.15__index.js` | 2472 | cart, category, favorites, home, product, reviews, search |
| `https://st.ozone.ru/s3/shared-deps/%40bx-fe/common-component-icon-header/1.2.19/index.js` | `bx-fe__common-component-icon-header__1.2.19__index.js` | 2475 | cart, category, favorites, home, product, reviews, search |
| `https://st.ozone.ru/s3/shared-deps/%40bx-fe/common-component-label-list-v2/1.9.0/index.js` | `bx-fe__common-component-label-list-v2__1.9.0__index.js` | 2870 | cart, favorites, home, search |
| `https://st.ozone.ru/s3/shared-deps/%40bx-fe/common-component-links-stub/1.5.10/index.js` | `bx-fe__common-component-links-stub__1.5.10__index.js` | 2106 | cart, category, favorites, home, product, reviews, search |
| `https://st.ozone.ru/s3/shared-deps/%40bx-fe/common-component-links-stub/1.5.9/index.js` | `bx-fe__common-component-links-stub__1.5.9__index.js` | 2100 | cart, category, favorites, home, product, reviews, search |
| `https://st.ozone.ru/s3/shared-deps/%40bx-fe/common-component-mob-hint-modal/3.10.0/index.js` | `bx-fe__common-component-mob-hint-modal__3.10.0__index.js` | 2493 | reviews |
| `https://st.ozone.ru/s3/shared-deps/%40bx-fe/common-component-preloader-five-dots/1.4.9/index.js` | `bx-fe__common-component-preloader-five-dots__1.4.9__index.js` | 1734 | cart, category, favorites, home, product, reviews, search |
| `https://st.ozone.ru/s3/shared-deps/%40bx-fe/common-component-results-header/1.11.0/index.js` | `bx-fe__common-component-results-header__1.11.0__index.js` | 2980 | category |
| `https://st.ozone.ru/s3/shared-deps/%40bx-fe/common-component-rich-string/3.9.0/index.js` | `bx-fe__common-component-rich-string__3.9.0__index.js` | 5523 | product, reviews |
| `https://st.ozone.ru/s3/shared-deps/%40bx-fe/common-feature-atom-actions/1.4.10/index.js` | `bx-fe__common-feature-atom-actions__1.4.10__index.js` | 4779 | cart, category, favorites, home, product, reviews, search |
| `https://st.ozone.ru/s3/shared-deps/%40bx-fe/common-feature-atom-actions/1.4.8/index.js` | `bx-fe__common-feature-atom-actions__1.4.8__index.js` | 4777 | cart, category, favorites, home, product, reviews, search |
| `https://st.ozone.ru/s3/shared-deps/%40bx-fe/common-feature-cart/1.7.8/index.js` | `bx-fe__common-feature-cart__1.7.8__index.js` | 32417 | product |
| `https://st.ozone.ru/s3/shared-deps/%40bx-fe/common-feature-favorites/1.4.10/index.js` | `bx-fe__common-feature-favorites__1.4.10__index.js` | 16374 | cart, category, favorites, home, product, reviews, search |
| `https://st.ozone.ru/s3/shared-deps/%40bx-fe/common-feature-favorites/1.4.12/index.js` | `bx-fe__common-feature-favorites__1.4.12__index.js` | 16374 | cart, category, favorites, home, product, reviews, search |
| `https://st.ozone.ru/s3/shared-deps/%40bx-fe/common-feature-navi/1.2.9/index.js` | `bx-fe__common-feature-navi__1.2.9__index.js` | 1061 | cart, favorites, home, search |
| `https://st.ozone.ru/s3/shared-deps/%40bx-fe/common-feature-notifications/1.5.8/index.js` | `bx-fe__common-feature-notifications__1.5.8__index.js` | 2291 | cart, category, favorites, home, product, reviews, search |
| `https://st.ozone.ru/s3/shared-deps/%40bx-fe/common-feature-notifications/1.6.0/index.js` | `bx-fe__common-feature-notifications__1.6.0__index.js` | 2291 | cart, category, favorites, home, product, reviews, search |
| `https://st.ozone.ru/s3/shared-deps/%40bx-fe/common-feature-subscriptions/1.4.12/index.js` | `bx-fe__common-feature-subscriptions__1.4.12__index.js` | 7545 | reviews |
| `https://st.ozone.ru/s3/shared-deps/%40bx-fe/ui-kit-button/5.4.3/index.js` | `bx-fe__ui-kit-button__5.4.3__index.js` | 9725 | category, home, reviews, search |
| `https://st.ozone.ru/s3/shared-deps/%40bx-fe/ui-kit-button/5.4.5/index.js` | `bx-fe__ui-kit-button__5.4.5__index.js` | 9725 | cart, category, favorites, home, product, reviews, search |
| `https://st.ozone.ru/s3/shared-deps/%40bx-fe/ui-kit-carousel/5.4.6/index.js` | `bx-fe__ui-kit-carousel__5.4.6__index.js` | 17405 | home, reviews |
| `https://st.ozone.ru/s3/shared-deps/%40bx-fe/ui-kit-carousel/5.4.9/index.js` | `bx-fe__ui-kit-carousel__5.4.9__index.js` | 17405 | category, product, search |
| `https://st.ozone.ru/s3/shared-deps/%40bx-fe/ui-kit-checkbox/5.4.3/index.js` | `bx-fe__ui-kit-checkbox__5.4.3__index.js` | 3949 | cart, category, favorites, home, product, reviews, search |
| `https://st.ozone.ru/s3/shared-deps/%40bx-fe/ui-kit-core/5.4.0/index.js` | `bx-fe__ui-kit-core__5.4.0__index.js` | 6788 | cart, category, favorites, home, product, reviews, search |
| `https://st.ozone.ru/s3/shared-deps/%40bx-fe/ui-kit-core/5.4.2/index.js` | `bx-fe__ui-kit-core__5.4.2__index.js` | 6913 | cart, category, favorites, home, product, reviews, search |
| `https://st.ozone.ru/s3/shared-deps/%40bx-fe/ui-kit-css-vars/6.4.0/index.js` | `bx-fe__ui-kit-css-vars__6.4.0__index.js` | 8489 | cart, category, favorites, home, product, reviews, search |
| `https://st.ozone.ru/s3/shared-deps/%40bx-fe/ui-kit-css-vars/7.0.2/index.js` | `bx-fe__ui-kit-css-vars__7.0.2__index.js` | 8489 | cart, category, favorites, home, product, reviews, search |
| `https://st.ozone.ru/s3/shared-deps/%40bx-fe/ui-kit-css-vars/7.2.0/index.js` | `bx-fe__ui-kit-css-vars__7.2.0__index.js` | 8489 | cart, category, favorites, home, product, reviews, search |
| `https://st.ozone.ru/s3/shared-deps/%40bx-fe/ui-kit-ds-badge/5.7.2/index.js` | `bx-fe__ui-kit-ds-badge__5.7.2__index.js` | 8095 | home |
| `https://st.ozone.ru/s3/shared-deps/%40bx-fe/ui-kit-ds-badge/5.7.7/index.js` | `bx-fe__ui-kit-ds-badge__5.7.7__index.js` | 7891 | cart, category, favorites, home, product, reviews, search |
| `https://st.ozone.ru/s3/shared-deps/%40bx-fe/ui-kit-ds-badge/5.7.9/index.js` | `bx-fe__ui-kit-ds-badge__5.7.9__index.js` | 7891 | cart, category, favorites, home, product, reviews, search |
| `https://st.ozone.ru/s3/shared-deps/%40bx-fe/ui-kit-ds-button/5.9.5/index.js` | `bx-fe__ui-kit-ds-button__5.9.5__index.js` | 7751 | cart, category, favorites, home, product, reviews, search |
| `https://st.ozone.ru/s3/shared-deps/%40bx-fe/ui-kit-ds-button/5.9.7/index.js` | `bx-fe__ui-kit-ds-button__5.9.7__index.js` | 7751 | cart, category, favorites, home, product, reviews, search |
| `https://st.ozone.ru/s3/shared-deps/%40bx-fe/ui-kit-ds-cell/5.5.9/index.js` | `bx-fe__ui-kit-ds-cell__5.5.9__index.js` | 15882 | cart, category, favorites, home, product, reviews, search |
| `https://st.ozone.ru/s3/shared-deps/%40bx-fe/ui-kit-ds-cell/5.6.0/index.js` | `bx-fe__ui-kit-ds-cell__5.6.0__index.js` | 15909 | category, home |
| `https://st.ozone.ru/s3/shared-deps/%40bx-fe/ui-kit-ds-cell/5.6.1/index.js` | `bx-fe__ui-kit-ds-cell__5.6.1__index.js` | 16091 | cart, category, favorites, home, product, search |
| `https://st.ozone.ru/s3/shared-deps/%40bx-fe/ui-kit-ds-checkbox/5.8.5/index.js` | `bx-fe__ui-kit-ds-checkbox__5.8.5__index.js` | 7631 | cart, category, favorites, home, product, reviews, search |
| `https://st.ozone.ru/s3/shared-deps/%40bx-fe/ui-kit-ds-checkbox/5.8.7/index.js` | `bx-fe__ui-kit-ds-checkbox__5.8.7__index.js` | 7632 | cart, category, favorites, home, product, search |
| `https://st.ozone.ru/s3/shared-deps/%40bx-fe/ui-kit-ds-count-picker/5.6.9/index.js` | `bx-fe__ui-kit-ds-count-picker__5.6.9__index.js` | 9099 | reviews |
| `https://st.ozone.ru/s3/shared-deps/%40bx-fe/ui-kit-ds-dialog/5.6.6/index.js` | `bx-fe__ui-kit-ds-dialog__5.6.6__index.js` | 11529 | cart, category, favorites, home, product, reviews, search |
| `https://st.ozone.ru/s3/shared-deps/%40bx-fe/ui-kit-ds-dialog/5.6.9/index.js` | `bx-fe__ui-kit-ds-dialog__5.6.9__index.js` | 11568 | cart, category, favorites, home, product, reviews, search |
| `https://st.ozone.ru/s3/shared-deps/%40bx-fe/ui-kit-ds-dropdown-content/5.5.6/index.js` | `bx-fe__ui-kit-ds-dropdown-content__5.5.6__index.js` | 4596 | cart, category, favorites, home, product, reviews, search |
| `https://st.ozone.ru/s3/shared-deps/%40bx-fe/ui-kit-ds-dropdown-wrapper/5.6.2/index.js` | `bx-fe__ui-kit-ds-dropdown-wrapper__5.6.2__index.js` | 9089 | cart, category, favorites, home, product, reviews, search |
| `https://st.ozone.ru/s3/shared-deps/%40bx-fe/ui-kit-ds-icon-button/5.12.6/index.js` | `bx-fe__ui-kit-ds-icon-button__5.12.6__index.js` | 5456 | cart, category, favorites, home, product, reviews, search |
| `https://st.ozone.ru/s3/shared-deps/%40bx-fe/ui-kit-ds-icon-button/5.12.9/index.js` | `bx-fe__ui-kit-ds-icon-button__5.12.9__index.js` | 5456 | cart, category, favorites, home, product, reviews, search |
| `https://st.ozone.ru/s3/shared-deps/%40bx-fe/ui-kit-ds-icon-scale/5.4.0/index.js` | `bx-fe__ui-kit-ds-icon-scale__5.4.0__index.js` | 2768 | cart, category, favorites, home, product, reviews, search |
| `https://st.ozone.ru/s3/shared-deps/%40bx-fe/ui-kit-ds-icon-scale/5.4.2/index.js` | `bx-fe__ui-kit-ds-icon-scale__5.4.2__index.js` | 2619 | cart, category, favorites, home, product, reviews, search |
| `https://st.ozone.ru/s3/shared-deps/%40bx-fe/ui-kit-ds-icon/5.9.0/index.js` | `bx-fe__ui-kit-ds-icon__5.9.0__index.js` | 5651 | cart, category, favorites, home, product, reviews, search |
| `https://st.ozone.ru/s3/shared-deps/%40bx-fe/ui-kit-ds-icon/5.9.4/index.js` | `bx-fe__ui-kit-ds-icon__5.9.4__index.js` | 5372 | cart, category, favorites, home, product, reviews, search |
| `https://st.ozone.ru/s3/shared-deps/%40bx-fe/ui-kit-ds-icon/5.9.6/index.js` | `bx-fe__ui-kit-ds-icon__5.9.6__index.js` | 5372 | cart, category, favorites, home, product, reviews, search |
| `https://st.ozone.ru/s3/shared-deps/%40bx-fe/ui-kit-ds-image-ratio/5.4.5/index.js` | `bx-fe__ui-kit-ds-image-ratio__5.4.5__index.js` | 5868 | cart, category, favorites, home, product, reviews, search |
| `https://st.ozone.ru/s3/shared-deps/%40bx-fe/ui-kit-ds-image-ratio/5.4.7/index.js` | `bx-fe__ui-kit-ds-image-ratio__5.4.7__index.js` | 5868 | cart, category, favorites, home, product, reviews, search |
| `https://st.ozone.ru/s3/shared-deps/%40bx-fe/ui-kit-ds-image/5.4.3/index.js` | `bx-fe__ui-kit-ds-image__5.4.3__index.js` | 7032 | cart, category, favorites, home, product, reviews, search |
| `https://st.ozone.ru/s3/shared-deps/%40bx-fe/ui-kit-ds-indicator/5.4.0/index.js` | `bx-fe__ui-kit-ds-indicator__5.4.0__index.js` | 5451 | cart, category, favorites, home, product, reviews, search |
| `https://st.ozone.ru/s3/shared-deps/%40bx-fe/ui-kit-ds-indicator/5.4.4/index.js` | `bx-fe__ui-kit-ds-indicator__5.4.4__index.js` | 4997 | cart, category, favorites, home, product, reviews, search |
| `https://st.ozone.ru/s3/shared-deps/%40bx-fe/ui-kit-ds-indicator/5.4.6/index.js` | `bx-fe__ui-kit-ds-indicator__5.4.6__index.js` | 4997 | cart, category, favorites, home, product, reviews, search |
| `https://st.ozone.ru/s3/shared-deps/%40bx-fe/ui-kit-ds-input-base/5.7.4/index.js` | `bx-fe__ui-kit-ds-input-base__5.7.4__index.js` | 23179 | category, search |
| `https://st.ozone.ru/s3/shared-deps/%40bx-fe/ui-kit-ds-input/5.6.4/index.js` | `bx-fe__ui-kit-ds-input__5.6.4__index.js` | 16764 | cart, category, favorites, home, product, reviews, search |
| `https://st.ozone.ru/s3/shared-deps/%40bx-fe/ui-kit-ds-input/5.6.6/index.js` | `bx-fe__ui-kit-ds-input__5.6.6__index.js` | 16764 | category, search |
| `https://st.ozone.ru/s3/shared-deps/%40bx-fe/ui-kit-ds-link-button/5.4.4/index.js` | `bx-fe__ui-kit-ds-link-button__5.4.4__index.js` | 3840 | cart, category, favorites, home, product, reviews, search |
| `https://st.ozone.ru/s3/shared-deps/%40bx-fe/ui-kit-ds-link-button/5.4.6/index.js` | `bx-fe__ui-kit-ds-link-button__5.4.6__index.js` | 3840 | cart, category, favorites, home, product, reviews, search |
| `https://st.ozone.ru/s3/shared-deps/%40bx-fe/ui-kit-ds-loader/5.5.3/index.js` | `bx-fe__ui-kit-ds-loader__5.5.3__index.js` | 2054 | cart, category, favorites, home, product, reviews, search |
| `https://st.ozone.ru/s3/shared-deps/%40bx-fe/ui-kit-ds-loader/5.5.5/index.js` | `bx-fe__ui-kit-ds-loader__5.5.5__index.js` | 2056 | cart, category, favorites, home, product, reviews, search |
| `https://st.ozone.ru/s3/shared-deps/%40bx-fe/ui-kit-ds-nav-tabs/5.4.7/index.js` | `bx-fe__ui-kit-ds-nav-tabs__5.4.7__index.js` | 4605 | favorites |
| `https://st.ozone.ru/s3/shared-deps/%40bx-fe/ui-kit-ds-notification-bar/5.6.0/index.js` | `bx-fe__ui-kit-ds-notification-bar__5.6.0__index.js` | 8395 | cart, category, favorites, home, product, reviews, search |
| `https://st.ozone.ru/s3/shared-deps/%40bx-fe/ui-kit-ds-price/5.6.0/index.js` | `bx-fe__ui-kit-ds-price__5.6.0__index.js` | 7327 | cart, category, favorites, home, product, reviews, search |
| `https://st.ozone.ru/s3/shared-deps/%40bx-fe/ui-kit-ds-price/5.6.2/index.js` | `bx-fe__ui-kit-ds-price__5.6.2__index.js` | 7513 | cart, category, favorites, home, product, search |
| `https://st.ozone.ru/s3/shared-deps/%40bx-fe/ui-kit-ds-radio/5.8.5/index.js` | `bx-fe__ui-kit-ds-radio__5.8.5__index.js` | 5605 | cart, category, favorites, home, product, reviews, search |
| `https://st.ozone.ru/s3/shared-deps/%40bx-fe/ui-kit-ds-radio/5.8.7/index.js` | `bx-fe__ui-kit-ds-radio__5.8.7__index.js` | 5605 | cart, category, favorites, home, product, search |
| `https://st.ozone.ru/s3/shared-deps/%40bx-fe/ui-kit-ds-rating-clickable/5.5.5/index.js` | `bx-fe__ui-kit-ds-rating-clickable__5.5.5__index.js` | 4331 | cart, favorites, home, search |
| `https://st.ozone.ru/s3/shared-deps/%40bx-fe/ui-kit-ds-rating-showing/5.5.3/index.js` | `bx-fe__ui-kit-ds-rating-showing__5.5.3__index.js` | 4495 | reviews |
| `https://st.ozone.ru/s3/shared-deps/%40bx-fe/ui-kit-ds-select/5.6.7/index.js` | `bx-fe__ui-kit-ds-select__5.6.7__index.js` | 12665 | category, search |
| `https://st.ozone.ru/s3/shared-deps/%40bx-fe/ui-kit-ds-tabs/5.7.7/index.js` | `bx-fe__ui-kit-ds-tabs__5.7.7__index.js` | 7764 | favorites |
| `https://st.ozone.ru/s3/shared-deps/%40bx-fe/ui-kit-ds-tag-button/5.8.3/index.js` | `bx-fe__ui-kit-ds-tag-button__5.8.3__index.js` | 6364 | cart, category, favorites, home, product, reviews, search |
| `https://st.ozone.ru/s3/shared-deps/%40bx-fe/ui-kit-ds-tag-button/5.8.5/index.js` | `bx-fe__ui-kit-ds-tag-button__5.8.5__index.js` | 6368 | cart, category, favorites, home, product, reviews, search |
| `https://st.ozone.ru/s3/shared-deps/%40bx-fe/ui-kit-ds-text-view/5.4.0/index.js` | `bx-fe__ui-kit-ds-text-view__5.4.0__index.js` | 11663 | cart, category, favorites, home, product, reviews, search |
| `https://st.ozone.ru/s3/shared-deps/%40bx-fe/ui-kit-ds-text-view/5.4.2/index.js` | `bx-fe__ui-kit-ds-text-view__5.4.2__index.js` | 11332 | cart, category, favorites, home, product, reviews, search |
| `https://st.ozone.ru/s3/shared-deps/%40bx-fe/ui-kit-ds-toggle/5.4.5/index.js` | `bx-fe__ui-kit-ds-toggle__5.4.5__index.js` | 3521 | cart, category, favorites, home, product, reviews, search |
| `https://st.ozone.ru/s3/shared-deps/%40bx-fe/ui-kit-ds-tooltip/5.7.10/index.js` | `bx-fe__ui-kit-ds-tooltip__5.7.10__index.js` | 18345 | cart, category, favorites, home, product, reviews, search |
| `https://st.ozone.ru/s3/shared-deps/%40bx-fe/ui-kit-ds-tooltip/5.7.10/popper.js` | `popper.js` | 18901 | cart, category, favorites, home, product, reviews, search |
| `https://st.ozone.ru/s3/shared-deps/%40bx-fe/ui-kit-ds-tooltip/5.7.7/index.js` | `bx-fe__ui-kit-ds-tooltip__5.7.7__index.js` | 18319 | cart, category, favorites, home, product, reviews, search |
| `https://st.ozone.ru/s3/shared-deps/%40bx-fe/ui-kit-field/5.4.2/index.js` | `bx-fe__ui-kit-field__5.4.2__index.js` | 1868 | cart, category, favorites, home, product, reviews, search |
| `https://st.ozone.ru/s3/shared-deps/%40bx-fe/ui-kit-image/5.4.3/index.js` | `bx-fe__ui-kit-image__5.4.3__index.js` | 6253 | cart, category, favorites, home, product, reviews, search |
| `https://st.ozone.ru/s3/shared-deps/%40bx-fe/ui-kit-input/5.4.4/index.js` | `bx-fe__ui-kit-input__5.4.4__index.js` | 6602 | reviews |
| `https://st.ozone.ru/s3/shared-deps/%40bx-fe/ui-kit-input/5.4.6/index.js` | `bx-fe__ui-kit-input__5.4.6__index.js` | 6602 | cart, category, favorites, home, product, reviews, search |
| `https://st.ozone.ru/s3/shared-deps/%40bx-fe/ui-kit-loader/5.4.2/index.js` | `bx-fe__ui-kit-loader__5.4.2__index.js` | 7744 | cart, category, favorites, home, product, reviews, search |
| `https://st.ozone.ru/s3/shared-deps/%40bx-fe/ui-kit-notification/5.4.5/index.js` | `bx-fe__ui-kit-notification__5.4.5__index.js` | 4299 | reviews |
| `https://st.ozone.ru/s3/shared-deps/%40bx-fe/ui-kit-notification/5.4.7/index.js` | `bx-fe__ui-kit-notification__5.4.7__index.js` | 4299 | cart, category, favorites, home, product, reviews, search |
| `https://st.ozone.ru/s3/shared-deps/%40bx-fe/ui-kit-popover/5.4.5/index.js` | `bx-fe__ui-kit-popover__5.4.5__index.js` | 13981 | home, reviews |
| `https://st.ozone.ru/s3/shared-deps/%40bx-fe/ui-kit-popover/5.4.7/index.js` | `bx-fe__ui-kit-popover__5.4.7__index.js` | 13981 | cart, category, favorites, home, product, reviews, search |
| `https://st.ozone.ru/s3/shared-deps/%40bx-fe/ui-kit-portal/5.4.3/index.js` | `bx-fe__ui-kit-portal__5.4.3__index.js` | 3130 | cart, category, favorites, home, product, reviews, search |
| `https://st.ozone.ru/s3/shared-deps/%40bx-fe/ui-kit-radio-group/5.4.4/index.js` | `bx-fe__ui-kit-radio-group__5.4.4__index.js` | 3159 | reviews |
| `https://st.ozone.ru/s3/shared-deps/%40bx-fe/ui-kit-radio/5.4.4/index.js` | `bx-fe__ui-kit-radio__5.4.4__index.js` | 3772 | cart, category, favorites, home, reviews, search |
| `https://st.ozone.ru/s3/shared-deps/%40bx-fe/ui-kit-range/5.4.6/index.js` | `bx-fe__ui-kit-range__5.4.6__index.js` | 15887 | category, search |
| `https://st.ozone.ru/s3/shared-deps/%40bx-fe/ui-kit-tag/5.4.3/index.js` | `bx-fe__ui-kit-tag__5.4.3__index.js` | 4399 | category, search |
| `https://st.ozone.ru/s3/shared-deps/%40bx-fe/ui-kit-text-field-wrapper/5.4.3/index.js` | `bx-fe__ui-kit-text-field-wrapper__5.4.3__index.js` | 4689 | reviews |
| `https://st.ozone.ru/s3/shared-deps/%40bx-fe/ui-kit-text-field-wrapper/5.4.5/index.js` | `bx-fe__ui-kit-text-field-wrapper__5.4.5__index.js` | 4689 | cart, category, favorites, home, product, reviews, search |
| `https://st.ozone.ru/s3/shared-deps/%40bx-fe/ui-kit-textarea/5.4.3/index.js` | `bx-fe__ui-kit-textarea__5.4.3__index.js` | 4030 | reviews |
| `https://st.ozone.ru/s3/shared-deps/%40bx-fe/ui-kit-transition/5.4.2/index.js` | `bx-fe__ui-kit-transition__5.4.2__index.js` | 2923 | cart, category, favorites, home, product, reviews, search |
| `https://st.ozone.ru/s3/shared-deps/%40bx-fe/ui-kit-typography-helper/5.4.0/index.js` | `bx-fe__ui-kit-typography-helper__5.4.0__index.js` | 1734 | cart, category, favorites, home, product, reviews, search |
| `https://st.ozone.ru/s3/shared-deps/%40bx-fe/ui-kit-typography-helper/5.4.2/index.js` | `bx-fe__ui-kit-typography-helper__5.4.2__index.js` | 1734 | cart, category, favorites, home, product, reviews, search |
| `https://st.ozone.ru/s3/shared-deps/%40ozon-shared-deps/clipboard/2.0.12/index.js` | `ozon-shared-deps__clipboard__2.0.12__index.js` | 9299 | product, reviews |
| `https://st.ozone.ru/s3/shared-deps/%40ozon-shared-deps/dayjs/1.8.34/index.js` | `ozon-shared-deps__dayjs__1.8.34__index.js` | 6687 | reviews |
| `https://st.ozone.ru/s3/shared-deps/%40ozon-shared-deps/portal-vue/2.1.10/index.js` | `ozon-shared-deps__portal-vue__2.1.10__index.js` | 8403 | cart, category, favorites, home, product, reviews, search |
| `https://st.ozone.ru/s3/shared-deps/%40ozon-shared-deps/qs/6.5.4/index.js` | `ozon-shared-deps__qs__6.5.4__index.js` | 7706 | cart, category, favorites, home, product, reviews, search |
