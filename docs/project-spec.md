# Display Market Intelligence Agent PoC 프로젝트 명세서

## 1. 프로젝트명

| 항목 | 내용 |
| --- | --- |
| 프로젝트명 | Display Market Intelligence Agent PoC |
| 프로젝트 유형 | 기존 레거시 웹 시스템 연계형 AI Agent PoC |
| 주요 목적 | 디스플레이 판매, 수주, 재고, 고객사, 경쟁사 데이터를 기반으로 자연어 질의응답과 회의용 브리프북 생성을 지원 |
| 데이터 원칙 | 실제 업무 데이터 미사용, Synthetic Data만 사용 |

## 2. 프로젝트 목적

Display Market Intelligence Agent PoC는 디스플레이 사업 관련 데이터를 통합 조회하고, 사용자의 자연어 질문에 대해 분석 요약 답변을 제공하는 AI Agent 개념검증 프로젝트이다.

기존 Vue 및 Spring Boot 기반 레거시 웹 시스템에 Python AI Agent 서버를 추가로 연동하여, 기존 업무 화면은 유지하면서 AI 기반 질의응답과 브리프북 생성 기능을 실험한다.

## 3. 해결하려는 업무 문제

| 업무 문제 | 현재 어려움 | PoC에서 제공할 해결 방향 |
| --- | --- | --- |
| 판매 현황 파악 | 지역, 제품, 고객사별 실적을 여러 화면에서 따로 확인해야 함 | 자연어 질문으로 주요 판매 지표와 변동 요인을 요약 |
| 수주 현황 파악 | 수주 금액, 진행 단계, 고객사별 흐름을 빠르게 비교하기 어려움 | 고객사, 제품군, 기간별 수주 현황을 통합 요약 |
| 재고 리스크 확인 | 재고 과다, 부족, 장기 보유 품목을 즉시 찾기 어려움 | 재고 수준과 위험 품목을 조건별로 분석 |
| 고객사 대응 준비 | 회의 전 고객사별 판매, 수주, 재고, 이슈를 수작업으로 정리해야 함 | 고객사별 회의용 브리프북 자동 생성 |
| 경쟁사 동향 확인 | 경쟁사 뉴스와 내부 지표를 함께 해석하기 어려움 | Synthetic 경쟁사 뉴스 기반 시장 동향 요약 |

## 4. 시스템 전체 구성

### 4.1 전체 아키텍처

| 계층 | 기술 | 역할 |
| --- | --- | --- |
| Frontend | Vue 2.6.10 | 사용자 질의 입력, 답변 표시, 브리프북 생성 요청, 결과 다운로드 UI |
| Backend | Spring Boot 2.1.18.RELEASE, Java 8 | Vue 요청 수신, 인증/권한 연계 가정, Python Agent API 중계 |
| Agent Server | Python 3.12, FastAPI | AI Agent API 제공, LangGraph 실행, Tool 호출, LLM API 호출 |
| Agent Framework | LangGraph, LangChain | 질의 분류, Tool 선택, 분석 흐름 제어, 응답 생성 |
| Tool Layer | MCP Tool 또는 MCP 스타일 Python Tool 함수 | 판매, 수주, 재고, 고객사, 경쟁사 뉴스 데이터 조회 및 분석 |
| Database | PostgreSQL | Synthetic Data 저장 |
| LLM Provider | 외부 LLM API | 자연어 이해, 요약, 브리프북 문장 생성 |

### 4.2 요청 흐름

| 단계 | 흐름 | 설명 |
| --- | --- | --- |
| 1 | 사용자 -> Vue | 자연어 질문 또는 브리프북 생성 조건 입력 |
| 2 | Vue -> Spring Boot | 기존 웹 시스템 API 형태로 요청 전달 |
| 3 | Spring Boot -> Python FastAPI | Agent API로 요청 중계 |
| 4 | Python Agent -> LangGraph | 질문 유형 분석 및 실행 그래프 시작 |
| 5 | LangGraph -> Tool Layer | 필요한 MCP Tool 또는 MCP 스타일 Tool 함수 호출 |
| 6 | Tool Layer -> PostgreSQL | Synthetic Data 조회 |
| 7 | Python Agent -> LLM API | 조회 결과를 기반으로 자연어 답변 또는 브리프북 생성 |
| 8 | Python FastAPI -> Spring Boot -> Vue | 최종 응답 반환 및 화면 표시 |

## 5. 포함 범위

| 구분 | 포함 내용 |
| --- | --- |
| 자연어 질의응답 | 판매, 수주, 재고, 고객사, 경쟁사 뉴스 관련 질문 답변 |
| 데이터 분석 요약 | 기간별, 지역별, 제품군별, 고객사별 주요 지표 요약 |
| 회의용 브리프북 | 특정 고객사 또는 주제 기준 브리프북 초안 생성 |
| Synthetic Data | 판매, 수주, 재고, 고객사, 경쟁사 뉴스 샘플 데이터 구성 |
| 레거시 연동 구조 | Vue -> Spring Boot -> Python Agent API 중계 구조 |
| Agent Workflow | LangGraph 기반 질의 분류, Tool 호출, 응답 생성 흐름 |
| Tool Layer | MCP Tool 또는 MCP 스타일 Python Tool 함수 구현 |
| API 연동 | Spring Boot 중계 API, Python Agent API 최소 구현 |

## 6. 제외 범위

| 구분 | 제외 내용 |
| --- | --- |
| ML 수요예측 | 머신러닝 기반 수요예측 모델 개발 제외 |
| 실데이터 연동 | 실제 판매, 수주, 재고, 고객사, 경쟁사 데이터 사용 제외 |
| 운영 배포 | 운영 환경 배포, 고가용성, 모니터링 체계 구축 제외 |
| 권한 체계 고도화 | 실제 사내 권한, 조직, 직무별 접근제어 상세 구현 제외 |
| 대규모 데이터 처리 | 대용량 배치, 스트리밍, 데이터 웨어하우스 연계 제외 |
| 문서 완성 자동화 | 완성형 PPT/Word 디자인 자동 생성은 1차 범위에서 제외 |
| 외부 뉴스 실시간 수집 | 실제 경쟁사 뉴스 크롤링 및 상용 뉴스 API 연동 제외 |

## 7. 주요 사용자 질문 예시

| 분류 | 질문 예시 |
| --- | --- |
| 판매 | "2026년 2분기 OLED 패널 판매 실적을 지역별로 요약해줘." |
| 판매 | "최근 3개월 동안 매출이 가장 많이 증가한 제품군은 뭐야?" |
| 수주 | "A사향 수주 현황과 주요 리스크를 정리해줘." |
| 수주 | "이번 분기 신규 수주가 감소한 고객사를 찾아줘." |
| 재고 | "재고가 과다한 제품군과 예상 원인을 알려줘." |
| 재고 | "북미 지역 출하 대기 재고 중 리스크가 높은 항목을 요약해줘." |
| 고객사 | "B사 회의 전에 봐야 할 판매, 수주, 재고 포인트를 정리해줘." |
| 경쟁사 | "최근 경쟁사 뉴스 기준으로 주의할 시장 이슈를 요약해줘." |
| 브리프북 | "C사 임원 미팅용 브리프북 초안을 만들어줘." |

> 고객사명은 PoC 문서와 Synthetic Data에서 `A사`, `B사`, `C사` 등 가상 명칭만 사용한다.

## 8. 주요 기능 목록

| 기능 ID | 기능명 | 설명 | 담당 시스템 |
| --- | --- | --- | --- |
| F-001 | 자연어 질문 입력 | 사용자가 업무 질문을 입력 | Vue |
| F-002 | Agent 질의 중계 | Vue 요청을 Python Agent API로 전달 | Spring Boot |
| F-003 | 질문 유형 분류 | 판매, 수주, 재고, 고객사, 경쟁사, 브리프북 유형 판별 | Python Agent |
| F-004 | 데이터 조회 Tool 호출 | 질의 유형에 맞는 Tool 실행 | LangGraph, Tool Layer |
| F-005 | 분석 요약 생성 | 조회 결과를 자연어로 요약 | Python Agent, LLM API |
| F-006 | 답변 화면 표시 | Agent 답변, 근거 데이터, 후속 질문 표시 | Vue |
| F-007 | 브리프북 생성 | 고객사 또는 주제 기준 회의용 요약 문서 생성 | Python Agent |
| F-008 | Synthetic Data 관리 | PoC용 샘플 데이터 생성 및 적재 | PostgreSQL, Python Script |
| F-009 | Agent 실행 로그 | 질문, Tool 호출, 응답 상태 로그 기록 | Spring Boot, Python Agent |

## 9. 데이터 테이블 목록

| 테이블명 | 설명 | 주요 컬럼 예시 |
| --- | --- | --- |
| `sales_records` | 판매 실적 데이터 | `id`, `sales_date`, `region`, `customer_id`, `product_id`, `quantity`, `revenue`, `currency` |
| `order_records` | 수주 데이터 | `id`, `order_date`, `customer_id`, `product_id`, `order_amount`, `order_status`, `expected_ship_date` |
| `inventory_records` | 재고 데이터 | `id`, `snapshot_date`, `warehouse_region`, `product_id`, `stock_quantity`, `safety_stock`, `inventory_status` |
| `customers` | 고객사 마스터 | `id`, `customer_name`, `region`, `industry_segment`, `tier`, `account_owner` |
| `products` | 제품 마스터 | `id`, `product_name`, `product_family`, `display_type`, `size_inch`, `resolution` |
| `competitor_news` | 경쟁사 뉴스 Synthetic Data | `id`, `news_date`, `competitor_name`, `title`, `summary`, `market_impact_level` |
| `agent_query_logs` | Agent 질의 로그 | `id`, `request_time`, `user_query`, `query_type`, `tool_names`, `response_status` |
| `briefbook_requests` | 브리프북 생성 이력 | `id`, `request_time`, `topic`, `customer_id`, `period_start`, `period_end`, `status` |

## 10. MCP Tool 목록

| Tool 이름 | 입력 예시 | 출력 예시 | 설명 |
| --- | --- | --- | --- |
| `get_sales_summary` | `period`, `region`, `product_family`, `customer_id` | 판매량, 매출, 증감률 | 판매 실적 요약 조회 |
| `get_order_pipeline` | `period`, `customer_id`, `order_status` | 수주 금액, 단계별 건수 | 수주 현황 및 파이프라인 조회 |
| `get_inventory_risk` | `snapshot_date`, `region`, `product_family` | 과다/부족 재고 목록, 리스크 등급 | 재고 리스크 분석 |
| `get_customer_overview` | `customer_id`, `period` | 고객사 기본 정보, 판매/수주 요약 | 고객사 단위 종합 조회 |
| `get_competitor_news_summary` | `period`, `competitor_name`, `impact_level` | 경쟁사 뉴스 요약, 시장 영향 | Synthetic 경쟁사 뉴스 요약 |
| `generate_briefbook_outline` | `customer_id`, `topic`, `period` | 브리프북 목차, 핵심 메시지 | 회의용 브리프북 초안 구성 |
| `search_display_market_context` | `keyword`, `period` | 관련 판매/수주/재고/뉴스 항목 | 복합 키워드 기반 데이터 검색 |
| `get_kpi_snapshot` | `period`, `region` | 매출, 수주, 재고 KPI | 대시보드형 KPI 스냅샷 생성 |

## 11. API 목록

### 11.1 Spring Boot API

| Method | Path | 설명 | 요청 대상 |
| --- | --- | --- | --- |
| `POST` | `/api/agent/chat` | 사용자 자연어 질문을 Python Agent로 중계 | Vue |
| `POST` | `/api/agent/briefbook` | 브리프북 생성 요청을 Python Agent로 중계 | Vue |
| `GET` | `/api/agent/history` | 사용자 질의 이력 조회 | Vue |
| `GET` | `/api/health/agent` | Python Agent 서버 상태 확인 | Vue 또는 운영 확인 |

### 11.2 Python FastAPI API

| Method | Path | 설명 | 호출 주체 |
| --- | --- | --- | --- |
| `POST` | `/agent/chat` | LangGraph Agent 실행 후 답변 반환 | Spring Boot |
| `POST` | `/agent/briefbook` | 회의용 브리프북 초안 생성 | Spring Boot |
| `GET` | `/agent/health` | Agent 서버 상태 확인 | Spring Boot |
| `GET` | `/tools` | 사용 가능한 Tool 목록 반환 | Spring Boot 또는 개발자 |

### 11.3 API 요청/응답 예시

| API | 요청 주요 필드 | 응답 주요 필드 |
| --- | --- | --- |
| `/api/agent/chat` | `message`, `userId`, `sessionId` | `answer`, `queryType`, `usedTools`, `evidence`, `followUpQuestions` |
| `/api/agent/briefbook` | `topic`, `customerId`, `periodStart`, `periodEnd` | `title`, `sections`, `keyMessages`, `sourceSummary` |

## 12. 4명 역할 분담

| 역할 | 담당자 | 주요 책임 |
| --- | --- | --- |
| Backend 담당 | 팀원 1 | Spring Boot 2.1.18 기반 중계 API, Agent API 연동, 로그 저장 |
| Frontend 담당 | 팀원 2 | Vue 2.6.10 기반 질의 화면, 답변 화면, 브리프북 요청 UI |
| Agent 담당 | 팀원 3 | FastAPI, LangGraph Workflow, Tool 호출, LLM 응답 생성 |
| Data/PM 담당 | 팀원 4 | Synthetic Data 설계, PostgreSQL 테이블, 발표 자료, 일정 관리 |

## 13. 6주 개발 일정

| 주차 | 목표 | 주요 작업 | 산출물 |
| --- | --- | --- | --- |
| 1주차 | 요구사항 및 구조 확정 | 프로젝트 범위 정의, 데이터 항목 정의, API 초안 작성 | 프로젝트 명세서, ERD 초안, API 초안 |
| 2주차 | Synthetic Data 및 DB 준비 | PostgreSQL 테이블 생성, Synthetic Data 생성/적재 스크립트 작성 | DB 스키마, 샘플 데이터 |
| 3주차 | Backend 및 Agent 기본 연동 | Spring Boot 중계 API, FastAPI Agent API, Health Check 구현 | API 연동 데모 |
| 4주차 | Tool Layer 및 LangGraph 구현 | MCP 스타일 Tool 함수, LangGraph 질의 분류 및 Tool 호출 흐름 구현 | 자연어 질의응답 1차 데모 |
| 5주차 | Frontend 화면 및 브리프북 기능 | Vue 질의 UI, 답변 표시, 브리프북 생성 화면 구현 | 통합 화면 데모 |
| 6주차 | 통합 테스트 및 발표 준비 | 시나리오 테스트, 오류 보완, 발표 자료 및 최종 데모 정리 | 최종 PoC, 발표 자료, 시연 시나리오 |

## 14. 최종 산출물

| 산출물 | 설명 |
| --- | --- |
| 프로젝트 명세서 | PoC 목적, 범위, 아키텍처, 일정, 역할 정의 문서 |
| DB 스키마 | PostgreSQL 테이블 정의 및 관계 |
| Synthetic Data | 판매, 수주, 재고, 고객사, 경쟁사 뉴스 샘플 데이터 |
| Vue 화면 | 자연어 질문 입력, 답변 표시, 브리프북 생성 요청 화면 |
| Spring Boot API | Vue 요청을 Python Agent로 중계하는 Java 8 호환 API |
| Python Agent Server | FastAPI 기반 Agent API 서버 |
| LangGraph Workflow | 질문 유형 분류, Tool 호출, 응답 생성 그래프 |
| MCP Tool 함수 | 데이터 조회 및 분석용 Tool 함수 |
| 브리프북 생성 기능 | 고객사 또는 주제별 회의용 요약 초안 |
| 테스트 시나리오 | 주요 사용자 질문별 실행 및 검증 케이스 |
| 발표 자료 | 프로젝트 개요, 아키텍처, 데모 시나리오, 기대 효과 |

## 15. 발표용 한 줄 설명

> Display Market Intelligence Agent는 기존 레거시 웹 시스템에 Python AI Agent 서버를 연동하여, Synthetic 디스플레이 사업 데이터를 자연어로 분석하고 회의용 브리프북까지 생성하는 AI Agent PoC입니다.

