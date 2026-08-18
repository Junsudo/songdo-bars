#!/bin/sh
# 데이터 재생성 전체 파이프라인 — 단계 누락 방지용. 하나라도 실패하면 중단.
set -e
python3 prep_map.py
python3 enrich_routes.py
python3 enrich_phones.py
python3 check_positions.py
python3 - <<'PY'
import json
d = json.loads(open('data/map_data.js', encoding='utf-8').read()[len('window.MAP_DATA = '):-1])
missing = [k for k in ('walk_min','taxi_min') if any(v.get(k) is None for v in d['venues'])]
assert not missing, f"필드 누락: {missing}"
print(f"OK — {len(d['venues'])}곳, 시간·좌표 검증 포함 전체 파이프라인 통과")
PY
