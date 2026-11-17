# Anti-detection

How `ozon-client` behaves on **one fixed IP**. This is a consistency and
pacing policy for a read-only client. It is not a guarantee that Ozon will
treat the traffic as a person.

The short version is in the README under [Anti-detection](README.md#anti-detection).

## What the probe actually showed

`audit/antibot_probe.md` (2026-10-16), six requests, egress `83.142.30.241`:

- Cold `curl_cffi` impersonating `chrome146`, full Chrome headers, **no cookies** → `403`, `ozon-antibot: 1`, JSON body with `incidentId`, `challengeURL`, `supportURL`, `timeoutSec`, `blockURL`.
- The same request plus the nine CDP cookies → `200`, same payload class as an in-page `fetch`.
- The browser and curl_cffi saw the same IP. Clearance traveled in the cookie jar, not in the TLS session.

That passing replay used the **live Chrome/153 Linux UA** on a **chrome146** TLS profile. It returned 200. A later check on the same IP showed why that mismatch has to stay:

**The jar is UA-bound. Profile consistency 403s.** Default profile hints — Chrome/146 UA, `sec-ch-ua` 146, platform `macOS`, TLS still `chrome146`, all nine cookie names in the jar — `search` returned **403**, incident `fab_20261016114137_01M528914ZZJMH5VATWFBH85YH`. One re-read of the jar, same hints, was also a challenge, and the session stopped. One follow-up GET, same jar, same TLS profile, minting Chrome/153 Linux UA and `sec-ch-ua`, returned **200** (158286 bytes, 32 `widgetStates`). UA and platform changed together; they were not split.

**On this target, UA/TLS-profile consistency is unachievable with curl_cffi 0.15.0.** The newest desktop profile is `chrome146`. The browser that minted the jar is Chrome/153. The clearance is a server-side cookie bound to the minting UA (and, untested, possibly to this IP), not a fingerprint you can satisfy by making the handshake and the UA tell one story. You have to send the minting browser's UA. That disagrees with the TLS profile. It is a known detectable inconsistency. It is not papered over. It is a hard ceiling until curl_cffi ships a `chrome153` profile, or the minting browser is downgraded to a version curl_cffi can impersonate. `ua_source="browser"` (default; `auto` is the same name) sends that UA. `ua_source="profile"` is opt-in for a Chrome whose major matches the profile. A 403 with `ozon-antibot: 1` while profile hints are in use is retried once with the live UA, then cool-down. Not twice. Rechecked after that flip: cookie-jar `search` and `product` on the default returned 200 (8 tiles; price `5 000,40 BYN`, 29 characteristics, reviews 47). Three GETs, no retry.

Cookie **values** are never printed, logged, or written by this client. The names are listed in the README. `document.cookie` is the wrong handoff (`abt_data` and most `__Secure-*` cookies are HttpOnly; `abt_data` is partitioned).

## Layer consistency

Bot checks stack. Failing one layer badly is enough. Sending a coherent stack is the whole job.

| Layer | What this client does | Consistent with |
|---|---|---|
| IP | Whatever the host already uses. No proxy, no rotation. | The jar was minted on this IP. Moving IP is untested and, per the usual clearance rules, likely voids the jar. |
| TLS / JA3 | `curl_cffi` impersonates the newest **desktop** Chrome profile the installed library ships. curl_cffi 0.15.0 → `chrome146`. Android profiles are skipped. The name is resolved at runtime (`newest_chrome_impersonate`), not pinned. | The profile's own handshake. |
| UA + `sec-ch-ua` + `sec-ch-ua-platform` | Default `ua_source="browser"` (`auto` is the same). Copied from the live page that minted the jar, including when that Chrome is newer than the TLS profile. On this host: Chrome/153, Linux. | The cookie jar. **Not** the TLS profile. The mismatch is required and still detectable. |
| `ua_source="profile"` | Opt-in. The impersonation profile's own hints (curl_cffi 0.15.0: Chrome/146, `sec-ch-ua` 146, platform `macOS`). Use it only when the minting Chrome's major matches the profile. A 403 `ozon-antibot: 1` on these hints retries once with the live UA, then stops. | The TLS profile, and on this host that choice 403s. |
| Header order / HTTP/2 | curl_cffi's impersonation stack, HTTP/2. Callers do not get to override UA or `sec-ch-ua*`. | The profile. |
| `sec-fetch-*` | Overridden to the fetch() shape the probe captured: `dest=empty`, `mode=cors`, `site=same-origin`. | An XHR/fetch from the site, not a top-level navigation. |
| JS challenge | Not executed on the cookie-jar path. The browser oracle is a real page and runs whatever the page runs. | Browser path only. |
| Cookies | The nine names, from CDP `Network.getAllCookies`, filtered to this host. Partitioned `abt_data` must be first-party. | The browser that minted them, same IP. |
| App headers | `x-o3-app-name`, `x-o3-app-version`, `x-o3-manifest-version` unchanged. `x-o3-parent-requestid` and `x-page-view-id` rotate **per document**, not per HTTP call. `x-page-previous` is the previous page type (`main.js` passes `previousPageType`), empty on the first view. | One page-view story. |
| Referer | Derived. Not the constant `https://ozon.by/?__rr=1` on every call. | The documents this process has fetched. |
| Behavior | Low rate, no default concurrency, jitter, warmup entry, cool-down. | A single slow reader. There is still no mouse, scroll, or focus signal. |

`OzonClient()` stays on the browser oracle, and that should remain the default. It is the only path with no split story: the TLS stack, the UA, the cookies, and the JS are the same Chrome. Cookie-jar is worth keeping, but only as an opt-in. After one mint it does not need the page for each call, which is why it exists. On curl_cffi 0.15.0 it cannot also be consistent: the handshake is chrome146 and the UA has to be the minting browser's. Use it when that speed is worth the known mismatch. Do not make it the default.

## What is randomized

- **Gap between requests.** After the token bucket allows a take, sleep `uniform(0.35, 1.15)` seconds. Disabled when `rate=0` (cookie mint, CLI commands that pass `--rate 0`).
- **Page-view ids.** `uuid4` for `x-page-view-id`, `uuid4().hex` for `x-o3-parent-requestid`. New pair when the document key changes. Layout params (`layout_page_index`, `layout_container`, `start_page_id`, `paginator_token`, `__rr`) do **not** change the key, so PDP screen 1 and screen 2 share a view.
- **Backoff before the one challenge retry.** `2 * 2^(n-1)` seconds, ±25%, capped at 30s.

Not randomized: which TLS profile (always the newest desktop one), the UA (always the minting browser, unless `ua_source="profile"` was asked for), accept-language (`ru-RU`), the cookie set, app version, manifest. Rotating those per request would look less like one browser, not more.

## Single-IP, low-and-slow

The 2026-10-15 ladder (40 concurrent → all 200, ~4 rps sustained) is **not** a budget. On one IP, concurrency is the loudest signal we can still choose.

- Library default: `TokenBucket(rate=0.5, burst=1.0)` via `OzonClient(rate=0.5, burst=1.0)`.
- Burst 1 means the next request waits for a refill. Overlap requires `burst > 1` **and** real threads. That is the opt-in. Leave it off.
- `ozon --rate` still defaults to `2.0` in `cli.py` (not changed here). Burst defaults to 1, and jitter still runs. Prefer `--rate 0.5` for a long session.
- Do not point two processes at the same IP and the same jar.

## Entry and referer

A cold deep link is a bad first action. `warmup(url=None, search=None)`:

1. Navigates the real browser to `https://<host>/?__rr=1`.
2. If `search` is set, navigates to `/search/?text=...&from_global=true`.
3. If `url` is not home, navigates there last.
4. Re-reads the cookie jar (cookie-jar transport only).
5. Tells the signer and the referer story about that trail.

A home-only warmup is still one navigation.

Cookie-jar referer rules after that:

- First document, or any call before a document has succeeded: `https://ozon.by/?__rr=1` (the configured base).
- A new document: the previous document URL.
- A layout slice of the current document: that document's own URL (the page `fetch()` would be running on).
- Composer actions such as `summaryV2` (no `url=` document): the current document, or home if there is none.

So a session that calls `search`, then `category`, then `product`, then `reviews`, then `questions` refers from home, then the search URL, then the category URL, then the product URL. Screen 2 of the product refers from the product URL. Query values in that referer are percent-encoded.

Skipping `warmup()` does not invent a home **request**. The first referer still *says* home. That claim has no matching navigation. Call `warmup()` if you care.

## Challenges and cool-down

Recognized as a challenge:

- response header `ozon-antibot` other than empty or `0`
- JSON object with `incidentId` / `incident_id` / `challengeURL` (the probe shape), any status
- HTML, or any non-success, whose body matches an incident id (`incidentId`, `data-incident-id`, `fab_chlg_…`)

A normal 200 entrypoint envelope is not a challenge. Checked against saved `audit/raw/product*.json`.

Discipline:

- **Never** retry 403 or 429 in a loop.
- Cookie-jar: one retry. Re-read the jar from CDP, sleep the exponential backoff, send once more. `retries=0` does not cancel that single refresh.
- Second consecutive challenge, or a third challenge in the life of the guard: stop. `AntibotBlocked`. Further `request()` calls raise and **do not send**. Cool-down is 900 seconds; the guard also sets `stopped`, so building a new client is what actually resumes.
- Browser oracle: a challenge does not re-fetch. The first one stops the session. Re-fetching inside the page is hammering.
- `429`: `RateLimited`, cool-down at least 60 seconds (or `Retry-After` if it parses as a number). Not retried.
- `5xx` and transport errors still use the existing backoff and `retries`. They are not challenges.

Cookie values that show up inside an exception string are redacted (`cookiejar._LEAK`, and the same pattern in `http.redact_secrets`).

## Request counts

`POST /api/composer-api.bx/widget/json/v2/batch` would in theory refresh many widgets in one call. It was **not** implemented:

- this client is GET-only (the pre-existing `address_bar` POST is left alone and is not used to "save" GETs)
- the inventory marks that route `write: true`, `verified_live: false`, and says it is unconfirmed whether the POST only reads

So the extra calls that are real GETs stay real GETs.

| Operation | Before | After (cold) | Why the second call is still there |
|---|---|---|---|
| `search` | 1 | 1 | One listing document. |
| `category` | 1 | 1 | One listing document. |
| `product` | 2 | 2 | Screen 1: price, heading, gallery, short specs. Screen 2 (`paginator.nextPage`, `layout_container=pdpPage2column&layout_page_index=2`): `webDescription` and the full `webCharacteristics` table (29 rows on the reference SKU). Neither page contains the other's fields. `/product/<slug>/features/` is also a separate GET and was not substituted. |
| `reviews` | 1 (2 only on a 404 fallback) | same | One reviews document when the first path works. |
| `questions(sku)` | 2 | 2 | Bare SKU has no slug. The product document is fetched to find `/product/<slug>/questions/`, then that document is fetched. The questions list is not on the product screen. |
| `questions` after `product` in the same client, within 90s | 2 | **1 wire + 1 cache** | The slug-resolution GET is the same entrypoint URL `product()` already fetched. Served from memory. |
| `summary` | 1 | 1 | `GET summaryV2`. Not a document, so it keeps the current page-view ids. |

The cache holds status, body, and non-cookie headers in process RAM only. TTL 90s, 24 entries. Challenges and non-200s are not stored. It does not merge the two product screens; those URLs differ.

## What is still detectable

Blunt list. None of this is fixed by header polish.

- **One IP, no residential pool.** This host's egress in the probe was a Dutch address (`83.142.30.241`, `loc=NL`), not a BY/RU residential exit. IP reputation is the first layer and this client does not touch it.
- **No behavioral signal.** No mouse movement, scroll, click, focus, or dwell time. Jitter is a sleep, not a person.
- **No JS on the cookie-jar path.** Challenges that need the page to run are not solved here. The jar is reused until it isn't. There is no nodriver / browser challenge step in this transport.
- **UA and TLS cannot both be telling the truth.** chrome146's own hints (macOS / Chrome 146) with this jar returned 403. The minting Chrome/153 Linux UA with the same jar and the same TLS profile returned 200. Cookie-jar mode therefore sends Chrome/153 over a chrome146 handshake. That mismatch is visible to anyone who cross-checks JA3 against `sec-ch-ua`. It stays until curl_cffi has a chrome153 profile or this browser is downgraded. The in-page browser transport does not have this hole.
- **Navigation headers the profile injects.** `sec-fetch-user: ?1` and `upgrade-insecure-requests: 1` are navigation headers. The in-page `fetch` did not send them. curl_cffi's chrome146 profile adds them unless the caller replaces the whole default set. The probe's cookie replay returned 200 with them present, so they are not the on/off switch. They are still a mismatch with a pure `fetch()`.
- **Header order is the impersonation library's, not a captured Chrome fetch.** We set the names we care about. We do not reproduce Chrome's HTTP/2 frame order byte for byte.
- **Referer without warmup is a claim.** The header says home. No home request was made.
- **App headers are a copy of one build** (`release_15-9-2026_aeebf0af` and the manifest pinned in `auth.py`). When the site ships a new frontend, those constants go stale. They were not changed here.
- **Page type in `x-page-previous` is inferred from the path**, not read from the site's tracker. It will be wrong for odd URLs. Empty on the first view matches the probe's capture; later values were not re-captured on the wire.
- **The jar's real TTL is unknown.** Declared `Expires` is about a year for several names and session for `xcid`. That was not measured by replaying later.
- **Which of the nine cookies is enough is unknown.** No leave-one-out.
- **Another IP is unknown.** Same-IP only.
- **Plain `requests` / `httpx` plus the jar is unknown.**
- **The GET cache can serve a page for up to 90s after the jar has actually died**, if the death happens after a success and nothing else challenges. The next uncached URL still hits the network.
- **CDP is still required to mint**, and a headed Chrome on a debug port is itself a signal on the browser-oracle path (`Runtime.evaluate` of `fetch`).
- **Concurrency is only discouraged, not blocked.** A caller can pass `burst=8` or `--rate 2` and undo the default.
