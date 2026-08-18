# -*- coding: utf-8 -*-
# Kakao Local API — 송도 FD6(음식점) 전수 수집 (quadtree 타일링, 쿼리당 45건 상한 우회)
import json, time, subprocess, urllib.parse

KEY = [l.split("=", 1)[1].strip() for l in open("keys.env") if l.startswith("KAKAO_REST_KEY=")][0]
BASE = "https://dapi.kakao.com/v2/local/search/category.json"
BBOX = (126.585, 37.355, 126.695, 37.425)  # lng1, lat1, lng2, lat2 — 송도동 여유 포함
MIN_SPAN = 0.0015
calls = 0

def api(params):
    global calls
    calls += 1
    url = BASE + "?" + urllib.parse.urlencode(params)
    out = subprocess.run(["curl", "-s", "--max-time", "15", url, "-H", f"Authorization: KakaoAK {KEY}"],
                         capture_output=True, text=True).stdout
    return json.loads(out)

def fetch_tile(x1, y1, x2, y2, places):
    rect = f"{x1},{y1},{x2},{y2}"
    d = api({"category_group_code": "FD6", "rect": rect, "size": 15, "page": 1})
    total = d["meta"]["total_count"]
    if total == 0:
        return
    if total > 45 and (x2 - x1) > MIN_SPAN and (y2 - y1) > MIN_SPAN:
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        for bx in ((x1, y1, mx, my), (mx, y1, x2, my), (x1, my, mx, y2), (mx, my, x2, y2)):
            fetch_tile(*bx, places)
            time.sleep(0.12)
        return
    for x in d["documents"]:
        places[x["id"]] = x
    page = 2
    while not d["meta"]["is_end"] and page <= 3:
        d = api({"category_group_code": "FD6", "rect": rect, "size": 15, "page": page})
        for x in d["documents"]:
            places[x["id"]] = x
        page += 1
        time.sleep(0.12)

places = {}
fetch_tile(*BBOX, places)
bars = [x for x in places.values() if "술집" in x["category_name"]]
songdo_bars = [x for x in bars if "송도동" in (x.get("address_name") or "")]
print(f"API 호출 {calls}회, FD6 전체 {len(places)}, 술집 {len(bars)}, 송도동 술집 {len(songdo_bars)}")
json.dump(list(places.values()), open("data/kakao_fd6_all.json", "w"), ensure_ascii=False)
json.dump(songdo_bars, open("data/kakao_bars.json", "w"), ensure_ascii=False)
from collections import Counter
print(Counter(x["category_name"].split(" > ")[2] if len(x["category_name"].split(" > ")) > 2 else "술집(기타)" for x in songdo_bars).most_common())
