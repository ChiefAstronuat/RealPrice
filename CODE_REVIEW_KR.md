# 코드 리뷰 요약 (최신 구현 기준)

## 확인한 핵심 이슈
1. **모드 분리 불명확**
   - 기존 구현에서 `mode=both`일 때 소매(retail) 라인도 함께 표시되어 UX 규칙(도매/소매 분리)에 어긋남.
2. **nowcast 노출 범위 과다**
   - 기존 구현에서 시계열 전체 구간에 nowcast 값이 노출될 수 있었음.
3. **summary 날짜 기준 delta 계산 오류 가능성**
   - 특정 `date` 파라미터 요청 시에도 전역 최신 인덱스를 기준으로 주간 비교가 계산될 가능성이 있었음.
4. **입력 파라미터 검증 부족**
   - `timeseries`의 `mode` 값이 비정상이어도 처리되어 디버깅이 어려움.

## 반영한 수정
- `timeseries`에서 `mode` 검증(`final|both|retail`) 및 잘못된 입력 400 반환 추가.
- `timeseries` nowcast는 `status in {mixed, nowcast}`인 구간만 노출하도록 제한.
- `summary`는 요청 `date`에 맞는 인덱스로 `delta_day`, `delta_week` 계산하도록 수정.
- 프론트 차트 라인 렌더링 규칙 수정:
  - `mode=both` -> final + nowcast
  - `mode=retail` -> final + retail
  - `mode=final` -> final only

## 잔여 리스크(다음 단계)
- 대용량 JSON 파일 기반 로드는 메모리/배포 효율이 낮아 DB 마트 조회로 전환 필요.
- 현재 커스텀 Canvas 차트는 접근성/툴팁/테스트성 개선 여지 큼(ECharts/Chart.js 권장).
- 인증/레이트리밋/관측치 품질경보(결측/이상치) 로직은 아직 미구현.
