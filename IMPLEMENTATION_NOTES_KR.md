# RealPrice 구현 메모 (현재 상태 / 리팩토링 계획 / 사용자 작업 필요사항)

## 1) 현재 구현 범위
- `/sweetpotato` 단일 페이지 UI 구현
- 상단 필터(지역/spec/기간/모드) + URL 쿼리 상태 동기화
- 요약 카드(확정/잠정/신뢰도/최신성)
- 메인 차트(final 실선, nowcast 점선, 최근 3일 음영, p10~p90 토글, 7일 중앙값 토글)
- 접힘 상세(시장 분포, 데이터 출처/제한)
- API 구현:
  - `GET /api/v1/sweetpotato/specs`
  - `GET /api/v1/regions?level=si_do`
  - `GET /api/v1/sweetpotato/summary`
  - `GET /api/v1/sweetpotato/timeseries`
  - `GET /api/v1/sweetpotato/market_breakdown`

## 2) 부족한 부분 및 리팩토링 계획
### 2.1 현재 한계
- 현재 데이터는 샘플(JSON) 기반이며, 실제 공공 API 연동 전 단계
- 인증/권한/요청 제한 제어 없음
- 차트가 커스텀 canvas로 구현되어 접근성/유지보수성이 낮을 수 있음
- 서버가 단일 파일(`app.py`) 구조라 서비스 확장성 제한

### 2.2 리팩토링 단계
1. **데이터 계층 분리**
   - `repository` 레이어로 API/DB 접근 모듈화
   - 샘플 JSON -> Postgres mart 테이블 조회로 전환
2. **백엔드 프레임워크 전환**
   - FastAPI로 라우팅/스키마(Pydantic) 정식화
   - OpenAPI 문서 자동화
3. **차트 컴포넌트 교체**
   - ECharts/Chart.js로 전환해 툴팁/접근성/확장성 개선
4. **배치 파이프라인 도입**
   - ETL 잡(`ingest_wholesale_*`, `ingest_kamis_daily`) 스케줄러 등록
5. **운영 품질 강화**
   - Redis 캐시 + 장애 알람 + SLA 모니터링

## 3) 사용자가 직접 준비해야 하는 항목(API 키/권한)
1. **공영도매시장 Open API 인증정보**
   - 정산정보 API
   - 실시간 경매정보 API
   - 표준코드 API
2. **KAMIS Open API 키**
   - 도소매 가격 및 지역별 조회 API
3. **배포 인프라 접근 권한**
   - 서버/DB/캐시(예: Postgres, Redis) 생성 권한
4. **운영 알림 채널 정보**
   - Slack Webhook 또는 이메일 SMTP 정보
5. **법적/정책 확인**
   - 데이터 이용약관, 재배포 허용 범위, 호출량 제한 준수 조건

## 4) 다음 액션 제안(바로 실행)
- [사용자] API 키 2종 전달(공영도매/KAMIS)
- [개발] 샘플 저장소를 실제 API 수집기로 교체
- [개발] mart 적재 스케줄 도입 + `/sweetpotato` 실데이터 연결
