# -*- coding: utf-8 -*-
# 네이버 블로그 검색에서 좌석수·단체 인원 언급 추출 ("90석", "단체 50명 가능" 등) — 주장 수준 데이터로 표기
import json, re, subprocess, time, unicodedata, urllib.parse

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
PREFIX = "window.MAP_DATA = "
data = json.loads(open("data/map_data.js", encoding="utf-8").read()[len(PREFIX):-1])

try: cache = json.load(open("data/seats_cache.json"))
except Exception: cache = {}

SEAT = re.compile(r"(\d{2,3})\s*석")
GROUP = re.compile(r"단체\s*(\d{2,3})\s*[명인]")

def crawl(name):
    q = urllib.parse.quote(re.sub(r"\(.*?\)", "", name).strip() + " 송도")
    url = f"https://search.naver.com/search.naver?ssc=tab.blog.all&query={q}"
    out = subprocess.run(["/usr/bin/curl", "-s", "--max-time", "12", url,
                          "-A", UA, "-H", "Accept-Language: ko-KR,ko;q=0.9"],
                         capture_output=True, text=True).stdout
    if not out or len(out) < 5000:
        return None  # 차단/실패
    seats = [int(m) for m in SEAT.findall(out) if 20 <= int(m) <= 400]
    groups = [int(m) for m in GROUP.findall(out) if 10 <= int(m) <= 300]
    return {"seat_max": max(seats) if seats else None, "seat_n": len(seats),
            "group_max": max(groups) if groups else None}

def norm(s):
    s = unicodedata.normalize("NFKC", str(s or "")).lower()
    return re.sub(r"[^0-9a-z가-힣]", "", s)

done = blocked = 0
for v in data["venues"]:
    key = norm(v["name"])
    if key not in cache:
        rec = crawl(v["name"])
        if rec is None:
            blocked += 1
            if blocked > 15:
                print("차단 의심 — 중단(캐시 저장, 재실행 시 이어감)"); break
            time.sleep(1.5); continue
        cache[key] = rec; done += 1
        if done % 40 == 0:
            json.dump(cache, open("data/seats_cache.json", "w"))
            print(f"{done}건 수집…")
        time.sleep(0.35)
    rec = cache.get(key) or {}
    v["seat_blog"] = rec.get("seat_max")
    v["group_blog"] = rec.get("group_max")

json.dump(cache, open("data/seats_cache.json", "w"))
open("data/map_data.js", "w", encoding="utf-8").write(PREFIX + json.dumps(data, ensure_ascii=False) + ";")
n = sum(1 for v in data["venues"] if v.get("seat_blog"))
g = sum(1 for v in data["venues"] if v.get("group_blog"))
print(f"좌석 언급 확보 {n}곳, 단체 인원 언급 {g}곳 (신규 조회 {done}, 실패 {blocked})")
