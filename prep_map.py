# -*- coding: utf-8 -*-
# 지도용 데이터 생성: data/map_data.js (window.MAP_DATA)
# 좌표 우선순위: 카카오 매칭 실좌표 > 다이닝코드 실좌표 > 카카오 주소 geocoding
import csv, json, re, subprocess, time, unicodedata, urllib.parse
from collections import defaultdict

DATA = "data"
KEY = [l.split("=", 1)[1].strip() for l in open("keys.env") if l.startswith("KAKAO_REST_KEY=")][0]
PUB_TYPES = {"호프/통닭", "정종/대포집/소주방"}
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

ALIAS = {"또봉이통닭 인천송도AIT센터점": "브루엠",
         "10.19갤러리&라운지": "10.19 Gallery&Lounge(10.19 갤러리 앤 라운지)",
         "펀비어킹 인천 송도마리나베이점": "펀비어킹 송도마리나베이점"}  # 카카오 상호 → 인허가 사업장명 (실사 확인분)
name_override = {}

def match(nm, branch, addr):
    if nm in ALIAS:
        c = by_name.get(norm(ALIAS[nm]))
        if c:
            r = max(c, key=area_of); name_override[r["관리번호"]] = nm; return r
    full = norm(nm + (branch or "")); n = norm(nm); bn = base_name(nm)
    plot = lot_of(addr or "")
    # 1) 같은 지번 + 이름 포함관계 — 가장 강한 근거 (비비큐(BBQ) 병기, 프런트/프론트 표기차 등 흡수)
    if plot:
        same = [r for r in by_lot.get(plot, [])
                if bn and len(bn) >= 2 and (bn in base_name(r["사업장명"]) or base_name(r["사업장명"]) in bn)]
        if same: return max(same, key=area_of)
    # 2) 상호 정확 일치 (동명 다지점이면 같은 지번 우선)
    for key in (full, n):
        cands = by_name.get(key)
        if not cands: continue
        if plot and len(cands) > 1:
            s2 = [r for r in cands if lot_of(r["지번주소"]) == plot]
            if s2: cands = s2
        return max(cands, key=area_of)
    # 3) 지점 접미사 제거 이름 — 지번이 전부 다른 걸로 확인되면 오지점 방지 위해 매칭 포기
    cands = by_base.get(bn) if bn else None
    if cands:
        if plot:
            s2 = [r for r in cands if lot_of(r["지번주소"]) == plot]
            if s2: return max(s2, key=area_of)
            if all(lot_of(r["지번주소"]) for r in cands): return None
        return max(cands, key=area_of)
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
kakao = [x for x in json.load(open(f"{DATA}/kakao_bars.json")) if not re.search(r"나이트|클럽", x["category_name"])]

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

# 더신더 케이스 보강: 비주점 업태(까페·기타·일식 등)로 등록된 진성 바 — 확인된 것만 명시 포함
EXTRA_POI_NAMES = set()  # 소형 바·라운지류 임의 추가분 전면 철회 (유저 지시)
EXTRA_LIC_NORMS = {norm(x) for x in ["앨리스피맥 송도아트포레점", "앨리스피맥", "크라운호프 송도점"]}  # 피맥·호프만 유지
EXTRA_DROP_LOTS = {("앨리스피맥", "30-2")}
try: ce7 = json.load(open(f"{DATA}/kakao_ce7.json"))
except Exception: ce7 = []
_have = {k["id"] for k in kakao}
for x in json.load(open(f"{DATA}/kakao_fd6_all.json")) + ce7:
    if x["place_name"] in EXTRA_POI_NAMES and x["id"] not in _have and "송도동" in (x.get("address_name") or ""):
        r = match(x["place_name"], "", x.get("address_name"))
        if r: lic_kakao.setdefault(r["관리번호"], x)
        else: kakao_unmatched.append(x)

# 카카오 '치킨' 카테고리 — 인허가 면적 100㎡ 이상이면 포함, KAKAO_FORCE 상호는 미매칭이어도 포함
fd6 = json.load(open(f"{DATA}/kakao_fd6_all.json"))
kchick = [x for x in fd6 if "음식점 > 치킨" in x["category_name"] and "송도동" in (x.get("address_name") or "")]
KAKAO_FORCE = ["또봉이"]
chick_added = forced = 0
for x in kchick:
    r = match(x["place_name"], "", x.get("address_name"))
    if r:
        if r["업태구분명"] in PUB_TYPES or area_of(r) >= 100:
            lic_kakao.setdefault(r["관리번호"], x); chick_added += 1
    elif any(f in x["place_name"] for f in KAKAO_FORCE) and not is_closed(x["place_name"], x.get("address_name")):
        kakao_unmatched.append(x); forced += 1
print(f"치킨 카테고리: 기준 통과 {chick_added}, 지정 포함 {forced} (전체 {len(kchick)})")

# ── 카테고리 분류 ──────────────────────────────────────────
def classify(uptae, kakao_leaf, dc_cat, big_nonpub):
    t = " ".join(x for x in [uptae or "", kakao_leaf or "", dc_cat or ""] if x)
    if big_nonpub: return "대형(200㎡+)"
    if re.search(r"일본식주점|이자카야|사케", t): return "이자카야"
    if re.search(r"칵테일|와인|위스키|재즈|라운지|바$|하이볼|LP", t): return "바·라운지"
    if re.search(r"포장마차|포차|대포집|소주방|오뎅", t): return "포차·주점"
    if re.search(r"호프|맥주|펍|치킨|통닭|브루|비어", t): return "호프·펍"
    if re.search(r"감성주점|술집", t): return "포차·주점"
    return "포차·주점"

try: _geo_cache = json.load(open(f"{DATA}/geocode_cache.json"))
except Exception: _geo_cache = {}

def geocode(jibun):
    m = re.search(r"(송도동\s*\d+(?:-\d+)?)", jibun or "")
    if not m: return None
    ck = m.group(1)
    if ck in _geo_cache: return dict(_geo_cache[ck]) if _geo_cache[ck] else None
    q = urllib.parse.quote(f"인천 연수구 {m.group(1)}")
    out = subprocess.run(["curl", "-s", "--max-time", "10",
                          f"https://dapi.kakao.com/v2/local/search/address.json?query={q}",
                          "-H", f"Authorization: KakaoAK {KEY}"], capture_output=True, text=True).stdout
    res = None
    try:
        docs = json.loads(out)["documents"]
        if docs: res = {"lat": float(docs[0]["y"]), "lng": float(docs[0]["x"])}
    except Exception: pass
    _geo_cache[ck] = res
    return res

EXCLUDE_NAMES = {"제우스볼펍", "헌팅",
    # 유저가 지시한 영구 제외 상호 (재유입 차단 — naver_cat 패턴 의존 금지)
    "바삭메밀뜰", "투플러스푸드", "다복이네", "봄설", "수제청국", "드림에프앤씨", "이터스", "동남집",
    "용호동낙지", "으뜸착한낙지", "송쭈집", "수블라키아", "엉클인더키친", "밥상편지", "블루오션한식",
    "주가코다리", "몰트하우스", "랍스터퍼블릭", "와인기대", "파르크드와인", "제이라운지", "1019", "데이롱",
    "튜나펍", "쎄시봉", "쉐이크쉑", "다올앤펍", "스월링라운지", "스낵얌"}
EXCLUDE_EXACT = {norm(x) for x in ["엘", "한일도", "대양주", "kmgm 송도신도시점", "케이엠지엠(KMGM) 송도신도시점"]}  # 개별 제외 (유저 지시, 정확 일치 — '엘'이 더샵엘테라스 등 오폭 방지)
def excluded_name(nm): return any(x in norm(nm) for x in EXCLUDE_NAMES) or norm(nm) in EXCLUDE_EXACT
venues = {}; geocoded = 0; coord_fixes = []
EXCLUDE_UPTAE = {"경양식", "식육(숯불구이)", "분식", "중국식", "뷔페식", "감성주점", "라이브카페",
                 "외국음식전문점(인도,태국등)", "탕류(보신용)", "패밀리레스트랑", "냉면집", "출장조리"}  # CRITERIA.md Exclude 표와 1:1 동기화
pubs = [r for r in songdo if r["업태구분명"] in PUB_TYPES]
kakao_bars_lic = [r for r in songdo if r["관리번호"] in lic_kakao and r["업태구분명"] != "감성주점"]  # 카카오 분류 우선. 단 감성주점(춤 허용=헌팅포차 프록시)만은 카카오 분류와 무관하게 제외 유지
extra_lic = [r for r in songdo if norm(r["사업장명"]) in EXTRA_LIC_NORMS
             and (norm(r["사업장명"]), lot_of(r["지번주소"])) not in EXTRA_DROP_LOTS]  # 명시 목록은 업태 제외보다 우선
# 호텔 내 업소 제외 (유저 지시)
HOTEL_RE = re.compile(r"호텔|쉐라톤|오라카이|홀리데이인|오크우드")
HOTEL_LOTS = {"6-9", "38", "93-1", "33-1", "6-10", "10-2"}
def in_hotel(name, addr):
    return bool(HOTEL_RE.search((name or "") + " " + (addr or ""))) or lot_of(addr) in HOTEL_LOTS

for r in {id(x): x for x in pubs + kakao_bars_lic + extra_lic}.values():
    if excluded_name(r["사업장명"]): continue
    if in_hotel(r["사업장명"], r["지번주소"]): continue
    mid = r["관리번호"]
    kp = lic_kakao.get(mid); dp = lic_dc.get(mid)
    if kp: coords = {"lat": float(kp["y"]), "lng": float(kp["x"])}; src = "kakao"
    else:
        coords = geocode(r["지번주소"]); src = "geocode"; geocoded += 1
        time.sleep(0.08)
    if not coords: continue
    if src == "kakao":
        klot = lot_of(kp.get("address_name")); llot = lot_of(r["지번주소"])
        if klot and llot and klot == llot:
            pass  # 같은 지번 확인 — 대형 필지에서 중심점과 멀어도 카카오 매장 좌표가 실위치
        elif norm(kp["place_name"]) == norm(r["사업장명"]):
            coord_fixes.append(f"{r['사업장명']}: 지번 상이({klot}≠{llot})지만 상호 정확 일치 — 카카오 실좌표 유지")
        else:
            g = geocode(r["지번주소"])
            if g:
                import math
                dm = math.hypot((coords["lat"] - g["lat"]) * 111320,
                                (coords["lng"] - g["lng"]) * 111320 * math.cos(math.radians(g["lat"])))
                if dm > 200:
                    coord_fixes.append(f"{r['사업장명']}: 지번 불일치({klot}≠{llot}) + {dm:.0f}m 이탈 → 오지점 판정, 지번 좌표로 보정·카카오 연결 해제")
                    coords = g; src = "geocode(보정)"; kp = None
    leaf = (kp.get("category_name", "").split(" > ")[-1] if kp else "")
    big_nonpub = False
    _cat = classify(r["업태구분명"], leaf, "", big_nonpub)
    if _cat == "바·라운지": continue  # CRITERIA: 와인·칵테일·위스키·라운지류 전면 제외 (2026-08-19)
    venues[f"lic:{mid}"] = {
        "name": name_override.get(mid) or (kp["place_name"] if kp else re.sub(r"^\s*(주식회사|유한회사|\(주\)|㈜|\(유\))\s*|\s*(\(주\)|㈜)\s*$", "", r["사업장명"]).strip() or r["사업장명"]),
        "lic_name": r["사업장명"] if kp and kp["place_name"] != r["사업장명"] else "",
        "cat": _cat,
        "uptae": r["업태구분명"], "area": area_of(r) or None,
        "phone": r["전화번호"] or (kp.get("phone") if kp else "") or "",
        "road": r["도로명주소"] or "", "jibun": r["지번주소"] or "",
        "licensed": True, "multi_use": (r["다중이용업소여부"] or "").strip() == "Y",
        "kakao_url": kp.get("place_url") if kp else "", "kjibun": (kp.get("address_name") or "") if kp else "", "coord_src": src, **coords,
    }
recovered = []
for kp in list(kakao_unmatched):
    _lot = lot_of(kp.get("address_name"))
    if not _lot: continue
    _c = [r for r in by_lot.get(_lot, []) if r["업태구분명"] in PUB_TYPES and r["관리번호"] not in lic_kakao]
    if len(_c) == 1 and "술집" in kp.get("category_name", ""):
        _r = _c[0]
        lic_kakao[_r["관리번호"]] = kp; name_override[_r["관리번호"]] = kp["place_name"]
        kakao_unmatched.remove(kp); recovered.append(kp["place_name"])
        if _r not in pubs: pubs.append(_r)
if recovered: print("지번 단독 결합 면적 회수 " + str(len(recovered)) + "곳: " + ", ".join(recovered[:8]))

dropped = []
for kp in kakao_unmatched:
    if excluded_name(kp["place_name"]): continue
    if in_hotel(kp["place_name"], kp.get("address_name")): continue
    if is_closed(kp["place_name"], kp.get("address_name")):
        dropped.append("kakao:" + kp["place_name"]); continue
    leaf = kp.get("category_name", "").split(" > ")[-1]
    _cat = classify("", leaf, "", False)
    if _cat == "바·라운지": continue
    venues[f"kko:{kp['id']}"] = {
        "name": kp["place_name"], "cat": _cat, "uptae": "",
        "area": None, "phone": kp.get("phone") or "", "road": kp.get("road_address_name") or "",
        "jibun": kp.get("address_name") or "", "licensed": False, "multi_use": False,
        "kakao_url": kp.get("place_url") or "",
        "coord_src": "kakao", "lat": float(kp["y"]), "lng": float(kp["x"]),
    }
json.dump(_geo_cache, open(f"{DATA}/geocode_cache.json", "w"))
print(f"좌표 검증: 지번 대비 200m 초과 이탈 보정 {len(coord_fixes)}건")
for c in coord_fixes: print("  !", c)
# 전화로 직접 확인된 좌석수 (유저 실측) — 추정치보다 우선 표시
CONFIRMED_SEATS = {"우후죽순": 90}
for v in venues.values():
    for k, n in CONFIRMED_SEATS.items():
        if k in norm(v["name"]): v["seat_confirmed"] = n

# ── 파티 트랙 (멤버 카톡 실사 후보) — 회식 CRITERIA와 별개, 파티 토글에서만 표시 ──
PARTY_NOTES = {
    "탄트라": "멤버 실사: 인앤아웃 100명 가능, 은근 괜찮았음",
    "더신더바": "멤버 최종 후보",
    "다이어메이커": "멤버 최종 후보 · 테라스 있음",
    "카페에디토레": "멤버 최종 후보 · 학교앞",
    "홀리데이인인천송도 터치스카이루프탑바": "멤버 평: 엄청 예쁜 느낌은 아닌 듯",
    "모나코": "멤버 평: 화이트 파티 느낌은 잘 안 살 듯",
    "126F&B": "멤버 언급(126 Street)",
    "불독펍": "멤버 언급",
    "레드문": "멤버 평: 애매",
    "레드문 센트럴파크점": "멤버 언급(캠퍼스타운)",
    "플레이그라운드 브루어리탭룸 송도점": "멤버 언급",
    "플레이그라운드 브루어리 브루펍 송도": "멤버 언급",
}
PARTY_ONLY = {"더신더바", "탄트라", "다이어메이커", "홀리데이인인천송도 터치스카이루프탑바", "모나코", "126F&B", "카페에디토레"}
# 자동 발굴(미실사) — 파티 개연성 신호(칵테일·와인바·라운지·재즈·대형)로 추린 후보. 멤버 검증 전.
PARTY_AUTO = {"째즈257", "연금술사 송도점", "오늘와인한잔 송도트리플스트리트점", "타펠 룬데 서울 송도점",
              "프로그앤코", "캐스크앤뀌베&Bar 인천송도점", "클로바", "더킹스 송도", "모닝스타137",
              "블루아이즈", "VIP", "VIP바 2호점", "원일레븐 WINE & DINE", "후레이", "자늑",
              "더라운지 송도", "라운지25", "오크우드프리미어인천 오크바"}
PARTY_ONLY = PARTY_ONLY | PARTY_AUTO
_pn = {norm(k): v for k, v in PARTY_NOTES.items()}
for v in venues.values():
    note = _pn.get(norm(v["name"]))
    if note is not None:
        v["party"] = True; v["party_note"] = note
_have_names = {norm(v["name"]) for v in venues.values()}
for x in json.load(open(f"{DATA}/kakao_fd6_all.json")) + ce7:
    if x["place_name"] not in PARTY_ONLY: continue
    if "송도동" not in (x.get("address_name") or ""): continue
    if norm(x["place_name"]) in _have_names: continue
    r = match(x["place_name"], "", x.get("address_name"))
    venues[f"pty:{x['id']}"] = {
        "name": x["place_name"], "cat": "파티", "uptae": (r["업태구분명"] if r else ""),
        "area": (area_of(r) or None) if r else None,
        "phone": (r["전화번호"] if r else "") or x.get("phone") or "",
        "road": x.get("road_address_name") or "", "jibun": x.get("address_name") or "",
        "licensed": bool(r), "multi_use": False,
        "kakao_url": x.get("place_url") or "", "kjibun": x.get("address_name") or "",
        "coord_src": "kakao", "lat": float(x["y"]), "lng": float(x["x"]),
        "party": True, "party_only": True, "party_note": PARTY_NOTES.get(x["place_name"], "자동 발굴 후보(미실사)"),
    }
print("파티 트랙:", sum(1 for v in venues.values() if v.get("party")), "곳 (전용", sum(1 for v in venues.values() if v.get("party_only")), ")")

out = {"generated": "2026-08-18", "igc": IGC, "venues": list(venues.values())}
open(f"{DATA}/map_data.js", "w", encoding="utf-8").write("window.MAP_DATA = " + json.dumps(out, ensure_ascii=False) + ";")
from collections import Counter
print(f"venues: {len(venues)} (geocoded {geocoded})")
print(Counter(v["cat"] for v in venues.values()).most_common())
print("licensed:", sum(1 for v in venues.values() if v["licensed"]), "/ unmatched:", sum(1 for v in venues.values() if not v["licensed"]))
print("업태 분포:", Counter(v["uptae"] or "(미매칭)" for v in venues.values()).most_common())
print(f"폐업 대장 매칭으로 제거: {len(dropped)}곳")
for d in dropped: print("  -", d)
