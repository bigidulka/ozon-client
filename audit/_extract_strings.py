#!/usr/bin/env python3
"""Classify string literals in downloaded ozon.by JS bundles.

Read-only. Writes bundle_strings.json, bundle_index.md, bundle_findings.md.
"""
from __future__ import annotations

import json
import os
import re
from collections import defaultdict

ROOT = str(__import__("pathlib").Path(__file__).resolve().parent)
BUNDLES = os.path.join(ROOT, "bundles")
MAP = os.path.join(ROOT, "download_map.json")

JUNK_QUERY = {
    "null", "this", "undefined", "true", "false", "function", "return",
    "dur", "rel", "enablejsapi", "_cb",
}
QUOTED_PARAMS = {
    "page", "text", "sort", "sorting", "filters", "filter", "tab", "menuId",
    "layout_page_index", "layout_container", "start_page_id", "widgetStateId",
    "product_id", "miniapp", "from_global", "__rr", "set_sm", "prv",
    "page_changed", "ai_mode", "redirect_query", "sku", "returnUrl", "rgPage",
    "refresh", "list", "url", "from", "sh",
}

# Client already calls these (method, path without query).
CLIENT_API = {
    ("GET", "/api/entrypoint-api.bx/page/json/v2"),
    ("GET", "/api/composer-api.bx/_action/summaryV2"),
    ("POST", "/api/composer-api.bx/_action/v2/addressBookBarTooltip"),
    ("GET", "/api/composer-api.bx/_action/v2/shellHorizontalMenuGetChildV1"),
}


def files():
    out = []
    for n in sorted(os.listdir(BUNDLES)):
        p = os.path.join(BUNDLES, n)
        if os.path.isfile(p) and n.endswith(".js"):
            out.append((n, open(p, errors="ignore").read()))
    return out


def brace_match(text, open_at):
    """text[open_at] must be '{'. Return inclusive end index or -1."""
    depth = 0
    i = open_at
    while i < len(text):
        c = text[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return i
        elif c in ("'", '"', "`"):
            q = c
            i += 1
            while i < len(text):
                if text[i] == "\\":
                    i += 2
                    continue
                if text[i] == q:
                    break
                i += 1
        i += 1
    return -1


def iter_fetches(text):
    key = "this.fetch("
    i = 0
    while True:
        j = text.find(key, i)
        if j < 0:
            return
        k = j + len(key)
        while k < len(text) and text[k].isspace():
            k += 1
        if k < len(text) and text[k] == "{":
            end = brace_match(text, k)
            if end > 0:
                yield j, text[k : end + 1], text[max(0, j - 350) : j]
        i = k + 1


def read_js_expr(text, i):
    """Read one JS expression starting at i. Stops at comma/paren at depth 0,
    but not inside strings or ${}."""
    start = i
    depth = 0
    while i < len(text):
        c = text[i]
        if c in ("'", '"', "`"):
            q = c
            i += 1
            while i < len(text):
                if text[i] == "\\":
                    i += 2
                    continue
                if q == "`" and text[i] == "$" and i + 1 < len(text) and text[i + 1] == "{":
                    i += 2
                    depth2 = 1
                    while i < len(text) and depth2:
                        if text[i] == "{":
                            depth2 += 1
                        elif text[i] == "}":
                            depth2 -= 1
                        i += 1
                    continue
                if text[i] == q:
                    i += 1
                    break
                i += 1
            continue
        if c in "([{":
            depth += 1
        elif c in ")]}":
            if depth == 0:
                break
            depth -= 1
        elif c == "," and depth == 0:
            break
        i += 1
    return text[start:i].strip(), i


def strings_in(expr):
    """Pull "..." '...' `...` literals out of a small expression."""
    out = []
    for m in re.finditer(r'"((?:[^"\\]|\\.)*)"|\'((?:[^\'\\]|\\.)*)\'|`((?:[^`\\]|\\.)*)`', expr):
        out.append(next(g for g in m.groups() if g is not None))
    return out


def norm_template(path):
    path = path.strip().strip("`")
    path = re.sub(r"\$\{[^}]*\}", "{param}", path)
    return path


def parse_fetch_obj(obj, before):
    method_m = re.search(r'method\s*:\s*["\'](get|post|put|delete|patch)["\']', obj, re.I)
    method = method_m.group(1).upper() if method_m else "?"
    paths = []
    dynamic = False
    pm = re.search(r"path\s*:\s*", obj)
    shorthand = False
    if not pm and re.search(r"[,{]\s*path\s*[,}]", obj):
        shorthand = True
        expr = "path"
        lits = []
    elif pm:
        expr, _ = read_js_expr(obj, pm.end())
        lits = [norm_template(s) for s in strings_in(expr)]
    else:
        expr, lits = "", []
    if pm or shorthand:
        if lits:
            paths.extend(lits)
            if "{param}" in "".join(lits) or (pm and "?" in expr and ":" in expr):
                dynamic = "{param}" in "".join(lits)
        elif re.fullmatch(r"[A-Za-z_$][\w$]*", expr or ""):
            matches = list(re.finditer(
                rf'(?:var|let|const)?\s*(?<![\w$+\-]){re.escape(expr)}\s*=(?!=)\s*',
                before,
            ))
            am = matches[-1] if matches else None
            if am:
                assigned, _ = read_js_expr(before, am.end())
                got = [norm_template(s) for s in strings_in(assigned)]
                got = [g for g in got if g.startswith("/") or re.match(r"^[A-Za-z0-9_./{}-]+$", g)]
                got = [g for g in got if not g.startswith("?")]
                if got:
                    paths.extend(got)
                    dynamic = any("{param}" in g for g in got)
                else:
                    dynamic = True
                    paths.append("{path}")
            else:
                dynamic = True
                paths.append("{path}")
        else:
            dynamic = True
            paths.append("{path}")
    override = None
    om = re.search(r"overrideServicePath\s*:\s*", obj)
    if om:
        ov, _ = read_js_expr(obj, om.end())
        lits = strings_in(ov)
        if lits:
            override = lits[0]
        elif "c(" in ov or "entrypoint" in before:
            override = "__version_switch__"
    return method, paths, dynamic, override


def join_api(service_path, version, path):
    path = norm_template(path)
    q = ""
    if "?" in path:
        path, q = path.split("?", 1)
        q = "?" + q
    # page/json version switch is applied by the caller via service path;
    # do not also prepend serviceVersion.
    base = "/api/" + service_path.strip("/")
    if version:
        base = base.rstrip("/") + "/v" + str(version)
    if not path.startswith("/"):
        path = "/" + path
    full = re.sub(r"(?<!:)/{2,}", "/", base + path)
    return full + (q or "")

def add(bucket, key, source, n=1):
    rec = bucket[key]
    rec["count"] += n
    rec["sources"].add(source)


def main():
    blob = files()
    endpoints = defaultdict(lambda: {"count": 0, "sources": set(), "dynamic": False, "query": ""})
    # key: (method, path_without_query)

    def record(method, full, source, dynamic=False):
        path, _, query = full.partition("?")
        path = re.sub(r"(?<!:)/{2,}", "/", path)
        if any(ch in path for ch in ("`", "$", " ", "\n", "'", '"')):
            return
        if path.endswith("{") or "/{param}{param}" in path:
            return
        rec = endpoints[(method, path)]
        rec["count"] += 1
        rec["sources"].add(source)
        rec["dynamic"] = rec["dynamic"] or dynamic or "{param}" in path or "{path}" in path
        if query and "{" not in query and "$" not in query:
            rec["query"] = query
        elif query and "{param}" in query:
            rec["query"] = re.sub(r"\$\{[^}]*\}", "{param}", query)

    for name, text in blob:
        # service windows
        spans = []
        for m in re.finditer(r'servicePath\s*=\s*(["\'][^"\']+["\']|[A-Za-z_$][\w$]*)', text):
            raw = m.group(1)
            if raw[0] in "\"'":
                sp = raw[1:-1]
            else:
                prev = text[max(0, m.start() - 1200):m.start()]
                found = list(re.finditer(
                    rf'(?:var\s+)?{re.escape(raw)}\s*=\s*["\']([^"\']+)["\']',
                    prev,
                ))
                if not found:
                    continue
                sp = found[-1].group(1)
            start = max(0, m.start() - 400)
            end_m = re.search(r'__serviceName', text[m.end(): m.end() + 8000])
            end = m.end() + (end_m.start() if end_m else 6000)
            ver_m = re.search(r'serviceVersion\s*=\s*["\']?(\d+)["\']?', text[start:end])
            spans.append((start, end, sp, ver_m.group(1) if ver_m else ""))

        def span_for(pos):
            for start, end, sp, ver in spans:
                if start <= pos <= end:
                    return sp, ver
            return None, ""

        for pos, obj, before in iter_fetches(text):
            method, paths, dynamic, override = parse_fetch_obj(obj, before)
            sp, ver = span_for(pos)
            if sp is None:
                # still record literal absolute paths inside the fetch
                for p in paths:
                    if p.startswith("/api/") or "composer-api" in p or "entrypoint-api" in p:
                        record(method, p if p.startswith("/") else "/" + p, name, dynamic)
                continue
            use_sps = [sp]
            if override == "__version_switch__":
                use_sps = ["entrypoint-api.bx", "composer-api.bx"]
            elif override:
                use_sps = [override]
            for p in paths:
                if override == "__version_switch__" and "page/json" in p:
                    # c(version): 2 -> entrypoint-api.bx (call-site default), else composer.
                    concrete = re.sub(r"v\{param\}", "v2", p)
                    record(method, join_api("entrypoint-api.bx", "", concrete), name, False)
                    other = re.sub(r"v\{param\}", "v{n}", p)
                    record(method, join_api("composer-api.bx", "", other), name, True)
                    continue
                targets = use_sps
                vers = [ver]
                if override == "__version_switch__":
                    targets = ["entrypoint-api.bx", "composer-api.bx"]
                    vers = ["", ""]
                for usp, uv in zip(targets, vers):
                    if p.startswith("{") or p.startswith("("):
                        record(method, join_api(usp, uv, "/{path}"), name, True)
                    else:
                        record(method, join_api(usp, uv, p), name, "{param}" in p or dynamic)

        # ComposerService.actionPost/Get({name:"literal"})
        for m in re.finditer(
            r'action(Post|Get|Put|Delete)\(\{name:\s*(?:'
            r'"([^"]+)"|\'([^\']+)\'|`([^`]+)`'
            r')',
            text,
        ):
            verb = {"Post": "POST", "Get": "GET", "Put": "PUT", "Delete": "DELETE"}[m.group(1)]
            literal = next(g for g in m.groups()[1:] if g)
            if "${" in literal or "/" == literal[0:1] and "v2/" not in literal:
                continue
            record(verb, "/api/composer-api.bx/_action/" + literal.lstrip("/"), name, False)

        # concrete review action ids (the broad rp* scan also matched chunk names)
        for lit in (
            "createCommentV2", "removeComment", "removeReview", "reportComment",
            "reportReview", "voteComment", "voteReview", "loadComment", "addComment",
            "rpDeleteMyReviewV2", "rpGetCommentsByReviewUuid", "rpIgnoreItem",
            "rpImageUpload", "rpSetOpinionUsefulnessV2", "v2/rpReportAbuseV2",
        ):
            if f'"{lit}"' in text or f"'{lit}'" in text:
                # only count inside rp-product bundles to avoid generic words
                if name.startswith("rp-product"):
                    record("POST", "/api/composer-api.bx/_action/" + lit, name, False)

    # literal API-ish paths not built via fetch()
    lit_pat = re.compile(
        r'(?:https?:)?//[^"\'\s]{0,80}?(/api/[A-Za-z0-9_./{}\-]{2,120})'
        r'|["\'`](/api/[A-Za-z0-9_./{}\-]{3,140})'
        r'|["\'`](/(?:pop-stats-collector)/api/[A-Za-z0-9_./{}\-]{2,120})'
        r'|["\'`]([^"\'`]{0,40}logs-gateway/input)'
    )
    extra_literals = defaultdict(lambda: {"count": 0, "sources": set()})
    for name, text in blob:
        if "/pop-stats-collector/api/v2/pop-stats/send" in text:
            extra_literals["/pop-stats-collector/api/v2/pop-stats/send"]["count"] += text.count("/pop-stats-collector/api/v2/pop-stats/send")
            extra_literals["/pop-stats-collector/api/v2/pop-stats/send"]["sources"].add(name)
        if "/api/logs-gateway/input" in text:
            extra_literals["/api/logs-gateway/input"]["count"] += text.count("/api/logs-gateway/input")
            extra_literals["/api/logs-gateway/input"]["sources"].add(name)
        for m in lit_pat.finditer(text):
            raw = next(g for g in m.groups() if g)
            raw = raw.split("?")[0]
            if not raw.startswith("/"):
                raw = "/" + raw.split("/", 1)[-1] if "logs-gateway" in raw else raw
            if "logs-gateway" in raw and not raw.startswith("/"):
                raw = "/" + raw[raw.find("logs-gateway"):]
            extra_literals[raw]["count"] += 1
            extra_literals[raw]["sources"].add(name)

    # headers
    headers = defaultdict(lambda: {"count": 0, "sources": set()})
    hq = re.compile(r'x-(?:o3|client|requested|page)-[a-z0-9-]+', re.I)
    for name, text in blob:
        for m in hq.finditer(text):
            add(headers, m.group(0).lower(), name)

    # query params
    params = defaultdict(lambda: {"count": 0, "sources": set()})
    qp = re.compile(r'[?&]([A-Za-z_][A-Za-z0-9_]{1,40})=')
    sp = re.compile(r'searchParams\.(?:get|set|has|append|delete)\(\s*["\']([^"\']+)["\']')
    for name, text in blob:
        found = set(qp.findall(text)) | set(sp.findall(text))
        for k in found:
            if k in JUNK_QUERY:
                continue
            if re.fullmatch(r'[a-zA-Z]{1,2}', k) and k not in {"id", "sh", "tab"}:
                continue
            if len(k) < 3 and k not in {"id", "sh", "tab"}:
                continue
            add(params, k, name, text.count(k))
        for k in QUOTED_PARAMS:
            c = len(re.findall(r'["\']' + re.escape(k) + r'["\']', text))
            if c:
                add(params, k, name, c)
        if re.search(r'\.start_page_id\s*=', text):
            add(params, "start_page_id", name, 1)

    # widgets: composer registry keys `name:{content:`
    widgets = defaultdict(lambda: {"count": 0, "sources": set(), "kind": "registry"})
    wpat = re.compile(r'(?:"([A-Za-z][\w-]{2,80})"|([A-Za-z][\w-]{2,80})):\{content:')
    for name, text in blob:
        for a, b in wpat.findall(text):
            key = a or b
            add(widgets, key, name)
            widgets[key]["kind"] = "registry"
    # explicit state-prefix array and data-widget attributes
    for name, text in blob:
        for m in re.findall(r'data-widget=\\?"([A-Za-z][\w-]{2,60})"', text):
            add(widgets, m, name)
            widgets[m]["kind"] = "data-widget"
        for m in re.findall(r'name:\s*"([a-z][A-Za-z0-9]+Widget)"', text):
            add(widgets, m, name)
            widgets[m]["kind"] = "vue_name"

    # tab / sort / filter identifiers
    tabs = defaultdict(lambda: {"count": 0, "sources": set(), "kind": ""})
    for name, text in blob:
        for m in set(re.findall(r'RESPONSE_FILTER_TYPE_[A-Z0-9_]+', text)):
            add(tabs, m, name)
            tabs[m]["kind"] = "filter_type"
        for m in set(re.findall(r'["\'](usefulness_desc|score_asc|score_desc)["\']', text)):
            add(tabs, m, name)
            tabs[m]["kind"] = "review_sort"
        for m, kind in (
            ("section-description", "pdp_section"),
            ("description-tab", "pdp_section"),
            ("characteristics", "pdp_section"),
            ("short-characteristics", "pdp_section"),
            ("rich-content", "pdp_section"),
            ("rich-annotation", "pdp_section"),
            ("search-sortings", "sort_control"),
            ("webTabs", "tab_widget"),
            ("webMobTabs", "tab_widget"),
            ("webMobTab", "tab_widget"),
            ("webProductTabs", "tab_widget"),
            ("webReviewTabs", "tab_widget"),
            ("webUgcNavTabs", "tab_widget"),
            ("webReviewsTitle", "tab_widget"),
            ("webListReviews", "tab_widget"),
            ("webListQuestions", "tab_widget"),
            ("webQuestionCount", "tab_widget"),
            ("tileGridDesktop", "listing_widget"),
            ("searchResultsV2", "listing_widget"),
        ):
            c = len(re.findall(r'(?<![\w-])' + re.escape(m) + r'(?![\w-])', text))
            if c:
                add(tabs, m, name, c)
                if not tabs[m]["kind"]:
                    tabs[m]["kind"] = kind

    def dump(bucket, extra_fields=()):
        rows = []
        for key, rec in bucket.items():
            if isinstance(key, tuple):
                row = {"method": key[0], "value": key[1]}
            else:
                row = {"value": key}
            row["count"] = rec["count"]
            row["sources"] = sorted(rec["sources"])
            for f in extra_fields:
                if f in rec and rec[f] not in ("", False, None):
                    row[f] = rec[f]
            rows.append(row)
        rows.sort(key=lambda r: (r.get("value") or "", r.get("method") or ""))
        return rows

    api_rows = dump(endpoints, ("dynamic", "query"))
    junk_actions = {"post", "get", "put", "delete", "miniapp", "v2", "rpProduct", "{path}"}
    cleaned = []
    for r in api_rows:
        action = r["value"].split("/_action/", 1)[-1] if "/_action/" in r["value"] else ""
        action = action.strip("/")
        if action in junk_actions or r["value"].rstrip("/").endswith("/_action/v2"):
            continue
        if r["value"].endswith("/{path}"):
            # keep the dispatcher pattern, but only one pair is useful; still keep
            pass
        cleaned.append(r)
    api_rows = cleaned
    # fold literal paths that are not already represented
    known_paths = {r["value"] for r in api_rows}
    for path, rec in extra_literals.items():
        norm = path.split("?")[0]
        exact = next((r for r in api_rows if r["value"] == norm), None)
        if exact:
            exact["sources"] = sorted(set(exact["sources"]) | rec["sources"])
            exact["count"] += rec["count"]
        elif "/api/" in norm or "logs-gateway" in norm or "pop-stats" in norm:
            method = "POST" if ("pop-stats" in norm or "logs-gateway" in norm) else "?"
            api_rows.append({
                "method": method,
                "value": norm,
                "count": rec["count"],
                "sources": sorted(rec["sources"]),
                "literal": True,
            })
    api_rows.sort(key=lambda r: (r["value"], r.get("method") or ""))

    action_rows = []
    for r in api_rows:
        val = r["value"]
        if "/_action/" in val:
            action = val.split("/_action/", 1)[1]
            action_rows.append({
                "value": action,
                "path": val,
                "method": r.get("method"),
                "count": r["count"],
                "sources": r["sources"],
                **({"dynamic": True} if r.get("dynamic") else {}),
            })
    action_rows.sort(key=lambda r: r["value"])

    widget_rows = dump(widgets, ("kind",))
    header_rows = dump(headers)
    param_rows = dump(params)
    tab_rows = dump(tabs, ("kind",))

    payload = {
        "api_paths": api_rows,
        "actions": action_rows,
        "widgets": widget_rows,
        "headers": header_rows,
        "query_params": param_rows,
        "tab_identifiers": tab_rows,
    }
    json.dump(payload, open(os.path.join(ROOT, "bundle_strings.json"), "w"), ensure_ascii=False, indent=1)
    print("api", len(api_rows), "actions", len(action_rows), "widgets", len(widget_rows),
          "headers", len(header_rows), "params", len(param_rows), "tabs", len(tab_rows))

    # --- index ---
    meta = json.load(open(MAP))
    lines = []
    lines.append("# Bundle index")
    lines.append("")
    lines.append("Static JS captured from ozon.by on 2026-10-16 via one CDP pass")
    lines.append("(new tab, then closed) that recorded `document` script URLs and")
    lines.append("`performance` resource entries. Files were then GET from `st.ozone.ru`")
    lines.append("with urllib. No POSTs.")
    lines.append("")
    lines.append("Page types and the URL that actually loaded:")
    lines.append("")
    src = json.load(open(os.path.join(ROOT, "script_sources.json")))
    for p in src["pages"]:
        lines.append(f"- **{p['page_type']}**: `{p['final_url']}` — {p['title'][:90]}")
    lines.append("")
    lines.append("Search note: requesting `https://ozon.by/search/?text=iphone&from_global=true`")
    lines.append("was rewritten by the site to a predicted brand category")
    lines.append("(`/category/smartfony-15502/apple-26303000/?text=iphone&...`).")
    lines.append("That page still loaded the catalog-search microfrontend")
    lines.append("(`catalog-search.js`, sort and active-filter bundles), so search widgets")
    lines.append("are covered. A non-rewritten `/search/?text=` HTML document was not")
    lines.append("snapshotted separately (CDP was used once).")
    lines.append("")
    ok = [r for r in meta["files"] if r["status"] == "ok"]
    lines.append(f"Deduped bundles: **{len(ok)}**. Downloaded bytes: **{sum(r['bytes'] for r in ok)}**.")
    lines.append("None exceeded the 15 MB skip threshold. Basename collisions")
    lines.append("(`index.js`, `entry.*.js`) are disambiguated with a parent-path prefix;")
    lines.append("the original basename is kept as the suffix.")
    lines.append("")
    lines.append("| URL | local file | bytes | page types |")
    lines.append("|---|---|---:|---|")
    for r in sorted(ok, key=lambda r: r["url"]):
        pages = ", ".join(r.get("pages") or [])
        url = r["url"].replace("|", "\\|")
        lines.append(f"| `{url}` | `{r['filename']}` | {r['bytes']} | {pages} |")
    open(os.path.join(ROOT, "bundle_index.md"), "w").write("\n".join(lines) + "\n")

    write_findings(payload, ok)
    print("wrote index and findings")


def write_findings(payload, downloaded):
    apis = payload["api_paths"]
    actions = payload["actions"]
    headers = payload["headers"]
    params = payload["query_params"]
    tabs = payload["tab_identifiers"]
    widgets = payload["widgets"]

    def has(method, path):
        return any(r.get("method") == method and r["value"] == path for r in apis)

    missing = []
    for r in apis:
        key = (r.get("method"), r["value"])
        if key in CLIENT_API:
            continue
        if r["value"].endswith("/{path}"):
            continue
        missing.append(r)

    # promising read-oriented catalogue endpoints
    interesting_sub = (
        "widget/json",
        "page/json",
        "getSearchTapTags",
        "categoryChildV3",
        "catalogMenuItemV1",
        "catalogMenuServicesV1",
        "horizontalContentV1",
        "getServicesV1",
        "/location/",
        "favoriteLists",
        "favoriteSuggest",
        "favoriteCheckItems",
        "favoriteCountItems",
        "favoriteGetShared",
        "summary",
        "pdpGetStarsBalance",
        "translateProductAttributes",
        "pdpViewProduct",
        "getSearchTapTags",
        "suggestedTapTags",
    )

    def interesting(r):
        v = r["value"]
        if "/user/location" in v:
            return False
        if any(s in v for s in (
            "logout", "Password", "Passport", "registration", "Auth", "otp", "Otp",
            "checkout", "Checkout", "addToCart", "Delete", "unsubscribe", "Subscribe",
            "patchUser", "upload", "unbind", "switchUser", "changeEmail", "changePhone",
            "goCheckout", "createOrder", "legal", "Legal", "sber", "Sber",
        )):
            return False
        return any(s in v for s in interesting_sub)

    prom = [r for r in missing if interesting(r)]
    # dedupe prom by value+method
    seen = set()
    prom_u = []
    for r in prom:
        k = (r.get("method"), r["value"])
        if k in seen:
            continue
        seen.add(k)
        prom_u.append(r)

    writes = [r for r in missing if r.get("method") in {"POST", "PUT", "DELETE"} and not interesting(r)]

    def src(r):
        return ", ".join(f"`{s}`" for s in r["sources"][:4])

    lines = []
    lines.append("# Bundle findings")
    lines.append("")
    lines.append("What the static bundles on the seven catalogue page types contain,")
    lines.append("compared with what `ozon_client` already calls.")
    lines.append("")
    lines.append("## Coverage")
    lines.append("")
    lines.append(f"- Downloaded bundles: {len(downloaded)} (all HTTP 200, all under 15 MB).")
    lines.append(f"- API paths reconstructed: {len(apis)}.")
    lines.append(f"- `_action` names: {len(actions)}.")
    lines.append(f"- Widget registry keys (`name:{{content:`): {len(widgets)}.")
    lines.append(f"- Header names (`x-o3-*`, `x-page-*`, `x-client-*`, `x-requested-*`): {len(headers)}.")
    lines.append(f"- Query-parameter names: {len(params)}.")
    lines.append(f"- Sort / filter / tab identifiers: {len(tabs)}.")
    lines.append("- GraphQL operation names: **none**. No `graphql`, `__typename`, or `operationName` string in any loaded bundle.")
    lines.append("- `x-client-*`: **none**.")
    lines.append("- `x-requested-*`: **none**.")
    lines.append("")
    lines.append("Paths are reconstructed the way `AbstractApiService.callApi` builds them")
    lines.append("(`main.js`: `getBrowserApiUrl` defaults the gateway to `api`, so the")
    lines.append("prefix is `/api/` + `servicePath` + optional `/v{serviceVersion}` + `path`).")
    lines.append("Each row in `bundle_strings.json` cites the local file under `audit/bundles/`.")
    lines.append("")
    lines.append("## What the client already uses")
    lines.append("")
    lines.append("| Call | In these bundles? |")
    lines.append("|---|---|")
    lines.append("| `GET /api/entrypoint-api.bx/page/json/v2?url=` | Yes. `ComposerService.jsonGet`, default version 2 switches service path to `entrypoint-api.bx`. Source: `main.js`. |")
    lines.append("| `GET /api/composer-api.bx/_action/summaryV2` | Yes. `host.js`, `bx-fe__common-feature-cart__1.7.8__index.js`. |")
    lines.append("| `GET /api/composer-api.bx/_action/v2/shellHorizontalMenuGetChildV1` | Yes. `cms-desktop-horizontal-menu.js` (`cmsShellHorizontalMenuGetChildV1`, query key `menuId`). |")
    lines.append("| `POST /api/composer-api.bx/_action/v2/addressBookBarTooltip` | **Not a string in the loaded bundles.** The action name was not found. The address-bar widget that did load is `addressBookMap-all-addressbook-bar.js` / registry key `addressBookBarWeb` (`cart-checkout-geo.js`). |")
    lines.append("| Page composer targets `/`, `/search/`, `/category/...`, `/product/...`, `/reviews/<sku>/`, `/cart`, `/my/favorites/`, `/searchSuggestions/search/` | These are page URLs passed as the `url` query of `page/json/v2`, not separate endpoints. `/search/` itself is not hard-coded; search UI lives in `search-desktop-search-bar-desktop.js`. |")
    lines.append("| Headers `x-o3-app-name`, `x-o3-app-version`, `x-o3-manifest-version`, `x-o3-parent-requestid`, `x-page-view-id`, `x-page-previous` | Yes, as one enum in `main.js`. |")
    lines.append("")
    lines.append("`layout_page_index` is **not** ignored by the frontend: `main.js` reads it")
    lines.append("(`searchParams.get(\"layout_page_index\")`) and `composer-all-paginator.js` /")
    lines.append("`catalog-all-infinite-virtual-paginator.js` send `layout_container`.")
    lines.append("`start_page_id` is a string in `composer-all-paginator.js`. The client’s note")
    lines.append("that `layout_page_index` is ignored matches server behaviour observed live,")
    lines.append("not the bundle (the bundle still supplies it).")
    lines.append("")
    lines.append("Strings the client sends that **do not appear** in these bundles:")
    lines.append("`from_global`, `__rr`, `prv`, `set_sm`. They are page-level query keys,")
    lines.append("not literals in the JS that was loaded.")
    lines.append("")
    lines.append("## Headers present in bundles")
    lines.append("")
    for r in headers:
        lines.append(f"- `{r['value']}` — {src(r)}")
    lines.append("")
    lines.append("## Query parameters present in bundles")
    lines.append("")
    for r in params:
        lines.append(f"- `{r['value']}` — {src(r)}")
    lines.append("")
    lines.append("Single-letter `?e=` / `?n=` matches from minified code were dropped as false positives.")
    lines.append("")
    lines.append("## Sort, filter, and tab identifiers")
    lines.append("")
    lines.append("Review list sort values (string literals, not yet passed by `reviews()`):")
    lines.append("")
    for r in tabs:
        if r.get("kind") == "review_sort":
            lines.append(f"- `{r['value']}` — {src(r)}")
    lines.append("")
    lines.append("Filter *types* (not filter ids):")
    lines.append("")
    for r in tabs:
        if r.get("kind") == "filter_type":
            lines.append(f"- `{r['value']}` — {src(r)}")
    lines.append("")
    lines.append("Product-page section / tab widgets. The lazy chunks `pdp-all-tabs`,")
    lines.append("`pdp-mob-tabs-v1`, and `rp-product-all-product-tabs-v1` are **referenced** from")
    lines.append("`pdp.js` / `rp-product.js` but were **not** in the initial load, so the")
    lines.append("tab-key enum inside them was not downloaded. What *is* in the loaded files:")
    lines.append("")
    for r in tabs:
        if r.get("kind") in {"pdp_section", "tab_widget", "sort_control", "listing_widget"}:
            lines.append(f"- `{r['value']}` ({r['kind']}) — {src(r)}")
    lines.append("")
    lines.append("There is no literal `\"specs\"` tab key. Characteristics are the widget")
    lines.append("`webShortCharacteristics` / `webCharacteristics` (registry in `pdp.js`) and")
    lines.append("the section string `characteristics` in `pdp-all-description-v3.js` and")
    lines.append("`pdp-desktop-product-mini-v1.js`. Questions are `webQuestionCount` /")
    lines.append("`webListQuestions` (`rp-product.js`), not a `questions` query value.")
    lines.append("")
    lines.append("## Widget names")
    lines.append("")
    lines.append(f"The full registry is {len(widgets)} keys in `bundle_strings.json` → `widgets`.")
    lines.append("Catalogue-relevant ones the client already knows by state prefix, confirmed")
    lines.append("as registry keys:")
    lines.append("")
    want = [
        "tileGridDesktop", "tileGrid2", "skuGrid", "searchResultsV2", "filters",
        "searchResultsFiltersActive", "searchResultsSort", "suggestedTapTags",
        "tagList", "webListReviews", "webReviewsTitle", "webReviewSort",
        "webQuestionCount", "webListQuestions", "webDescription",
        "webShortCharacteristics", "webCharacteristics", "webGallery",
        "addressBookBarWeb", "headerCartIcon", "emptyCart", "favoriteCounter",
        "horizontalMenu", "catalogMenu", "paginator", "infiniteVirtualPaginator",
    ]
    by_name = {w["value"]: w for w in widgets}
    for name in want:
        w = by_name.get(name)
        if w:
            lines.append(f"- `{name}` — {src(w)}")
        else:
            lines.append(f"- `{name}` — **not** a registry key in the loaded bundles.")
    lines.append("")
    lines.append("`reviewsTitleWidget` is the Vue `name` in `rp-product-all-reviews-title.js`;")
    lines.append("the composer key is `webReviewsTitle`. `data-widget=\"webListReviews\"` is")
    lines.append("a literal in `rp-product-web-list-reviews-v3.js`.")
    lines.append("")
    lines.append("Cart also loaded every `entry.travel.js` split (avia, hotels, railway, tours, …).")
    lines.append("Those files contribute a large share of the 1k+ registry keys (travel checkout")
    lines.append("widgets). They are real strings, not catalogue endpoints.")
    lines.append("")
    lines.append("## Endpoints and actions the client does not call")
    lines.append("")
    lines.append("### Read-shaped, worth a catalogue client knowing about")
    lines.append("")
    lines.append("These are absent from `session.py` / `catalog.py`. Method and path are the")
    lines.append("bundle’s own `fetch` / `actionGet` / `actionPost` literals.")
    lines.append("")
    if not prom_u:
        lines.append("None.")
    for r in prom_u:
        dyn = " (path template)" if r.get("dynamic") else ""
        q = f"?{r['query']}" if r.get("query") else ""
        lines.append(f"- `{r.get('method','?')} {r['value']}{q}`{dyn} — {src(r)}")
    lines.append("")
    lines.append("Notes on the most useful ones:")
    lines.append("")
    lines.append("- `POST /api/composer-api.bx/widget/json/v2` and `.../v2/batch` (`main.js`, `ComposerService.widget` / `widgetBatch`). This is how the site refreshes one widget (`widgetStateId` query) without refetching the whole page. The client only uses `entrypoint-api.bx/page/json/v2`.")
    lines.append("- `POST /api/entrypoint-api.bx/page/json/v2` (`ComposerService.jsonPost` in `main.js`). Same URL as the client’s GET, but POST. Not used.")
    lines.append("- `POST /api/composer-api.bx/_action/v2/getSearchTapTags` (`search-desktop-search-bar-desktop.js`). Suggest/tap tags. The client only loads `/searchSuggestions/search/` through the page composer.")
    lines.append("- Menu siblings of the one menu call the client makes: `GET .../v2/categoryChildV3` (`cms-desktop-catalog-menu.js`), `GET .../v2/catalogMenuItemV1`, `GET .../v2/catalogMenuServicesV1`, `GET .../v2/horizontalContentV1` (`catalog-menu-all-horizontal-category-menu-v1.js`), `GET .../v2/getServicesV1` (`cms-desktop-catalog-menu.js`).")
    lines.append("- `GET /api/location/v2/current` and `GET /api/location/v2/search` (`pdp-desktop-sale-v12.js`, `LocationService`, `serviceVersion` 2). `POST /api/location/v2/user/location` is the write that sets the area; not a catalogue read.")
    lines.append("- Favorites reads the client does not use (it only opens `/my/favorites/`): `GET .../_action/favoriteLists`, `GET .../_action/favoriteSuggestListTitle` (`bx-fe__common-feature-favorites__1.4.10__index.js` and `1.4.12`). `POST favoriteCountItems` / `favoriteCheckItems` are counts, still POSTs.")
    lines.append("- `GET .../_action/summary` (v1) still sits next to `summaryV2` in `host.js`.")
    lines.append("- `GET .../_action/pdpGetStarsBalance?product_id=` (`pdp-mobile-add-to-cart-v10.js`).")
    lines.append("- Review sort is not a separate endpoint. `webListReviews` takes sort ids `usefulness_desc`, `score_asc`, `score_desc` (`rp-product-web-list-reviews-v3.js`). `reviews()` does not send them.")
    lines.append("")
    lines.append("`addressBookBarTooltip` remains a live-traffic endpoint with **no** bundle")
    lines.append("source in this set. Do not treat it as confirmed by these files.")
    lines.append("")
    lines.append("### Write actions present in the bundles (client correctly does not call them)")
    lines.append("")
    lines.append("Listed so they are not mistaken for missing catalogue reads. Not a usage guide.")
    lines.append("")
    # compact unique write paths, skip dynamic
    shown = 0
    for r in writes:
        if r.get("dynamic"):
            continue
        if shown >= 40:
            lines.append(f"- … {len(writes) - shown} more write-shaped paths are in `bundle_strings.json` → `actions`.")
            break
        lines.append(f"- `{r.get('method','?')} {r['value']}` — {src(r)}")
        shown += 1
    if shown == 0:
        lines.append("None classified.")
    lines.append("")
    lines.append("Review mutations encoded as action-name literals (same `_action` prefix,")
    lines.append("`rp-product-web-list-reviews-v3.js` and siblings): `createCommentV2`,")
    lines.append("`removeReview`, `rpDeleteMyReviewV2`, `rpGetCommentsByReviewUuid` (this one")
    lines.append("is a read), `rpSetOpinionUsefulnessV2`, `v2/rpReportAbuseV2`, `voteReview`,")
    lines.append("`reportReview`.")
    lines.append("")
    lines.append("### Also fetched, not composer")
    lines.append("")
    lines.append("- `POST /pop-stats-collector/api/v2/pop-stats/send` — `1.0.4.js` (CDN RUM).")
    lines.append("- `POST {xapi}/api/logs-gateway/input` — `main.js` (`ClientLogger`). Host is the xapi gateway, not `ozon.by`.")
    lines.append("")
    lines.append("## Gaps")
    lines.append("")
    lines.append("- Search HTML was the brand-predicted category, not a raw `/search/?text=` document. Search bundles still loaded.")
    lines.append("- Lazy widget chunks named from registries but not requested on first paint (for example `pdp-all-tabs`, `rp-product-web-review-sort-desktop`, `catalog-all-search-suggestions`) were not downloaded. Their names are in the parent bundles (`pdp.js`, `rp-product.js`, `catalog-search.js`) and therefore in `widgets`, but their bodies are absent.")
    lines.append("- `addressBookBarTooltip`, `from_global`, `__rr`, `prv`, and `set_sm` are not in this bundle set.")
    open(os.path.join(ROOT, "bundle_findings.md"), "w").write("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
