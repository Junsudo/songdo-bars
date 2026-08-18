# -*- coding: utf-8 -*-
# 상호 매칭 감사: 카카오 POI ↔ 인허가 쌍의 주소지(지번) 대조
import csv, json, re, unicodedata
from collections import defaultdict

DATA = "data"
PUB_TYPES = {"호프/통닭", "감성주점", "정종/대포집/소주방"}

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

def area_of(r):
    try: return float(r["소재지면적"])
    except (ValueError, TypeError): return 0.0

by_name = defaultdict(list); by_base = defaultdict(list); by_lot = defaultdict(list)
for r in songdo:
    by_name[norm(r["사업장명"])].append(r)
    by_base[base_name(r["사업장명"])].append(r)
    lot = lot_of(r["지번주소"])
    if lot: by_lot[lot].append(r)

ALIAS = {"또봉이통닭 인천송도AIT센터점": "브루엠"}

def match(nm, addr):
    if nm in ALIAS:
        c = by_name.get(norm(ALIAS[nm]))
        if c: return max(c, key=area_of), "alias"
    n = norm(nm); bn = base_name(nm)
    plot = lot_of(addr or "")
    if plot:
        same = [r for r in by_lot.get(plot, [])
                if bn and len(bn) >= 2 and (bn in base_name(r["사업장명"]) or base_name(r["사업장명"]) in bn)]
        if same: return max(same, key=area_of), "지번+이름"
    cands = by_name.get(n)
    if cands:
        if plot and len(cands) > 1:
            s2 = [r for r in cands if lot_of(r["지번주소"]) == plot]
            if s2: cands = s2
        return max(cands, key=area_of), "이름정확"
    cands = by_base.get(bn) if bn else None
    if cands:
        if plot:
            s2 = [r for r in cands if lot_of(r["지번주소"]) == plot]
            if s2: return max(s2, key=area_of), "기본이름"
            if all(lot_of(r["지번주소"]) for r in cands): return None, None
        return max(cands, key=area_of), "기본이름"
    return None, None

kakao = json.load(open(f"{DATA}/kakao_bars.json"))
fd6 = json.load(open(f"{DATA}/kakao_fd6_all.json"))
kchick = [x for x in fd6 if "음식점 > 치킨" in x["category_name"] and "송도동" in (x.get("address_name") or "")]
geo = json.load(open(f"{DATA}/geocode_cache.json"))

import math
def dist_lot(klat, klng, llot):
    g = geo.get(f"송도동 {llot}")
    if not g: return None
    return math.hypot((klat - g["lat"]) * 111320, (klng - g["lng"]) * 111320 * math.cos(math.radians(g["lat"])))

ok = 0; pairs = []
for x in kakao + kchick:
    r, how = match(x["place_name"], x.get("address_name"))
    if not r: continue
    klot = lot_of(x.get("address_name")); llot = lot_of(r["지번주소"])
    if klot and llot and klot == llot:
        ok += 1; continue
    dm = dist_lot(float(x["y"]), float(x["x"]), llot) if llot else None
    exact_name = norm(x["place_name"]) == norm(r["사업장명"])
    pairs.append((x["place_name"], klot, r["사업장명"], llot, how,
                  round(dm) if dm is not None else -1, exact_name))

print(f"매칭 쌍 전수: 지번 일치 {ok}, 지번 불일치 {len(pairs)}")
print("\n-- 지번 불일치 상세 (카카오상호 | 카카오지번 | 인허가상호 | 인허가지번 | 매칭방법 | 거리m | 상호동일) --")
for p in sorted(pairs, key=lambda p: -p[5]):
    print(f"  {'⚠️' if p[5] > 200 or not p[6] else '·'} {p[0]} | {p[1]} | {p[2]} | {p[3]} | {p[4]} | {p[5]}m | {'동일' if p[6] else '상이'}")
