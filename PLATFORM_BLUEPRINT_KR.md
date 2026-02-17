# RealPrice 고구마 가격 제품(MVP) 상세 설계안

## 1) 제품 목표와 SLA

### 1.1 목표(Price Product)
사용자에게 “고구마 가격”을 단일 숫자로 뭉개지 않고, 동일 규격(`spec_id`) 기준으로 제공한다.
- 도매 확정가(final)
- 도매 잠정가(nowcast)
- 소매 평균가(KAMIS, 별도 레이어)
- 가격 분포(p10~p90), 신뢰도, 최신성
- 지역 편차 및 규격 정의

핵심 원칙:
- 가격 최소 단위는 반드시 `spec_id`
- “평균 자료(KAMIS)”는 도매 확정/잠정과 혼합 표시 금지

### 1.2 ±3일 SLA(운영 고정값)
- T일 final은 T+3일 내 확정
- T~T+3 구간은 nowcast + final 동시 제공
- UI에 `잠정/확정` 배지 및 confidence score 의무 노출

---

## 2) 규격(spec) 고정

## 2.1 MVP 표준 규격
- commodity: 고구마
- variety: (초기) 일반계 고정, 확장 시 밤/호박
- grade: 상품(상급 대응), 중품
- unit: KRW/kg (고정)
- size: 가능하면 고정, 미지정 시 품질 패널티

## 2.2 품질 규격 연결
- KAMIS/표준규격의 등급·중량·균일도·결점 기준을 `quality_rule_ref`로 연결
- 동일 상품명이라도 규격 다르면 다른 `spec_id`로 분리

---

## 3) MVP 화면 IA (1페이지 원칙)

## 3.1 단일 페이지
- 경로: `/sweetpotato`
- 상단 필터 고정 + 중앙 요약/추이 + 하단 접힘 상세

## 3.2 상단 필터(고정 영역)
- 품목: 고구마(고정)
- 지역: 전국 / 시·도 / (확장) 시군구
- 규격(spec): 품종, 등급 (단위 KRW/kg 고정)
- 기간: 14일 / 30일 / 90일 / 1년 / 전체
- 모드: 확정 / 잠정+확정 / 소매(평균)

## 3.3 핵심 카드(요약)
- 확정가(final): 값 + 전일/전주 대비
- 잠정가(nowcast): 최근 3일 구간만
- 범위(p10~p90) + confidence
- 최신성(as-of KST)
- 보조 문구: “확정은 보통 T+3일 반영, 최근 3일은 잠정치”

## 3.4 메인 추이 차트
- final: 실선
- nowcast: 점선(최근 3일만)
- 불확실성 밴드(p10~p90): 기본 OFF 토글
- 거래량: 하단 bar 또는 tooltip
- tooltip: 날짜/final/nowcast/p10/p90/거래량/시장 수

## 3.5 하단 접힘 상세
- 시장별 분포(상위 10개 시장)
- spec 정의(이 값이 어떤 규격인지)
- 데이터 출처/갱신주기/제한(투명성)

---

## 4) UX 필수 규칙(혼란 방지)

### 4.1 최근 3일 시각 분리
- 차트에서 최근 3일 배경 음영
- 레전드에 “잠정(최근 3일)” 명시
- 카드에서도 잠정 배지 유지

### 4.2 KAMIS 평균 분리
- KAMIS는 별도 토글/보조축으로만 제공
- 기본 모드는 도매 확정/잠정

### 4.3 공유 URL
- 필터 상태를 쿼리스트링에 보존
- 예: `/sweetpotato?region=11&spec=SP001&range=90d&mode=both`

---

## 5) 차트 스펙(가격 추이)

### 5.1 데이터 포인트(일 1개)
- 차트는 raw 관측치가 아니라 `daily mart` 집계를 사용

```json
{
  "date": "2026-02-17",
  "final": 3150,
  "nowcast": 3210,
  "p10": 2800,
  "p90": 3600,
  "wholesale_volume_kg": 128500,
  "n_markets": 18,
  "confidence": 0.82
}
```

### 5.2 선 스타일 규칙
- final: 실선(기본 표시)
- nowcast: 점선, 최근 3일 외 구간은 null
- p10~p90: 음영, 기본 OFF

### 5.3 스무딩 옵션 분리
- 기본: raw daily
- 옵션: `7일 중앙값(±3)` 토글
- 스무딩 ON 시 tooltip에 원값 동시 표시

---

## 6) 백엔드 API 계약(웹 UI 최소)

### 6.1 메타 API
- `GET /api/v1/sweetpotato/specs`
  - returns: `spec_id, label, grade, variety, unit`
- `GET /api/v1/regions?level=si_do`
  - returns: `region_id, region_name`

### 6.2 요약 카드 API
- `GET /api/v1/sweetpotato/summary?spec_id=...&region_id=...&date=YYYY-MM-DD`
- returns: `final, nowcast, p10, p90, confidence, as_of`

### 6.3 시계열 API
- `GET /api/v1/sweetpotato/timeseries?spec_id=...&region_id=...&start=YYYY-MM-DD&end=YYYY-MM-DD&mode=both`
- returns: daily points array

### 6.4 시장 분포 API
- `GET /api/v1/sweetpotato/market_breakdown?spec_id=...&date=YYYY-MM-DD&region_scope=...`
- returns:
  - by-market: `market_id, market_name, median_price, volume_kg, p10, p90, trades`
  - summary: `total_volume_kg, n_markets`

---

## 7) 서빙 데이터 마트(선계산)

### 7.1 `mart_sweetpotato_price_daily`
- PK: `(date, spec_id, region_id)`
- columns:
  - `final_krw_per_kg`
  - `nowcast_krw_per_kg`
  - `p10, p90`
  - `wholesale_volume_kg`
  - `n_markets, n_trades`
  - `confidence_score`
  - `as_of_timestamp`
  - `status = final | nowcast | mixed`

### 7.2 `mart_sweetpotato_market_daily` (상세용)
- PK: `(date, spec_id, market_id)`
- columns:
  - `median_krw_per_kg, p10, p90`
  - `volume_kg, n_trades`
  - `confidence`

---

## 8) 데이터 소스 정책(Required/Recommended/Not Available)

### 8.1 Required
- 공영도매시장 정산정보(final 근간)
- 공영도매시장 실시간 경매정보(nowcast 근간)
- 공영도매시장 표준코드(해석 필수)
- 실시간 CSV fallback(장애/검증)

### 8.2 Recommended
- KAMIS 도·소매 및 지역 평균 API
- KAMIS 해석 규칙(5일 이동평균 성격) 메타화

### 8.3 Not Available
- 점포별 실제 매입원가/폐기율/실원가
- 계약 마진/농가 실측 원가/로트 물성 데이터
- UI에서 반드시 “추정치”로 명시

---

## 9) ETL 파이프라인

### 9.1 주기
- 실시간 경매: 10~30분
- 정산정보: 일 1회 + D-3 재수집
- 표준코드: 일 1회(또는 주 1회)
- KAMIS: 일 1~2회

### 9.2 잡
- `ingest_wholesale_codes`
- `ingest_wholesale_realtime`
- `ingest_wholesale_settlement`
- `ingest_kamis_daily`

핵심:
- `kg_unit_cnvr_qyt` 기반 kg 환산
- 환산 실패 플래그 저장
- 코드 변경 diff 이력 관리

---

## 10) 가격 산출 로직

### 10.1 MVP(규칙 기반)
- nowcast: 실시간 경매를 시장별 median 후 거래량 가중 결합
- final: 정산 `avg_price` 또는 `total_amt/total_qty`
- 안정화: D-3 재수집 + 선택적 스무딩

### 10.2 확장(상태공간)
- 잠재가격 `p_t` + 관측치(`auction`, `settlement`, `kamisRetail`) 융합
- 정산 유입 전 nowcast 중심, 유입 후 final 수렴

---

## 11) 프론트엔드 구현 스택/컴포넌트

### 11.1 스택
- Next.js + TypeScript
- ECharts 또는 Chart.js
- Tailwind 또는 최소 CSS

### 11.2 최소 컴포넌트
- `FilterBar`
- `PriceSummaryCards`
- `TrendChart`
- `QualityBadge`
- `MarketBreakdown`(접힘)
- `DataSourcePanel`(접힘)

---

## 12) 성능/캐시 전략

### 12.1 캐시 계층
- CDN 캐시: timeseries
- Redis 캐시: summary
- DB 인덱스: `(spec_id, region_id, date)` 필수

### 12.2 응답 최적화
- gzip/brotli 기본 적용
- 필드 선택 파라미터 지원: `?fields=final,nowcast`

---

## 13) 신뢰를 지키는 표시 규칙
- 메인 숫자는 3개(확정/잠정/소매)
- 신뢰도: 높음/보통/낮음 + 근거 툴팁
- 원인설명/출처/제약은 접힘 기본
- 차트 영역 광고 금지(가독성·신뢰 보호)

---

## 14) 광고 배치(식품 무관, 간섭 최소)
- 메인 카드 아래 가로 배너 1개
- 상세 탭 진입 시 하단/사이드 1개
- 차트 영역 광고 금지

---

## 15) MVP 즉시 산출물
1. `/sweetpotato` 단일 페이지
2. 초기값: 전국 고정 + spec 1개 고정
3. Summary + 90일 차트 + 최신성/신뢰도
4. 출처/제한 패널

확장 순서:
- 지역 드롭다운
- spec 확장(품종/등급/포장)
- 시장별 분포 탭
- KAMIS 소매 평균 토글
