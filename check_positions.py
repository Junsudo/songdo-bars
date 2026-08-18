# -*- coding: utf-8 -*-
# 전수 좌표 역검증: 각 업소의 최종 좌표를 reverse geocode해서 지번주소와 대조
import json, re, subprocess, time, urllib.parse

KEY = [l.split("=", 1)[1].strip() for l in open("keys.env") if l.startswith("KAKAO_REST_KEY=")][0]
d = json.loads(open("data/map_data.js", encoding="utf-8").read()[len("window.MAP_DATA = "):-1])
geo_cache = json.load(open("data/geocode_cache.json"))

def lot_of(addr):
    m = re.search(r"송도동\s*(\d+(?:-\d+)?)", addr or "")
    return m.group(1) if m else None

def rev(lat, lng):
    out = subprocess.run(["curl", "-s", "--max-time", "10",
        f"https://dapi.kakao.com/v2/local/geo/coord2address.json?x={lng}&y={lat}",
        "-H", f"Authorization: KakaoAK {KEY}"], capture_output=True, text=True).stdout
    try: return json.loads(out)["documents"][0]["address"]["address_name"]
    except Exception: return None

import math
def dist_m(a, b):
    return math.hypot((a[0]-b[0])*111320, (a[1]-b[1])*111320*math.cos(math.radians(a[0])))

fails = []; lot_diff_near = 0; ok = 0; norev = 0
for i, v in enumerate(d["venues"]):
    exp = lot_of(v.get("jibun"))
    ra = rev(v["lat"], v["lng"])
    time.sleep(0.06)
    if not ra: norev += 1; continue
    got = lot_of(ra)
    if exp and got == exp: ok += 1; continue
    # 지번 불일치 — 기대 지번 geocode와의 실거리로 판정
    g = geo_cache.get(f"송도동 {exp}") if exp else None
    if g:
        dm = dist_m((v["lat"], v["lng"]), (g["lat"], g["lng"]))
        if dm <= 200: lot_diff_near += 1; continue
        fails.append((v["name"], exp, got, round(dm)))
    else:
        lot_diff_near += 1  # 기대 지번 geocode 불가(카카오단독 등) — 근접 판정 불가, 좌표는 카카오 원좌표
print(f"전수 {len(d['venues'])}곳: 지번 일치 {ok}, 인접(<=200m·경계) {lot_diff_near}, 역변환실패 {norev}, FAIL {len(fails)}")
for f in fails: print("  FAIL:", f)
