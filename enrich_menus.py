# -*- coding: utf-8 -*-
# 카카오맵 플레이스 공식 메뉴(panel3)를 각 업소에 부착 — 블로그 추출 대체
import json, subprocess, time

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
PREFIX = "window.MAP_DATA = "
data = json.loads(open("data/map_data.js", encoding="utf-8").read()[len(PREFIX):-1])

try: cache = json.load(open("data/kakao_menus.json"))
except Exception: cache = {}

def fetch_menu(pid):
    out = subprocess.run(["/usr/bin/curl", "-s", "--max-time", "12",
        f"https://place-api.map.kakao.com/places/panel3/{pid}",
        "-A", UA, "-H", "Referer: https://place.map.kakao.com/", "-H", "Origin: https://place.map.kakao.com",
        "-H", "Accept: application/json, text/plain, */*", "-H", "pf: web"],
        capture_output=True, text=True).stdout
    try:
        d = json.loads(out)
        items = (d.get("menu") or {}).get("menus", {}).get("items") or []
        return [{"n": m.get("name"), "p": m.get("price"), "r": bool(m.get("is_recommend"))} for m in items[:10]]
    except Exception:
        return None

done = 0
for v in data["venues"]:
    u = v.get("kakao_url") or ""
    if not u:
        v["menus"] = []; continue
    pid = u.rstrip("/").split("/")[-1]
    if pid not in cache:
        r = fetch_menu(pid)
        cache[pid] = r if r is not None else []
        done += 1
        if done % 40 == 0:
            json.dump(cache, open("data/kakao_menus.json", "w"))
            print(f"{done}건…")
        time.sleep(0.15)
    items = cache.get(pid) or []
    items = sorted(items, key=lambda m: (not m["r"],))  # 추천 먼저, 이후 메뉴판 순서
    out = []
    for m in items:
        if not m.get("n"): continue
        p = m.get("p")
        out.append(f"{m['n']} {p:,}원" if isinstance(p, int) and p > 0 else m["n"])
        if len(out) >= 4: break
    v["menus"] = out

json.dump(cache, open("data/kakao_menus.json", "w"))
open("data/map_data.js", "w", encoding="utf-8").write(PREFIX + json.dumps(data, ensure_ascii=False) + ";")
n = sum(1 for v in data["venues"] if v.get("menus"))
print(f"카카오 메뉴 확보 {n}/{len(data['venues'])}곳 (신규 조회 {done})")
