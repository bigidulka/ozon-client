# Antibot probe — ozon.by entrypoint (2026-10-16)

Read-only diagnosis. The docstring in `src/ozon_client/http.py` was treated as unverified.
No source files under `src/ozon_client/` were modified. Cookie values were not written here.

Probe target (the client's own GET):

```
GET /api/entrypoint-api.bx/page/json/v2?url=%2Fproduct%2Fapple-smartfon-iphone-17-pro-esim-12-512-gb-esim-siniy-3094054833%2F
Host: ozon.by
```

Live browser: Chrome/153.0.8010.36, CDP `127.0.0.1:9222`, tab `https://ozon.by/?__rr=1`.
`curl_cffi` 0.15.0, impersonate profile `chrome146` (newest profile shipped; there is no `chrome153`).
User-Agent and `sec-ch-ua` were taken from the live page, not from the impersonation profile:

```
User-Agent: Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/153.0.0.0 Safari/537.36
sec-ch-ua: "Google Chrome";v="153", "Not_A Brand";v="8", "Chromium";v="153"
sec-ch-ua-mobile: ?0
sec-ch-ua-platform: "Linux"
accept-language: ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7
```

## 1. Request count: 6

| # | kind | host | result |
|---|---|---|---|
| 1 | D browser egress | `www.cloudflare.com/cdn-cgi/trace` | 200, ip captured |
| 2 | D curl_cffi egress | `www.cloudflare.com/cdn-cgi/trace` | 200, ip captured |
| 3 | A `BrowserOracle` fetch | `ozon.by` entrypoint | 200 |
| 4 | B curl_cffi, no cookies | `ozon.by` entrypoint | 403 |
| 5 | C curl_cffi, 9 cookies | `ozon.by` entrypoint | 200 |
| 6 | cold curl_cffi again, `allow_redirects=False`, to recover the 403 body the first script discarded | `ozon.by` entrypoint | **307**, not followed |

No nodriver attempt. No challenge solve. No POST.

## 2. Results

| variant | status | `ozon-antibot` | incident id | notes |
|---|---|---|---|---|
| A control, in-page `fetch` via `BrowserOracle` | 200 | absent | — | `application/json`, 155528 bytes, `widgetStates` count 80, `x-o3-page-type: pdp`, `server: nginx`. No warmup needed. |
| B curl_cffi `chrome146`, headers copied from A's wire request, **no cookies** | 403 | `1` | `fab_chlg_20261015224434_01M50VT71DAFFDT6V95F2C1YF4` | HTTP/2 (`http_version` 3). No redirect chain. Body 6619 bytes, `content-type: application/json`, top-level keys exactly `incidentId`, `challengeURL`, `supportURL`, `timeoutSec`, `blockURL`. `Set-Cookie` name: `abt_data` (value not stored). |
| C same as B plus the 9 CDP cookies | 200 | absent | — | HTTP/2. 155527 bytes, `widgetStates` count 80, `x-o3-page-type: pdp`, `content-type: application/json;charset=UTF-8`. `Set-Cookie` name: `__Secure-ETC` (value not stored). |
| D egress traces | 200 / 200 | n/a | n/a | Both sides `ip=83.142.30.241`, `loc=NL`, `colo=AMS`, `warp=off`, `tls=TLSv1.3`, `http=http/2`. |
| E body class of B | 403 JSON | `1` | same as B | Application challenge descriptor. Not an HTML interstitial. `challengeURL` string itself was not retained (see below). |
| F nodriver | skipped | — | — | Precondition "B and C both 403 from the same IP" was not met. |

### Headers actually on the wire for A (and replayed for B and C)

Captured with `Network.requestWillBeSent` + `requestWillBeSentExtraInfo` on the control `fetch`. Cookie header stripped and not stored.

Present: `accept: application/json`, `accept-encoding: gzip, deflate, br, zstd`, `accept-language` (above), `content-type: application/json`, `priority: u=1, i`, `referer: https://ozon.by/?__rr=1`, `sec-ch-ua*`, `sec-fetch-dest: empty`, `sec-fetch-mode: cors`, `sec-fetch-site: same-origin`, `user-agent` (above), `x-o3-app-name: dweb_client`, `x-o3-app-version: release_15-9-2026_aeebf0af`, `x-o3-manifest-version` (the manifest in `auth.py`), `x-o3-parent-requestid`, `x-page-view-id`, `x-page-previous` (empty).

**Not sent by Chrome on this fetch:** `sec-fetch-user`, `upgrade-insecure-requests`. Those are navigation headers. A local HTTP/1 rehearsal showed the `chrome146` impersonation profile *also injects* `sec-fetch-user: ?1` and `upgrade-insecure-requests: 1` when the caller does not override them. C still returned 200, so those extras are not what blocks or unblocks this endpoint. `http2-settings` / `upgrade` appeared only on the plaintext local rehearsal, not as the ozon HTTP/2 status.

`document.cookie` on the ozon tab exposes only `__Secure-ab-group` and `xcid`. The other seven are HttpOnly. Handoff used CDP `Network.getCookies` for `https://ozon.by/`.

| name | httpOnly | secure | sameSite | session | declared expiry (UTC) | ttl at probe |
|---|---|---|---|---|---|---|
| `__Secure-access-token` | yes | yes | Lax | no | 2027-10-15T22:16:52Z | ~8759 h |
| `abt_data` | yes | yes | None | no | 2027-10-15T20:28:06Z | ~8758 h |
| `__Secure-ab-group` | no | yes | Lax | no | 2027-10-15T22:16:52Z | ~8759 h |
| `__Secure-user-id` | yes | yes | Lax | no | 2027-10-15T22:16:52Z | ~8759 h |
| `__Secure-ext_xcid` | yes | yes | None | no | 2027-08-24T20:17:48Z | ~7510 h |
| `xcid` | no | no | — | **yes** | none | session |
| `cookie_settings` | yes | yes | Lax | no | 2026-11-15T20:09:33Z | ~741 h |
| `__Secure-ETC` | yes | yes | None | no | 2027-10-15T20:09:26Z | ~8757 h |
| `__Secure-refresh-token` | yes | yes | Lax | no | 2027-10-15T22:16:52Z | ~8759 h |

All nine were sent together on C. No leave-one-out. Declared `Expires` is not a measured server-side lifetime; nothing was replayed later.

## 3. Same-IP verdict: **Yes**

Browser trace and curl_cffi trace both saw `83.142.30.241` (`loc=NL`, `colo=AMS`).
How: a background Chrome tab navigated to `https://www.cloudflare.com/cdn-cgi/trace` (Chrome's own network stack, then closed) versus `curl_cffi` GET of the same URL.

Corroboration that this was not a split tunnel:

- No `HTTP_PROXY` / `HTTPS_PROXY` / `ALL_PROXY` in the environment.
- Chrome command line has no `--proxy-server`. SwitchyOmega is installed; its stored `chrome.proxy` mode is `direct`.
- Default route is `wlan0` via `192.168.0.1` (`src 192.168.0.150`). `tun0` (`172.20.0.1`) is not the default route.
- Chrome's network-service sockets are sourced from `192.168.0.150`, not `tun0`.

This is **not** the RU/BY residential egress the docstring describes. The comparison is same-IP, and that IP is a Dutch egress. DNS for `ozon.by` from this host: `185.73.194.77`, `185.73.195.108`.

## 4. Gate type (E)

The first cold response (B) is **not** a silent TLS close and **not** an HTML "Checking your browser" interstitial.

Quoted evidence from the parsed body (the script kept keys, status, and the incident id; it did not keep the JSON text, so `challengeURL` is known to exist and is **not** quoted):

- status `403`
- response header `ozon-antibot: 1`
- `content-type: application/json`
- body length 6619
- object keys: `incidentId`, `challengeURL`, `supportURL`, `timeoutSec`, `blockURL`
- `incidentId` = `fab_chlg_20261015224434_01M50VT71DAFFDT6V95F2C1YF4` (`fab_chlg_` + UTC timestamp `20261015224434`)
- `Set-Cookie` name `abt_data`
- final URL stayed on `/api/entrypoint-api.bx/page/json/v2` (recorded redirect history empty)
- no `cf-ray`, no `server: cloudflare` (`server: nginx`)

So the API itself returns an Ozon challenge descriptor. A widget (Turnstile / reCAPTCHA / DataDome / SmartCaptcha), if any, would be whatever `challengeURL` points at. That URL was not fetched and was not stored. No sitekey was observed.

The only extra cold request (row 6), sent because the JSON text had been dropped, came back **307** `text/html` (164-byte nginx "307 Temporary Redirect") with `Set-Cookie` name `__Secure-ETC` and no `ozon-antibot` header. `Location` was not recorded. It was not followed. It does not replace B as the classification sample; it does show a second cold request is not a clean replay of the first.

What B vs C isolates: the TLS stack, impersonation profile, UA, header set, URL, and egress IP were the same. The only intended difference was the cookie jar. Cookies off → 403 challenge JSON. Cookies on → 200 product JSON.

## 5. Classification: **Hybrid (Method 4)**, not tier 1, not live-CDP-only

Tier 1 is out because B is a full Chrome header replay on `curl_cffi` impersonate `chrome146`, from the **same** IP the browser just used, and it is still `403` + `ozon-antibot: 1`. A correct-looking client hello is not sufficient.

Live-CDP-only is out because C, a different TLS stack (curl-impersonate's chrome146, with a Chrome 153 UA), returned the same class of payload as the in-page fetch: HTTP 200, ~155 KB, 80 `widgetStates`, `x-o3-page-type: pdp`. The clearance traveled in the cookie jar.

It is challenge-gated for a **cold** client (B's JSON is a challenge object, not a fingerprint RST). That is the shape people file under tier 8, but the clearance is portable: a browser that has already passed can hand its cookies to `curl_cffi` and the follow-up does not need the live page. Nodriver was not required and was not run.

## 6. Bottom line

**YES, BUT only after a browser warmup that mints the cookie jar.** A never-touched `curl_cffi` client does not get in.

Config that returned 200 on this IP, immediately after reading the live jar:

- `curl_cffi` session, `impersonate="chrome146"`, HTTP/2
- UA + `sec-ch-ua*` of the live Chrome 153 (mismatch vs the 146 TLS profile did **not** block)
- the header set in section 2, including the `x-o3-*` headers from `BrowserSessionSigner`
- all 9 cookies from CDP `Network.getCookies`, Secure flag honored, names: `__Secure-access-token`, `abt_data`, `__Secure-ab-group`, `__Secure-user-id`, `__Secure-ext_xcid`, `xcid`, `cookie_settings`, `__Secure-ETC`, `__Secure-refresh-token`

`document.cookie` alone is the wrong handoff: it is missing `abt_data` and every `__Secure-*` token except `__Secure-ab-group`.

Not measured: which subset of the nine is sufficient, whether plain `requests` (no impersonation) plus the same jar also passes, or whether the jar still works from another IP. Declared cookie expiry is about a year for `abt_data` and the auth cookies; `xcid` is a session cookie; `cookie_settings` is ~31 days. No delayed replay was done, so operational TTL is unknown. Do not treat the year-long `Expires` as a measured clearance lifetime.

## 7. What `http.py` got wrong

Confirmed, on this shared IP:

- Lines 8 and 12–13. `curl_cffi` impersonating Chrome, without the jar, is 403 with `ozon-antibot: 1`. The same URL from the live page is 200. IP alone does not explain B, because A and B shared `83.142.30.241`.

Not retested, so not overturned:

- Line 7 (`requests` with no jar).
- Line 9 (RU/BY residential exits). This host's egress is NL, not those exits.

Overturned:

- **Line 10 and lines 20–24.** Replaying the browser cookies through `curl_cffi` did **not** 403. It returned 200 with 80 `widgetStates`. The clearance is **not** bound to the browser's TLS session. It is bound to the cookie jar (and, untested, possibly also to this IP). The sentence "the curl_cffi retry on the same IP immediately after was still 403 with a brand-new incidentId" is false for this session.
- `auth.py:3` "TIER FOUND: 6 — browser-executed challenge, non-portable clearance." The challenge exists for a cold client. The clearance **is** portable to `curl_cffi` on the same IP. "Non-portable" is the wrong conclusion.

Most likely reason a prior cookie replay could have failed even while listing these names: `document.cookie` does not contain `abt_data` (HttpOnly). A replay that only had the two JS-visible names would still look like B. This probe did not use that path.
