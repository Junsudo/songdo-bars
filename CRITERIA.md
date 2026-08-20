# Inclusion Criteria — Songdo Bar Map

Governing document. Every pipeline rule traces to a line here. When a rule and this file disagree, this file wins.

## Purpose

| Item | Value |
|---|---|
| Use case | University club dinners (회식/개강총회), ~100 people, IGC-based |
| Deciding question | "Can a student club hold a loud, cheap, soju/beer dinner here?" — NOT "is it a bar?" |

## Deciding test

A venue passes only if it passes EVERY row. One failed row = out.

| # | Test | PASS looks like | FAIL looks like |
|---|---|---|---|
| 1 | Role of alcohol | Soju/beer is the point, or equal to the food: 호프, 포차, 이자카야, 요리주점, 치킨호프, 피맥, 조개·안주집 | A sober dinner there is normal: 백반, 국밥, 한정식, 정식, 구이 전문(소고기·생선), 초밥, 뷔페, 브런치, 버거, 외국요리 전문(파스타·그리스·태국·멕시코) |
| 2 | Price per head | ~₩20-30k covers 안주+술; soju/beer sold by the bottle at bottle prices | Premium liquor core, glass pricing: 위스키, 와인, 칵테일, 하이볼 전문, craft flights, 코스/오마카세, hotel F&B |
| 3 | Seating structure | Open hall; tables can be pushed together; 20-40 people seat in one section | Bar-counter centric, booth/room-only, standing, gallery/전시형 |
| 4 | Noise | Group toasts and shouting are normal there | Quiet/date ambience expected: 와인바, 라운지, 재즈바, LP바 |
| 5 | Operation type | Ordinary table service | Dance/booking floor (감성주점, 헌팅포차, 클럽, 나이트), performance-watching (라이브카페), membership/reservation-only |
| 6 | Hours | Evening-to-late (자정 전후까지) | Closes ~21-22h: mall food courts, cafes, bakeries |

Notes.
- No per-venue minimum size: 100 people can split across sections or venues. Size is handled by the area filter, not the deciding test.
- Signal conflicts (e.g., izakaya with a sushi Naver category): row 1 decides. Still unclear → ask the owner. Never include silently.
- Calibration anchors, PASS (owner-verified): 부엉이산장, 우후죽순 (90석 phone-confirmed), 88노가리, 단토리, 역전할머니맥주, 앨리스피맥, 크라운호프.
- Calibration anchors, FAIL (owner-rejected): 더몰트하우스 (whisky), 와인기대, 파르크드와인, 데이롱 (highball cafe), 튜나펍, 쎄시봉 (live cafe), 랍스터퍼블릭라운지, 제이라운지, 10.19, 쉐이크쉑, 경복궁 삼계탕, 파노라믹65, hotel venues.

## Include

| Source | Rule |
|---|---|
| License register (alive, Songdo-dong) | 업태 in {호프/통닭, 정종/대포집/소주방} |
| Kakao FD6 `술집` category | If matched to an alive license (any 업태 not excluded below) |
| Kakao FD6 `치킨` category | Only if matched license ≥ 100㎡, or alias-verified (또봉이=브루엠) |
| Curated allowlist | 앨리스피맥 (23-5, 84-2), 크라운호프 송도점 — pimac/hof only |

## Exclude (hard rules, owner-decided)

| Class | Rule |
|---|---|
| 업태 | 경양식, 뷔페식, 중국식, 분식, 식육(숯불구이), 감성주점 (dance-permitted = hunting pocha proxy), 라이브카페, 탕류(보신용), 패밀리레스트랑, 냉면집, 출장조리 |
| Hotels | Name/address contains 호텔·쉐라톤·오라카이·홀리데이인·오크우드, or lot in {6-9, 38, 93-1, 33-1, 6-10, 10-2} |
| Ghosts | Unmatched POI whose name/lot matches the closed-license register |
| Kakao category | 나이트, 클럽 |
| Naver category (non-pub 업태) | 베이커리, 제과, 급식, 도시락, 반찬, 샐러드, 카페·디저트, 낙지, 주꾸미, 바닷가재, 이탈리아, 그리스, 태국, 멕시코, 남미, plus 한정식·소고기·생선·초밥·샤브·국수류 for any restaurant-type entry |
| Named rejects | 제우스볼펍(bowling), 헌팅*, 다올앤펍(license-only ghost), 스월링라운지, 스낵얌, 앨리스피맥 30-2 (all zero-evidence), 더몰트하우스(whisky pub), 랍스터퍼블릭라운지, 와인기대, 파르크드와인, 제이라운지, 10.19, 데이롱, 튜나펍, 쎄시봉 (specialty, owner-rejected), 쉐이크쉑 |

## Data quality

| Item | Value |
|---|---|
| Matching order | ① same-lot + name containment ② exact name (same-lot preferred) ③ suffix-stripped name, abort if all candidate lots differ |
| Coordinate gate | Kakao coords kept when POI lot == license lot; lot mismatch + >200m → license-lot geocode, kakao link severed |
| Position audit | check_positions.py reverse-geocodes every venue; FAIL must be 0 to ship |
| Seat estimate | area ÷ 2.0 (low) to ÷ 1.65 (high); calibrated by phone-confirmed 우후죽순 = 90 seats @150㎡ |
| Phone-confirmed data | CONFIRMED_SEATS in prep_map.py, overrides estimates |
| Rebuild | `./regen.sh` only (prep → routes → phones → naver → seats → audits). Never run steps individually for a release |

## Load-bearing decisions

- 2026-08-18 DiningCode dropped as a source (stale/ghost entries; owner order).
- 2026-08-18 Franchise branch mis-matching fixed by lot-first matching after 역전할머니 incident.
- 2026-08-19 Hotels excluded wholesale (owner order).
- 2026-08-19 감성주점 excluded as hunting-pocha proxy (owner order, important).
- 2026-08-19 "Large venue" track abolished: every 200㎡+ non-pub candidate failed owner review. Big-venue search happens inside the pub pool via the area filter.
- 2026-08-19 Specialty small bars (wine/whisky/lounge/highball) fail the use case even when individually verified as real bars. Curation must test against the use case, not venue authenticity.
