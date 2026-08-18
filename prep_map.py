# -*- coding: utf-8 -*-
# 지도용 데이터 생성: data/map_data.js (window.MAP_DATA)
# 좌표 우선순위: 카카오 매칭 실좌표 > 다이닝코드 실좌표 > 카카오 주소 geocoding
import csv, json, re, subprocess, time, unicodedata, urllib.parse
from collections import defaultdict

DATA = "data"
KEY = [l.split("=", 1)[1].strip() for l in open("keys.env") if l.startswith("KAKAO_REST_KEY=")][0]
PUB_TYPES = {"호프/통닭", "감성주점", "정종/대포집/소주방"}
IGC = {"lat": 37.3760532112935, "lng": 126.667676508026}  # 카카오 실측(인천글로벌캠퍼스, 송도동 187)

def norm(s):
    if not s: return ""
    s = unicodedata.normalize("NFKC", str(s)).lower()
    s = re.sub(r"\(주\)|주식회사|㈜", "", s)
    return re.sub(r"[^0-9a-z가-힣]", "", s)

def base_name(s):
    n = norm(s)
    n = re.sub(r"(인천)?(송도)?(국제도시|타임스페이스|트리플스트리트|커낼워크|센트럴파크|워터프런트|스마트스퀘어|롯데몰|캠퍼스타운역?)?(\d공구)?점$", "", n)
    return n or norm(s)

def lot_of(addr):
    m = re.search(r"송도동\s*(\d+(?:-\d+)?)", addr or "")
    return m.group(1) if m else None

rows = list(csv.DictReader(open(f"{DATA}/yeonsu_restaurants.csv", encoding="utf-8")))
songdo = [r for r in rows if r["영업상태명"] == "영업/정상" and "송도동" in (r["지번주소"] or "")]
closed = [r for r in rows if r["영업상태명"] == "폐업" and "송도동" in (r["지번주소"] or "")]

def area_of(r):
    try: return float(r["소재지면적"])
    except (ValueError, TypeError): return 0.0

by_name = defaultdict(list); by_base = defaultdict(list); by_lot = defaultdict(list)
for r in songdo:
    by_name[norm(r["사업장명"])].append(r)
    by_base[base_name(r["사업장명"])].append(r)
    lot = lot_of(r["지번주소"])
    if lot: by_lot[lot].append(r)

def match(nm, branch, addr):
    full = norm(nm + (branch or "")); n = norm(nm); bn = base_name(nm)
    for key, table in ((full, by_name), (n, by_name), (bn, by_base)):
        if key and table.get(key): return max(table[key], key=area_of)
    lot = lot_of(addr or "")
    if lot:
        for r in by_lot.get(lot, []):
            rb = base_name(r["사업장명"])
            if bn and rb and len(bn) >= 2 and (bn in rb or rb in bn): return r
    return None

# 폐업 대장 인덱스 — 미매칭 항목의 유령(폐업) 제거용
closed_by_name = {norm(r["사업장명"]) for r in closed}
closed_by_lot = defaultdict(list)
for r in closed:
    lot = lot_of(r["지번주소"])
    if lot: closed_by_lot[lot].append(r)

def is_closed(nm, addr):
    n = norm(nm); bn = base_name(nm)
    if n in closed_by_name: return True
    lot = lot_of(addr or "")
    if lot:
        for r in closed_by_lot.get(lot, []):
            rb = base_name(r["사업장명"])
            if bn and rb and len(bn) >= 2 and (bn in rb or rb in bn): return True
    return False

dc = json.load(open(f"{DATA}/diningcode_all.json"))
kakao = json.load(open(f"{DATA}/kakao_bars.json"))

lic_dc = {}; lic_kakao = {}
dc_unmatched = []; kakao_unmatched = []
for poi in dc:
    r = match(poi["nm"], poi.get("branch"), poi.get("addr") or poi.get("road_addr"))
    if r: lic_dc.setdefault(r["관리번호"], poi)
    else: dc_unmatched.append(poi)
for kp in kakao:
    r = match(kp["place_name"], "", kp.get("address_name"))
    if r: lic_kakao.setdefault(r["관리번호"], kp)
    else: kakao_unmatched.append(kp)

# ── 카테고리 분류 ──────────────────────────────────────────
def classify(uptae, kakao_leaf, dc_cat, big_nonpub):
    t = " ".join(x for x in [uptae or "", kakao_leaf or "", dc_cat or ""] if x)
    if big_nonpub: return "회식형 대형"
    if re.search(r"일본식주점|이자카야|사케", t): return "이자카야"
    if re.search(r"칵테일|와인|위스키|재즈|라운지|바$|하이볼|LP", t): return "바·라운지"
    if re.search(r"포장마차|포차|대포집|소주방|오뎅", t): return "포차·주점"
    if re.search(r"호프|맥주|펍|치킨|브루|비어", t): return "호프·펍"
    if re.search(r"감성주점|술집", t): return "포차·주점"
    return "포차·주점"

def geocode(jibun):
    m = re.search(r"(송도동\s*\d+(?:-\d+)?)", jibun or "")
    if not m: return None
    q = urllib.parse.quote(f"인천 연수구 {m.group(1)}")
    out = subprocess.run(["curl", "-s", "--max-time", "10",
                          f"https://dapi.kakao.com/v2/local/search/address.json?query={q}",
                          "-H", f"Authorization: KakaoAK {KEY}"], capture_output=True, text=True).stdout
    try:
        docs = json.loads(out)["documents"]
        if docs: return {"lat": float(docs[0]["y"]), "lng": float(docs[0]["x"])}
    except Exception: pass
    return None

venues = {}; geocoded = 0
pubs = [r for r in songdo if r["업태구분명"] in PUB_TYPES]
big = [r for r in songdo if (r["업태구분명"] in PUB_TYPES or r["관리번호"] in lic_dc or r["관리번호"] in lic_kakao) and area_of(r) >= 200]
for r in {id(x): x for x in pubs + big}.values():
    mid = r["관리번호"]
    kp = lic_kakao.get(mid); dp = lic_dc.get(mid)
    if kp: coords = {"lat": float(kp["y"]), "lng": float(kp["x"])}; src = "kakao"
    else:
        coords = geocode(r["지번주소"]); src = "geocode"; geocoded += 1
        time.sleep(0.08)
    if not coords: continue
    leaf = (kp.get("category_name", "").split(" > ")[-1] if kp else "")
    big_nonpub = r["업태구분명"] not in PUB_TYPES and area_of(r) >= 200 and not re.search(r"호프|주점|펍|바|맥주", (leaf or "") + (dp.get("category", "") if dp else ""))
    venues[f"lic:{mid}"] = {
        "name": r["사업장명"], "cat": classify(r["업태구분명"], leaf, "", big_nonpub),
        "uptae": r["업태구분명"], "area": area_of(r) or None,
        "phone": r["전화번호"] or (kp.get("phone") if kp else "") or "",
        "road": r["도로명주소"] or "", "jibun": r["지번주소"] or "",
        "licensed": True, "multi_use": (r["다중이용업소여부"] or "").strip() == "Y",
        "kakao_url": kp.get("place_url") if kp else "", "coord_src": src, **coords,
    }
dropped = []
for kp in kakao_unmatched:
    if is_closed(kp["place_name"], kp.get("address_name")):
        dropped.append("kakao:" + kp["place_name"]); continue
    leaf = kp.get("category_name", "").split(" > ")[-1]
    venues[f"kko:{kp['id']}"] = {
        "name": kp["place_name"], "cat": classify("", leaf, "", False), "uptae": "",
        "area": None, "phone": kp.get("phone") or "", "road": kp.get("road_address_name") or "",
        "jibun": kp.get("address_name") or "", "licensed": False, "multi_use": False,
        "kakao_url": kp.get("place_url") or "",
        "coord_src": "kakao", "lat": float(kp["y"]), "lng": float(kp["x"]),
    }
out = {"generated": "2026-08-18", "igc": IGC, "venues": list(venues.values())}
open(f"{DATA}/map_data.js", "w", encoding="utf-8").write("window.MAP_DATA = " + json.dumps(out, ensure_ascii=False) + ";")
from collections import Counter
print(f"venues: {len(venues)} (geocoded {geocoded})")
print(Counter(v["cat"] for v in venues.values()).most_common())
print("licensed:", sum(1 for v in venues.values() if v["licensed"]), "/ unmatched:", sum(1 for v in venues.values() if not v["licensed"]))
print(f"폐업 대장 매칭으로 제거: {len(dropped)}곳")
for d in dropped: print("  -", d)
