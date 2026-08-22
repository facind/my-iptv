#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
my-iptv gen.py
- 读取 sources.txt 上游清单
- 抓取、解析、按关键字分组(香港台/HBO/Discovery/NGC/新闻/其他)、URL 去重
- 并发测速：超时 8s / 连接错误 / 非 2xx 的链直接丢弃
- 输出 UTF-8 无 BOM 的 my.m3u
"""
import os
import re
import sys
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

HK_KW = ["TVB", "ViuTV", "HOY", "RTHK", "翡翠", "明珠", "J2", "开电视",
         "港台", "Now", "无线"]
HBO_KW = ["HBO"]
DISCO_KW = ["Discovery", "Discov", "动物星球", "Animal Planet"]
NGC_KW = ["Nat Geo", "National Geographic", "NGC", "NatGeoWild"]

TIMEOUT = 8  # 秒


def fetch(url, timeout=15):
    try:
        r = requests.get(url, timeout=timeout,
                         headers={"User-Agent": "Mozilla/5.0"},
                         allow_redirects=True)
        if r.ok:
            return r.content.decode("utf-8-sig", errors="ignore")
    except Exception:
        pass
    return ""


def classify(meta, name, from_news):
    low = (name + meta).lower()
    if any(k.lower() in low for k in HBO_KW):
        return "HBO"
    if any(k.lower() in low for k in DISCO_KW):
        return "Discovery"
    if any(k.lower() in low for k in NGC_KW):
        return "NGC"
    if any(k.lower() in name for k in HK_KW) or "hk" in meta.lower() or 'tvg-country="HK"' in meta:
        return "香港台"
    if from_news:
        return "新闻"
    return "其他(亚洲)"


def probe(stream_url):
    """返回 True 表示链可达(2xx 且未在 TIMEOUT 内超时)。"""
    try:
        # 对 m3u8/hls 用 HEAD 先探，失败再 GET 前 4KB
        r = requests.head(stream_url, timeout=TIMEOUT,
                          headers={"User-Agent": "Mozilla/5.0"},
                          allow_redirects=True)
        if r.ok:
            return True
        # HEAD 被拒(405/403)时退化 GET 少量数据
        r2 = requests.get(stream_url, timeout=TIMEOUT,
                          headers={"User-Agent": "Mozilla/5.0"},
                          allow_redirects=True, stream=True)
        # 读一小段触发超时判定
        next(r2.iter_content(chunk_size=1024), None)
        return r2.ok
    except Exception:
        return False


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    src = os.path.join(here, "sources.txt")
    out = os.path.join(here, "my.m3u")

    urls_upstream = []
    with open(src, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            urls_upstream.append(line)

    seen_url = set()
    blocks = []  # (group, extinf_raw, stream_url)

    for u in urls_upstream:
        txt = fetch(u)
        if not txt:
            print(f"[skip] empty/fail: {u}")
            continue
        from_news = "categories/news" in u or "news.m3u" in u
        lines = txt.splitlines()
        i = 0
        while i < len(lines):
            if lines[i].startswith("#EXTINF"):
                meta = lines[i]
                m = re.search(r'tvg-name="([^"]*)"', meta)
                if m:
                    name = m.group(1)
                else:
                    name = meta.split(",", 1)[-1] if "," in meta else meta
                if i + 1 < len(lines):
                    stream = lines[i + 1].strip()
                    if stream and not stream.startswith("#"):
                        if stream not in seen_url:
                            seen_url.add(stream)
                            grp = classify(meta, name, from_news)
                            meta_new = re.sub(r'group-title="[^"]*"',
                                              f'group-title="{grp}"', meta)
                            if 'group-title="' not in meta_new:
                                meta_new = meta_new.rstrip() + f' group-title="{grp}"'
                            blocks.append((grp, meta_new, stream))
                        i += 2
                        continue
            i += 1

    print(f"[collect] {len(blocks)} unique channels before probe")

    # 并发测速，超时 8s 的丢
    survivers = []
    with ThreadPoolExecutor(max_workers=20) as ex:
        futs = {ex.submit(probe, b[2]): b for b in blocks}
        done = 0
        for fut in as_completed(futs):
            done += 1
            b = futs[fut]
            ok = fut.result()
            if ok:
                survivers.append(b)
            if done % 50 == 0:
                print(f"[probe] {done}/{len(blocks)} checked")
    print(f"[probe] alive {len(survivers)} / {len(blocks)}")

    order = ["香港台", "HBO", "Discovery", "NGC", "新闻", "其他(亚洲)"]
    survivers.sort(key=lambda b: order.index(b[0]) if b[0] in order else 99)

    with open(out, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for grp, meta, stream in survivers:
            f.write(meta + "\n")
            f.write(stream + "\n")

    print(f"[done] {len(survivers)} channels -> my.m3u")


if __name__ == "__main__":
    main()
