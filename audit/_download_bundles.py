#!/usr/bin/env python3
"""GET static JS bundles listed in script_sources.json. No POSTs."""
from __future__ import annotations

import json
import os
import ssl
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.error import HTTPError, URLError
from urllib.parse import unquote, urlparse
from urllib.request import Request, urlopen

ROOT = str(__import__("pathlib").Path(__file__).resolve().parent)
SRC = os.path.join(ROOT, "script_sources.json")
OUT = os.path.join(ROOT, "bundles")
MAP = os.path.join(ROOT, "download_map.json")
MAX_BYTES = 15 * 1024 * 1024
WORKERS = 5
UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/153.0.0.0 Safari/537.36"
)

ctx = ssl.create_default_context()


def load_urls():
    data = json.load(open(SRC))
    by_url = {}
    for page in data["pages"]:
        urls = set(page["scripts"]) | set(page["links"]) | set(page["perf"])
        for raw in urls:
            clean = raw.split("#")[0]
            path = urlparse(clean).path
            if ".js" not in path.split("?")[0]:
                continue
            base = clean.split("?")[0]
            by_url.setdefault(base, set()).add(page["page_type"])
            # keep one full URL (with query if any) for the request
            by_url[base]  # noqa
    # re-walk to remember a request URL (query stripped is fine for CDN)
    return {u: sorted(pages) for u, pages in by_url.items()}


def local_names(urls):
    """Prefer the original basename; disambiguate collisions with parent dirs."""
    from collections import defaultdict

    groups = defaultdict(list)
    for u in urls:
        path = unquote(urlparse(u).path)
        base = path.rstrip("/").split("/")[-1]
        groups[base].append(u)
    names = {}
    for base, group in groups.items():
        if len(group) == 1:
            names[group[0]] = base
            continue
        for u in group:
            path = unquote(urlparse(u).path).strip("/")
            parts = path.split("/")
            # drop the basename, keep up to 3 parent segments that differ
            parents = parts[:-1]
            # shared-deps: @scope/pkg/version
            if "shared-deps" in parents:
                i = parents.index("shared-deps")
                tag = "__".join(parents[i + 1 :]).replace("@", "")
            elif "detached" in parents:
                i = parents.index("detached")
                tag = "__".join(parents[i + 1 :])
            else:
                tag = "__".join(parents[-3:])
            tag = tag.replace("/", "__")
            names[u] = f"{tag}__{base}" if tag else base
    # final uniqueness
    seen = {}
    for u, name in list(names.items()):
        if name not in seen:
            seen[name] = u
            continue
        n = 2
        stem, ext = os.path.splitext(name)
        while f"{stem}__{n}{ext}" in seen:
            n += 1
        names[u] = f"{stem}__{n}{ext}"
        seen[names[u]] = u
    return names


def fetch(url, dest):
    req = Request(url, headers={"User-Agent": UA, "Accept": "*/*", "Referer": "https://ozon.by/"})
    t0 = time.time()
    try:
        with urlopen(req, timeout=40, context=ctx) as resp:
            cl = resp.headers.get("Content-Length")
            if cl and int(cl) > MAX_BYTES:
                return {
                    "url": url,
                    "status": "skipped_large",
                    "bytes": int(cl),
                    "http": resp.status,
                    "elapsed_s": round(time.time() - t0, 2),
                }
            buf = bytearray()
            while True:
                chunk = resp.read(1024 * 64)
                if not chunk:
                    break
                buf += chunk
                if len(buf) > MAX_BYTES:
                    return {
                        "url": url,
                        "status": "skipped_large",
                        "bytes": len(buf),
                        "http": resp.status,
                        "elapsed_s": round(time.time() - t0, 2),
                    }
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            tmp = dest + ".part"
            with open(tmp, "wb") as f:
                f.write(buf)
            os.replace(tmp, dest)
            return {
                "url": url,
                "status": "ok",
                "bytes": len(buf),
                "http": getattr(resp, "status", 200),
                "elapsed_s": round(time.time() - t0, 2),
            }
    except HTTPError as e:
        return {"url": url, "status": "http_error", "http": e.code, "error": str(e), "bytes": 0}
    except URLError as e:
        return {"url": url, "status": "url_error", "error": str(e.reason), "bytes": 0}
    except Exception as e:
        return {"url": url, "status": "error", "error": f"{type(e).__name__}: {e}", "bytes": 0}


def main():
    os.makedirs(OUT, exist_ok=True)
    pages = load_urls()
    names = local_names(pages)
    # resume
    done = {}
    if os.path.exists(MAP):
        prev = json.load(open(MAP))
        for row in prev.get("files", []):
            if row.get("status") == "ok" and os.path.exists(os.path.join(OUT, row["filename"])):
                done[row["url"]] = row
    lock = threading.Lock()
    results = list(done.values())

    todo = [u for u in pages if u not in done]
    print(f"urls={len(pages)} already={len(done)} todo={len(todo)}", flush=True)

    def persist():
        payload = {
            "generated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "files": sorted(results, key=lambda r: r["url"]),
        }
        tmp = MAP + ".part"
        json.dump(payload, open(tmp, "w"), ensure_ascii=False, indent=1)
        os.replace(tmp, MAP)

    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        futs = {}
        for u in todo:
            dest = os.path.join(OUT, names[u])
            futs[ex.submit(fetch, u, dest)] = u
        n = 0
        for fut in as_completed(futs):
            u = futs[fut]
            row = fut.result()
            row["filename"] = names[u]
            row["pages"] = pages[u]
            with lock:
                results.append(row)
                n += 1
                if n % 20 == 0 or row["status"] != "ok":
                    persist()
                    ok = sum(1 for r in results if r["status"] == "ok")
                    print(f"progress {n}/{len(todo)} ok={ok} last={row['status']} {row.get('bytes',0)} {names[u]}", flush=True)
    persist()
    from collections import Counter
    c = Counter(r["status"] for r in results)
    total = sum(r.get("bytes") or 0 for r in results if r["status"] == "ok")
    print("DONE", dict(c), "bytes", total, flush=True)


if __name__ == "__main__":
    main()
