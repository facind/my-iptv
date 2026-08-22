#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""本地逻辑验证：用模拟上游数据喂给 gen.py 的同款解析/分组/去重/测速流程。"""
import os, re, requests
from concurrent.futures import ThreadPoolExecutor, as_completed

HK_KW=["TVB","ViuTV","HOY","RTHK","翡翠","明珠","J2","开电视","港台","Now","无线"]
HBO_KW=["HBO"]; DISCO_KW=["Discovery","Discov","动物星球","Animal Planet"]
NGC_KW=["Nat Geo","National Geographic","NGC","NatGeoWild"]
TIMEOUT=8

def classify(meta,name,from_news):
    low=(name+meta).lower()
    if any(k.lower() in low for k in HBO_KW): return "HBO"
    if any(k.lower() in low for k in DISCO_KW): return "Discovery"
    if any(k.lower() in low for k in NGC_KW): return "NGC"
    if any(k.lower() in name for k in HK_KW) or "hk" in meta.lower(): return "香港台"
    if from_news: return "新闻"
    return "其他(亚洲)"

def probe(u):
    # 本地 mock：http://alive 视为可达，其余不可达
    return u.startswith("http://alive")

# 模拟上游 m3u 文本（含重复 URL、各组频道、新闻组）
mock1 = """#EXTM3U
#EXTINF:-1 tvg-name="TVB翡翠台" group-title="HK",TVB翡翠台
http://alive/tvb
#EXTINF:-1 tvg-name="HBO Asia" group-title="IN",HBO Asia
http://alive/hbo
#EXTINF:-1 tvg-name="Discovery HD" group-title="DOC",Discovery HD
http://alive/disc
#EXTINF:-1 tvg-name="Nat Geo Wild" group-title="DOC",Nat Geo Wild
http://dead/ngc
#EXTINF:-1 tvg-name="BBC World" group-title="NEWS",BBC World
http://alive/bbc
#EXTINF:-1 tvg-name="ViuTV" group-title="HK",ViuTV
http://alive/viu
"""
# 重复 URL（应被去重）
mock2 = """#EXTM3U
#EXTINF:-1 tvg-name="TVB翡翠台" group-title="HK",TVB翡翠台
http://alive/tvb
#EXTINF:-1 tvg-name="RTHK31" group-title="HK",RTHK31
http://alive/rthk
"""

class C: 
    def __init__(self,t): self.text=t; self.ok=True
def fetch(u,*a,**k): return ""  # 不用

import io, sys
# 直接解析 mock 文本
blocks=[]
seen=set()
for tag,txt in [("cat",mock1),("news",mock2)]:
    from_news = tag=="news"
    lines=txt.splitlines(); i=0
    while i<len(lines):
        if lines[i].startswith("#EXTINF"):
            meta=lines[i]
            m=re.search(r'tvg-name="([^"]*)"',meta)
            name=m.group(1) if m else meta.split(",",1)[-1]
            if i+1<len(lines):
                stream=lines[i+1].strip()
                if stream and not stream.startswith("#") and stream not in seen:
                    seen.add(stream)
                    grp=classify(meta,name,from_news)
                    blocks.append((grp,meta,stream))
                i+=2; continue
        i+=1

print(f"[collect] {len(blocks)} unique before probe")
surv=[]; ex=ThreadPoolExecutor(max_workers=8)
futs={ex.submit(probe,b[2]):b for b in blocks}
for f in as_completed(futs):
    if f.result(): surv.append(futs[f])
order=["香港台","HBO","Discovery","NGC","新闻","其他(亚洲)"]
surv.sort(key=lambda b:order.index(b[0]) if b[0] in order else 99)
out=io.StringIO(); out.write("#EXTM3U\n")
for g,me,s in surv: out.write(me+"\n"+s+"\n")
print("----- my.m3u 内容 -----")
print(out.getvalue())
print(f"[done] 存活 {len(surv)}/{len(blocks)}")
print("分组统计:", {g:sum(1 for b in surv if b[0]==g) for g in order})
