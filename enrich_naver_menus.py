# -*- coding: utf-8 -*-
# 네이버 플레이스 메뉴: 검색에서 place id 매칭(이름 문맥) → m.place 메뉴 페이지 APOLLO 파싱
# 내부 검색어에 '송도'를 붙이는 것은 동명 타지역 매장 오매칭 방지용 (사용자 노출 링크와 무관)
import json, re, subprocess, time, unicodedata, urllib.parse

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
PREFIX = "window.MAP_DATA = "
data = json.loads(open("data/map_data.js", encoding="utf-8").read()[len(PREFIX):-1])

def norm(s):
    s = unicodedata.normalize("NFKC", str(s or "")).lower()
    return re.sub(r"[^0-9a-z가-힣]", "", s)

try: ids = json.load(open("data/naver_place_ids.json"))
except Exception: ids = {}
try: mcache = json.load(open("data/naver_menus.json"))
except Exception: mcache = {}

def curl(url):
    return subprocess.run(["/usr/bin/curl", "-s", "--max-time", "12", url, "-A", UA,
                           "-H", "Accept-Language: ko-KR,ko;q=0.9"], capture_output=True, text=True).stdout

def find_id(name):
    q = urllib.parse.quote(re.sub(r"\(.*?\)", "", name).strip() + " 송도")
    h = curl(f"https://search.naver.com/search.naver?query={q}")
    key = norm(name)[:8]
    for m in re.finditer(r"entry/place/(\d+)", h):
        ctx = h[max(0, m.start()-400):m.start()+100]
        if key and key in norm(ctx):
            return m.group(1)
    return None

def fetch_menu(pid):
    h = curl(f"https://m.place.naver.com/restaurant/{pid}/menu/list")
    m = re.search(r"window\.__APOLLO_STATE__\s*=\s*(\{.*?\});", h, re.S)
    if not m: return []
    try: d = json.loads(m.group(1))
    except Exception: return []
    out = []
    for k, v in d.items():
        if k.startswith("Menu:") and v.get("name"):
            try: p = int(v.get("price") or 0)
            except Exception: p = 0
            out.append({"n": v["name"], "p": p, "r": bool(v.get("recommend"))})
    return out[:12]

done = 0
for v in data["venues"]:
    key = norm(v["name"])
    if key not in ids:
        ids[key] = find_id(v["name"]); done += 1
        time.sleep(0.3)
        if done % 30 == 0:
            json.dump(ids, open("data/naver_place_ids.json", "w")); print(f"id {done}건…")
    pid = ids.get(key)
    if pid and pid not in mcache:
        mcache[pid] = fetch_menu(pid)
        time.sleep(0.25)
    items = (mcache.get(pid) or []) if pid else []
    items = sorted(items, key=lambda m: (not m["r"],))
    out = []
    for m in items:
        out.append(f"{m['n']} {m['p']:,}원" if m["p"] > 0 else m["n"])
        if len(out) >= 4: break
    v["menus_nv"] = out

json.dump(ids, open("data/naver_place_ids.json", "w"))
json.dump(mcache, open("data/naver_menus.json", "w"))
open("data/map_data.js", "w", encoding="utf-8").write(PREFIX + json.dumps(data, ensure_ascii=False) + ";")
n = sum(1 for v in data["venues"] if v.get("menus_nv"))
both = sum(1 for v in data["venues"] if v.get("menus_nv") and not v.get("menus"))
print(f"네이버 메뉴 확보 {n}곳 (카카오 메뉴 없던 곳 보완 {both}곳)")
