# CLAUDE.md — songdo-bars

Songdo bar map for university club dinners. Live: https://junsudo.github.io/songdo-bars/

## Ground rules

| Item | Value |
|---|---|
| Governing doc | `CRITERIA.md`. Every include/exclude decision must pass its 6-row test. When unclear, ask the owner. NEVER add or protect a venue on your own judgment — this failed twice (더몰트하우스 incident) |
| Rebuild | `./regen.sh` only. Never run pipeline steps individually for a release (a skipped step once shipped data without travel times) |
| Ship gate | `check_positions.py` must report FAIL 0 |
| Owner style | Answer only what was asked. Report root cause before patching. Korean replies, English technical terms |

## Pipeline

| Step | Script | Notes |
|---|---|---|
| 1 | `prep_map.py` | License CSV + Kakao merge, matching, coordinate gate, exclusions |
| 2 | `enrich_routes.py` | Walk = OSRM foot (routing.openstreetmap.de), taxi = Kakao Navi (time+fare). Cache: `data/routes_cache.json` |
| 3 | `enrich_phones.py` | Phone fill via Kakao keyword search |
| 4 | `enrich_naver.py` | Naver presence/category + global category drops |
| 5 | `crawl_seats.py` | Blog seat mentions (thin) |
| 5b | `enrich_menus.py` | Official Kakao menus via place-api panel3 — needs `pf: web` header (curl 406 without it) |
| 6 | `check_positions.py` | Reverse-geocode audit of every venue |

`build_xlsx` logic lives inline in history; xlsx is generated from `data/map_data.js`, not from raw sources.

## Keys (`keys.env`, gitignored — never commit)

| Key | Service | Gotchas |
|---|---|---|
| KAKAO_REST_KEY | Kakao Local + Navi (app "PAGE Spot", 카카오맵 enabled) | Local: max 45 results/query → bbox quadtree. Navi: no `priority=SHORTEST` (invalid) |
| NAVER_HUB_ID / SECRET | NAVER API HUB 지역검색 | Domain `naverapihub.apigw.ntruss.com`, path `/search/v1/local`, headers `X-NCP-APIGW-API-KEY-ID`/`X-NCP-APIGW-API-KEY`. display≤5, start=1 fixed, no telephone |
| TAGO_KEY | data.go.kr — BusRoute(신형) + BusRouteInfoInqireService(구형) | 순환42: cityCode=23, routeId=ICB365000515. 신형 getBusRoute needs opr_ymd with data (monthly snapshots, e.g. 01일자) |

## Hard-won facts

- License CSV: `file.localdata.go.kr/file/download/general_restaurants/info?orgCode=3520000` — needs browser UA **and** `Referer: https://www.data.go.kr/`, CP949. localdata.go.kr portal itself is dead (2026-01).
- Sandbox proxy breaks Python urllib TLS — always shell out to `/usr/bin/curl`.
- naver.com domains block fetch; Naver Place has no API. Transit minutes impossible without ODsay (owner rejected signup) — Kakao Map deep link is the accepted substitute.
- DiningCode was removed as a source by owner order. Do not reintroduce. Its stale entries create ghosts (술판 incident).
- Matching is lot-first (`match()` in prep_map.py) after franchise branch mix-ups (역전할머니 incident). Aliases for verified same-store different-name cases live in `ALIAS`.
- Phone-confirmed facts go in `CONFIRMED_SEATS` (e.g., 우후죽순 90석). Seat estimate = area ÷2.0~÷1.65, calibrated on that datapoint.
- GitHub Pages uses Actions build (`build_type=workflow`, deploys in ~25s); `.nojekyll` required (Jekyll builds failed). Browser CDN cache is 10min, fixed.
- Transit overlay data: `data/transit.js` (Incheon Line 1 from OSM + Kakao SW8 stations; 순환42 = 105 official TAGO stops + Kakao Navi road-chained line). Bus stops render as green squares, never circles (owner order); station names always labeled.
