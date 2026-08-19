# Inclusion Criteria — Songdo Bar Map

Governing document. Every pipeline rule traces to a line here. When a rule and this file disagree, this file wins.

## Purpose

| Item | Value |
|---|---|
| Use case | University club dinners (회식/개강총회), ~100 people, IGC-based |
| Deciding question | "Can a student club hold a drinking dinner here?" — NOT "is it a bar?" |
| Owner ruling | Specialty venues fail even if they serve alcohol: whisky pubs, wine bars, lounges, live cafes, hunting pochas |

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
