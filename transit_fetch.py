# -*- coding: utf-8 -*-
# 교통 오버레이 데이터: 인천1호선 선형(OSM) + 역(카카오 SW8) + 순환42 대표 정류장(공식 노선도 SVG 판독분 지오코딩)
import json, subprocess, urllib.parse, time

KEY = [l.split("=", 1)[1].strip() for l in open("keys.env") if l.startswith("KAKAO_REST_KEY=")][0]

def kakao(url):
    out = subprocess.run(["/usr/bin/curl", "-s", "--max-time", "10", url, "-H", f"Authorization: KakaoAK {KEY}"],
                         capture_output=True, text=True).stdout
    try: return json.loads(out)
    except Exception: return {}

# 1) 지하철역 (송도 구간, 카카오 SW8)
sw = kakao("https://dapi.kakao.com/v2/local/search/category.json?category_group_code=SW8&rect=126.60,37.36,126.70,37.43&size=15")
stations = []
for x in sw.get("documents", []):
    nm = x["place_name"]
    if "인천1호선" in nm or "인천 1호선" in nm:
        stations.append({"name": nm.split(" ")[0], "lat": float(x["y"]), "lng": float(x["x"])})
print("지하철역:", [s["name"] for s in stations])

# 2) 노선 선형 (OSM subway ways)
osm = json.load(open("data/osm_subway.json"))
segs = []
for w in osm.get("elements", []):
    if w.get("type") == "way" and w.get("geometry"):
        segs.append([[p["lat"], p["lon"]] for p in w["geometry"]])
print("선형 세그먼트:", len(segs))

# 3) 순환42 대표 정류장 (공식 노선도 SVG 판독, 노선 순서) — 카카오 키워드 지오코딩
STOPS = ["셀트리온", "랜드마크시티 센트럴더샵 203동", "송도SK뷰 105동", "e편한세상 송도 109동",
         "달빛축제공원 대공연장", "힐스테이트레이크 송도", "신정중학교", "송도풍림아이원 2단지",
         "현송중학교", "신송고등학교", "인천대입구역", "캠퍼스타운역", "예송중학교", "연세대학교 국제캠퍼스",
         "지식정보단지역", "겐트대학교 글로벌캠퍼스", "송도공영차고지", "극지연구소"]
bus = []
for s in STOPS:
    q = urllib.parse.quote(f"송도 {s}")
    d = kakao(f"https://dapi.kakao.com/v2/local/search/keyword.json?query={q}&x=126.65&y=37.39&radius=9000&size=3&sort=distance")
    docs = d.get("documents", [])
    if docs:
        x = docs[0]
        bus.append({"name": s, "lat": float(x["y"]), "lng": float(x["x"])})
    else:
        print("  !미해결:", s)
    time.sleep(0.1)
print(f"순환42 정류장 지오코딩: {len(bus)}/{len(STOPS)}")

out = {"line1": segs, "stations": stations, "bus42": bus}
open("data/transit.js", "w", encoding="utf-8").write("window.TRANSIT = " + json.dumps(out, ensure_ascii=False) + ";")
print("data/transit.js 저장")
