# 송도 술집 지도

인천글로벌캠퍼스(IGC) 기준 송도동 술집 지도. https://junsudo.github.io/songdo-bars/

- 모집단: 행정안전부 지방행정 인허가 데이터(연수구, 매일 갱신) + 카카오맵 Local API
- 규모: 인허가 신고 영업장 면적(㎡) → 추정 좌석(2.0~2.5㎡/석)
- 이동 시간: 도보 OSRM(foot), 택시 카카오내비 API(시간·요금), 대중교통은 카카오맵 실시간 링크
- 폐업 필터: 영업중 대장 + 폐업 대장 대조로 유령 업소 제거

## 데이터 갱신

```
python3 collect_kakao.py   # 카카오 술집 수집 (keys.env에 KAKAO_REST_KEY 필요)
python3 prep_map.py        # 인허가 병합 + 좌표
python3 enrich_routes.py   # 도보·택시 시간
python3 enrich_phones.py   # 전화번호 보강
```

인허가 CSV는 `https://file.localdata.go.kr/file/download/general_restaurants/info?orgCode=3520000` (브라우저 User-Agent 필요, CP949).
