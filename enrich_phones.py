# -*- coding: utf-8 -*-
# 전화번호 보강: 비어 있는 업소를 카카오 키워드 검색(좌표 반경 300m + 이름 일치)으로 채움
import json, re, subprocess, time, unicodedata, urllib.parse

KEY = [l.split("=", 1)[1].strip() for l in open("keys.env") if l.startswith("KAKAO_REST_KEY=")][0]
PREFIX = "window.MAP_DATA = "
raw = open("data/map_data.js", encoding="utf-8").read()
data = json.loads(raw[len(PREFIX):-1])

def norm(s):
    s = unicodedata.normalize("NFKC", str(s or "")).lower()
    return re.sub(r"[^0-9a-z가-힣]", "", s)

# 로컬 디렉토리 소스(생활맥주·트리플스트리트)의 전화 먼저 활용
dir_phones = {}
try:
    ts = json.load(open("data/triplestreet.json"))
    for x in ts:
        if x.get("tel"): dir_phones[norm(x["name"])] = x["tel"]
except Exception: pass
db_html = open("data/dailybeer.html", encoding="utf-8", errors="replace").read()
for m in re.findall(r'\{[^{}]*"name"[^{}]*\}', db_html.replace("\\/", "/")):
    try:
        o = json.loads(m)
        if "송도" in json.dumps(o, ensure_ascii=False) and o.get("tel"): dir_phones[norm(o["name"])] = o["tel"]
    except Exception: pass

def kakao_phone(v):
    q = urllib.parse.quote(v["name"])
    url = (f"https://dapi.kakao.com/v2/local/search/keyword.json?query={q}"
           f"&x={v['lng']}&y={v['lat']}&radius=300&size=5")
    out = subprocess.run(["curl", "-s", "--max-time", "10", url, "-H", f"Authorization: KakaoAK {KEY}"],
                         capture_output=True, text=True).stdout
    try:
        for doc in json.loads(out)["documents"]:
            a, b = norm(doc["place_name"]), norm(v["name"])
            if doc.get("phone") and (a in b or b in a):
                return doc["phone"]
    except Exception: pass
    return ""

filled_dir = filled_kakao = 0
for v in data["venues"]:
    if v.get("phone"): continue
    p = dir_phones.get(norm(v["name"]))
    if p: v["phone"] = p; filled_dir += 1; continue
    p = kakao_phone(v)
    if p: v["phone"] = p; filled_kakao += 1
    time.sleep(0.1)

open("data/map_data.js", "w", encoding="utf-8").write(PREFIX + json.dumps(data, ensure_ascii=False) + ";")
total = sum(1 for v in data["venues"] if v.get("phone"))
print(f"디렉토리로 {filled_dir}, 카카오 검색으로 {filled_kakao} 보강 → 전화 보유 {total}/{len(data['venues'])}")
