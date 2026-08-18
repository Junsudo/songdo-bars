# -*- coding: utf-8 -*-
# 네이버 지역검색(API HUB) 통합: 업소별 조회로 네이버 등록 여부·카테고리 부착 + 좌표 교차검증
import json, re, subprocess, time, unicodedata, urllib.parse, math

ID = [l.split("=", 1)[1].strip() for l in open("keys.env") if l.startswith("NAVER_HUB_ID=")][0]
SEC = [l.split("=", 1)[1].strip() for l in open("keys.env") if l.startswith("NAVER_HUB_SECRET=")][0]
PREFIX = "window.MAP_DATA = "
data = json.loads(open("data/map_data.js", encoding="utf-8").read()[len(PREFIX):-1])

def norm(s):
    s = unicodedata.normalize("NFKC", str(s or "")).lower()
    return re.sub(r"<[^>]+>|[^0-9a-z가-힣]", "", s)

def lot_of(addr):
    m = re.search(r"송도동\s*(\d+(?:-\d+)?)", addr or "")
    return m.group(1) if m else None

try: cache = json.load(open("data/naver_cache.json"))
except Exception: cache = {}

def search(q):
    url = "https://naverapihub.apigw.ntruss.com/search/v1/local?" + urllib.parse.urlencode({"query": q, "display": 5})
    out = subprocess.run(["/usr/bin/curl", "-s", "--max-time", "10", url,
                          "-H", f"X-NCP-APIGW-API-KEY-ID: {ID}", "-H", f"X-NCP-APIGW-API-KEY: {SEC}"],
                         capture_output=True, text=True).stdout
    try: return json.loads(out).get("items", [])
    except Exception: return []

def pick(v, items):
    vn = norm(v["name"]); vlot = lot_of(v.get("jibun")) or lot_of(v.get("kjibun"))
    best = None
    for it in items:
        tn = norm(it.get("title"))
        name_sim = vn and tn and min(len(vn), len(tn)) >= 3 and (vn in tn or tn in vn)
        ilot = lot_of(it.get("address"))
        lot_ok = vlot and ilot and vlot == ilot
        if name_sim and lot_ok: return it, "이름+지번"
        if name_sim and not best: best = (it, "이름")
        elif lot_ok and not best: best = (it, "지번")
    return best if best else (None, None)

done = far = found = 0
far_list = []
for v in data["venues"]:
    key = norm(v["name"]) + "|" + (lot_of(v.get("jibun")) or "")
    if key not in cache:
        q = re.sub(r"\(.*?\)", "", v["name"]).strip()
        items = search(f"{q} 송도")
        it, how = pick(v, items)
        if not it and " " in q:
            items = search(q.split()[0] + " 송도")
            it, how = pick(v, items)
        rec = None
        if it:
            try:
                nlat = int(it["mapy"]) / 1e7; nlng = int(it["mapx"]) / 1e7
                dm = math.hypot((v["lat"] - nlat) * 111320, (v["lng"] - nlng) * 111320 * math.cos(math.radians(nlat)))
            except Exception:
                dm = None
            rec = {"cat": it.get("category") or "", "how": how, "dist": round(dm) if dm is not None else None}
        cache[key] = rec
        done += 1
        if done % 30 == 0:
            json.dump(cache, open("data/naver_cache.json", "w"))
            print(f"{done}건 조회…")
        time.sleep(0.11)
    rec = cache[key]
    if rec and rec.get("how") == "이름" and (rec.get("dist") is None or rec["dist"] > 300):
        rec = None  # 이름 단독 매칭은 300m 이내만 인정 (원거리 동명 오매칭 방지)
    if rec:
        found += 1
        v["naver_cat"] = rec["cat"]; v["naver_ok"] = True
        if rec.get("dist") is not None and rec["dist"] > 300:
            far += 1; far_list.append((v["name"], rec["dist"], rec["how"]))
    else:
        v["naver_cat"] = ""; v["naver_ok"] = False

json.dump(cache, open("data/naver_cache.json", "w"))
open("data/map_data.js", "w", encoding="utf-8").write(PREFIX + json.dumps(data, ensure_ascii=False) + ";")
print(f"네이버 등록 확인 {found}/{len(data['venues'])}, 좌표 300m 초과 {far}건")
for f in far_list: print("  ?", f)
