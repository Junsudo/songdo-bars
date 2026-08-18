# -*- coding: utf-8 -*-
# IGC 기준 도보(OSRM foot)·택시(카카오내비) 시간을 map_data.js에 주입. 좌표별 캐시로 재실행 시 스킵.
import json, subprocess, time

KEY = [l.split("=", 1)[1].strip() for l in open("keys.env") if l.startswith("KAKAO_REST_KEY=")][0]
PREFIX = "window.MAP_DATA = "
raw = open("data/map_data.js", encoding="utf-8").read()
data = json.loads(raw[len(PREFIX):-1])
IGC = data["igc"]

try: cache = json.load(open("data/routes_cache.json"))
except Exception: cache = {}

def curl(url, hdr=None):
    args = ["curl", "-s", "--max-time", "15", url]
    if hdr: args += ["-H", hdr]
    out = subprocess.run(args, capture_output=True, text=True).stdout
    try: return json.loads(out)
    except Exception: return None

def walk_route(lat, lng):
    d = curl(f"https://routing.openstreetmap.de/routed-foot/route/v1/foot/{IGC['lng']},{IGC['lat']};{lng},{lat}?overview=false")
    if d and d.get("code") == "Ok" and d.get("routes"):
        r = d["routes"][0]
        return {"walk_min": round(r["duration"] / 60), "walk_km": round(r["distance"] / 1000, 2)}
    return {}

def taxi_route(lat, lng):
    d = curl(f"https://apis-navi.kakaomobility.com/v1/directions?origin={IGC['lng']},{IGC['lat']}&destination={lng},{lat}",
             f"Authorization: KakaoAK {KEY}")
    try:
        r = d["routes"][0]
        if r.get("result_code") != 0: return {}
        s = r["summary"]
        return {"taxi_min": max(1, round(s["duration"] / 60)), "taxi_fare": s.get("fare", {}).get("taxi")}
    except Exception:
        return {}

done = 0
for i, v in enumerate(data["venues"]):
    key = f"{v['lat']:.6f},{v['lng']:.6f}"
    if key not in cache or "walk_min" not in cache[key] or "taxi_min" not in cache[key]:
        rec = dict(cache.get(key, {}))
        if "walk_min" not in rec:
            rec.update(walk_route(v["lat"], v["lng"])); time.sleep(0.25)
        if "taxi_min" not in rec:
            rec.update(taxi_route(v["lat"], v["lng"])); time.sleep(0.1)
        cache[key] = rec
        done += 1
        if done % 25 == 0:
            json.dump(cache, open("data/routes_cache.json", "w"))
            print(f"{i+1}/{len(data['venues'])} …")
    v.update({k: cache[key].get(k) for k in ("walk_min", "walk_km", "taxi_min", "taxi_fare")})

json.dump(cache, open("data/routes_cache.json", "w"))
open("data/map_data.js", "w", encoding="utf-8").write(PREFIX + json.dumps(data, ensure_ascii=False) + ";")
ok_w = sum(1 for v in data["venues"] if v.get("walk_min") is not None)
ok_t = sum(1 for v in data["venues"] if v.get("taxi_min") is not None)
print(f"완료: 도보 {ok_w}/{len(data['venues'])}, 택시 {ok_t}/{len(data['venues'])}")
