#!/usr/bin/env python3
"""Fetch one Ozon entrypoint page and write a truncated decoded dump.

Usage:
  PYTHONPATH=src python3 audit/_fetch.py <pagetype> <path> [k=v ...]

Only GET via entrypoint-api. Never POSTs.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from ozon_client import OzonClient
from ozon_client.catalog import _decode, _page_url

OUT = Path(__file__).resolve().parent / "raw"
OUT.mkdir(parents=True, exist_ok=True)

STR_LIM = 220
LIST_KEEP = 2
DEPTH = 7


def trunc(node, depth=0):
    if depth > DEPTH:
        if isinstance(node, dict):
            return {"_keys": list(node.keys())[:40], "_depth": "cut"}
        if isinstance(node, list):
            return {"_len": len(node), "_depth": "cut"}
        if isinstance(node, str) and len(node) > STR_LIM:
            return node[:STR_LIM] + f"…<{len(node)}>"
        return node
    if isinstance(node, str):
        return node if len(node) <= STR_LIM else node[:STR_LIM] + f"…<{len(node)}>"
    if isinstance(node, list):
        if len(node) <= LIST_KEEP:
            return [trunc(x, depth + 1) for x in node]
        return {
            "_len": len(node),
            "_head": [trunc(x, depth + 1) for x in node[:LIST_KEEP]],
        }
    if isinstance(node, dict):
        return {str(k): trunc(v, depth + 1) for k, v in node.items()}
    return node


def family(key: str) -> str:
    # tileGridDesktop-123-default-1 -> tileGridDesktop
    return re.sub(r"-\d+-default-\d+$", "", key)


def summarize_widget(obj):
    if isinstance(obj, dict):
        fields = {}
        for k, v in obj.items():
            if isinstance(v, list):
                fields[k] = f"list[{len(v)}]"
            elif isinstance(v, dict):
                fields[k] = f"dict{{{','.join(list(v.keys())[:12])}}}"
            elif isinstance(v, str):
                fields[k] = f"str[{len(v)}]"
            else:
                fields[k] = type(v).__name__
        return {"type": "dict", "fields": fields}
    if isinstance(obj, list):
        return {"type": "list", "len": len(obj)}
    return {"type": type(obj).__name__}


def collect_links(node, out: set, depth=0):
    if depth > 10:
        return
    if isinstance(node, dict):
        for k, v in node.items():
            if k in ("link", "url", "href", "deeplink") and isinstance(v, str):
                if v.startswith("/") and not v.startswith("//"):
                    out.add(v.split("#")[0])
            else:
                collect_links(v, out, depth + 1)
    elif isinstance(node, list):
        for v in node[:80]:
            collect_links(v, out, depth + 1)


def main():
    if len(sys.argv) < 3:
        print("usage: _fetch.py pagetype path [k=v ...]", file=sys.stderr)
        sys.exit(2)
    pagetype, path = sys.argv[1], sys.argv[2]
    params = {}
    for a in sys.argv[3:]:
        k, _, v = a.partition("=")
        params[k] = v
    c = OzonClient()
    try:
        env = _page_url(c, path, **params)
    finally:
        c.close()
    if not isinstance(env, dict):
        print("NOT_OBJECT", type(env), str(env)[:200])
        sys.exit(1)
    ws = env.get("widgetStates") or {}
    decoded = {}
    summary = []
    links = set()
    if isinstance(ws, dict):
        for key, raw in ws.items():
            obj = _decode(raw)
            decoded[key] = obj
            summary.append({
                "key": key,
                "family": family(str(key)),
                "shape": summarize_widget(obj),
            })
            collect_links(obj, links)
    # also scan other envelope fields for links (layout often has them)
    for k, v in env.items():
        if k != "widgetStates":
            collect_links(v, links)
    dump = {
        "pagetype": pagetype,
        "path": path,
        "params": params,
        "envelope_keys": list(env.keys()),
        "seo": trunc(env.get("seo")),
        "pageInfo": trunc(env.get("pageInfo")),
        "location": trunc(env.get("location")),
        "layout": trunc(env.get("layout")),
        "shared": trunc(env.get("shared")) if "shared" in env else None,
        "nextPage": env.get("nextPage"),
        "prevPage": env.get("prevPage"),
        "widget_families": sorted({s["family"] for s in summary}),
        "widget_summary": summary,
        "widgetStates": {k: trunc(v) for k, v in decoded.items()},
        "discovered_links": sorted(links)[:400],
    }
    # drop Nones
    dest = OUT / f"{pagetype}.json"
    dest.write_text(json.dumps(dump, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {dest} bytes={dest.stat().st_size} widgets={len(summary)} links={len(links)}")
    print("envelope", dump["envelope_keys"])
    print("families:")
    for f in dump["widget_families"]:
        print(" ", f)
    print("---links sample---")
    for L in sorted(links):
        if any(x in L for x in ("/brand", "/seller", "/highlight", "/promo", "/category",
                                "/product", "/reviews", "/questions", "/cart", "/my/",
                                "/search", "/info", "/help", "/context", "/tab")):
            print(L[:220])


if __name__ == "__main__":
    main()
