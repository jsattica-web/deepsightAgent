# GPT 모델 적용 시 agent.py Tool AS-IS / TO-BE

## 1. 목적과 기준

[판매 Tool 상세 설계](sales-trend-tool-as-is-to-be.md)의 질문 해석·조회·답변 생성 책임 분리 방향을 6개 Tool 전체에 적용한다. 최종 구조는 [다중 Tool 호출 방향](openai-llm-multi-tool-direction.md)을 기준으로 삼는다.

- 확인일: 2026-09-08
- 코드 기준: 작업 디렉터리의 [agent.py](../agent-python/app/agent/agent.py), [tool_schema.py](../agent-python/app/schemas/tool_schema.py), [common.py](../agent-python/app/schemas/common.py), app/tools 내 조회 함수
- 이 문서는 변경 설계이며 Python 구현을 변경하지 않는다.
- **참고 문서의 기존 AS-IS와 현재 파일은 다르다.** 현재는 GPT 연결과 판매·수주 입력 변경이 일부 진행된 상태다. 아래에서 기존 구조, 현재 전환 상태, 최종 TO-BE를 구분한다.
- GPT의 구체적인 모델 선정은 이 문서 범위에 포함하지 않는다.

## 2. 전체 비교

| 구분 | 기존 구조 | 현재 파일 | TO-BE |
| --- | --- | --- | --- |
| 모델 | RuleBasedChatModel | ChatOpenAI를 llm으로 생성하고 create_agent(model=llm)에 연결 | 검증한 모델 ID·설정을 외부 설정으로 관리 |
| Tool 선택 | choose_tool_name()의 키워드 우선순위 | 규칙 클래스는 남아 있으나 build_agent()는 llm 사용 | 질문에 필요한 복수 Tool 선택 및 실행 계획 검증 |
| 입력 | question 문자열 | 판매·수주는 구조화 인자, 나머지 4개는 question | 검증된 업무 인자 |
| 조회 계층 | 단일 제품·고객 중심 | 기존 Request와 SQL이 유지됨 | Wrapper·Request·SQL·응답 모델을 함께 정합화 |
| 반환 | build_*_answer()의 화면 응답 | 판매·수주만 하위 결과 직접 반환 | 공통 업무 결과 반환 후 최종 응답을 별도로 조립 |
| 브리핑 | Wrapper 내부에서 4개 조회 순차 실행 | 동일 | output_mode="briefing"에 따른 최종 표현 단계 |
| 최종 응답 | 마지막 ToolMessage를 그대로 전달 | GPT 마지막 메시지를 JSON 파싱 | 모든 Tool 결과 종합 후 화면 계약 검증 |

기존 흐름:

```text
질문 → 규칙 라우터 → Tool(question)
     → 키워드/고정값으로 Request 생성 → 조회·도메인 계산
     → build_*_answer() → 화면 응답
```

목표 흐름:

```text
질문 + 기준일/데이터 범위
  → GPT의 Tool 선택·구조화 인자 생성
  → 서버의 스키마·실행 계획 검증
  → 독립적인 데이터 Tool 실행
  → 결과 정규화 및 호출 ID별 보관
  → output_mode에 따라 분석·비교·브리핑 형식 선택
  → GPT 교차분석 + 서버의 표·차트 조립
  → 최종 응답 스키마 검증 → 화면
```

QueryPlan은 Structured Outputs로 생성할 실행 계획 객체다. tools, 제품·고객·기간, Tool별 인자, output_mode(analysis/comparison/briefing)를 포함한다. 계획에서 미지정 고객을 빈 목록으로 표현했다면 실행 전에 null로 정규화한다. 미확정 기간은 정책 적용 또는 추가 질문 후 확정한다. GPT 연결만으로 자동 생성되거나 서버의 병렬 실행·의존성 관리가 완성되는 것은 아니다.

## 3. 현재 전환 상태에서 먼저 맞출 부분

| 위치 | 현재 확인 사항 | TO-BE 조치 |
| --- | --- | --- |
| sales_trend_tool | product_groups 리스트를 product_group에 전달하지만 SalesTrendRequest.product_group은 str | 복수 필드를 Request·SQL까지 구현하거나 단일 인자 형태를 유지하는 임시 어댑터 적용 |
| sales_trend_tool | customer_ids, group_by, metrics는 기존 Request에 없는 필드 | 실제 요청 필드·검증·조회 로직 추가. 현재 모델은 extra 금지 설정이 없어 미정의 필드가 무시될 수 있음 |
| order_status_tool | product_groups=product_groups 뒤 쉼표 누락 | 문법 오류 수정 후 인터페이스 검증 |
| order_status_tool | 기존 Request는 product_group, customer_id, status 단수형 | 복수 인자에 맞게 하위 계층 확장. 현재 필수 product_group도 전달되지 않음 |
| order_status_tool | group_by_customer를 입력받지만 Request에 전달하지 않음 | 요청 필드·SQL 집계·결과 차원까지 연결 |
| RuleBasedChatModel._generate() | Tool 인자를 항상 {"question": question}으로 구성 | 유지할 경우 새 스키마를 만드는 어댑터 필요. GPT 운영 경로에서는 제거하거나 테스트 전용으로 격리 |
| build_agent() | “Select the best tool and return its JSON result.” 프롬프트 | 복수 조회·추가 조회·근거 기반 종합·실패 표시 정책으로 변경 |
| run_agent() / parse_agent_response() | 마지막 content를 json.loads()로 파싱 | JSON 파싱뿐 아니라 최종 응답 모델 검증 및 실패 처리 |
| 모델·의존성 | 모델 문자열은 gpt-5o-mini, requirements.txt에 langchain-openai 명시 없음 | 모델 ID의 실제 사용 가능 여부 확인, langchain-openai 의존성 명시 및 호환성 검증 |

위 내용은 정적 코드 확인 결과다. 현재 쉼표 누락은 모듈 로딩을 막는 문법 문제이며, GPT 연동이 정상 동작한다고 볼 수 없다. 모델 문자열의 유효성이나 API 접근 가능 여부는 실행으로 확인하지 않았다.

## 4. 공통 입력 설계

- 날짜: YYYY-MM-DD, 월: YYYY-MM. 형식과 실제 달력 날짜, 시작 ≤ 종료를 서버에서 검증한다.
- “최근 6개월”은 요청 기준일·데이터 최신 월·당월 포함 여부 정책으로 확정한다. 고정 DEFAULT_*를 자연어 해석의 대체값으로 쓰지 않는다.
- 기간이나 고객이 불명확하면 명시된 기본 정책을 알리거나 추가 질문한다. 고객 누락을 CUST_A로 자동 치환하지 않는다.
- product_groups는 명시적인 비어 있지 않은 목록으로 정의한다. “전체”는 서버의 제품 목록으로 해석하고, 임의 문자열이나 빈 목록을 전체 조회로 취급하지 않는다.
- customer_ids=null, statuses=null은 해당 필터 없음이다. 빈 목록은 입력 오류로 처리한다.
- group_by, metrics, statuses, sections는 허용값을 제한한다. 지원하지 않는 집계나 지표를 받기만 하고 무시하지 않는다.
- 리스트 기본값은 스키마의 default_factory 등을 사용한다.
- Pydantic 업무 검증과 모델에 전송되는 Tool JSON Schema를 함께 확인한다. 미정의 필드를 거부하도록 설계한다.

Function Calling은 모델이 인자를 제안하고 애플리케이션이 실행한 결과를 모델에 돌려주는 흐름이다. strict 모드를 적용할 때는 객체의 additionalProperties=false와 모든 속성의 required 등록이 필요하며, 선택 의미는 nullable 값으로 표현한다. 실제 전송 스키마를 확인해야 한다. [OpenAI Function Calling 공식 문서](https://developers.openai.com/api/docs/guides/function-calling)

## 5. sales_trend_tool

### AS-IS

참고 문서의 기존 형태는 sales_trend_tool(question: str)이다. 기간은 2026-01~2026-06, 고객은 None으로 고정하고 제품군과 고객별 집계만 키워드로 추출했다.

현재 파일은 아래 입력으로 변경 중이며 하위 SalesTrendRequest는 아직 단수형이다.

```python
sales_trend_tool(
    start_month: str,
    end_month: str,
    product_groups: list[str],
    customer_ids: list[str] | None = None,
    group_by: list[str] = ["month"],
    metrics: list[str] = ["qty", "revenue", "asp"],
)
```

### TO-BE

입력 이름은 현재 전환 방향을 유지하되 다음 계약을 실제 구현한다.

| 인자 | 허용값·의미 |
| --- | --- |
| start_month, end_month | 조회 시작·종료 월 |
| product_groups | 제품군 목록 |
| customer_ids | 고객 목록 또는 필터 없음 |
| group_by | month, customer, product_group의 조합 |
| metrics | qty, revenue, asp 중 필요한 지표 |

- SalesTrendRequest와 get_sales_trend()를 복수 필터·허용된 집계 기준에 맞게 확장한다.
- SalesTrendPoint에 필요한 product_group 차원을 추가하고, 월을 생략하는 집계를 지원한다면 month 필수 여부도 수정한다.
- 반환은 조회 조건, data, aggregates, 도메인 계산, warnings를 포함한다.
- ASP는 매출 합계 / 수량 합계로 계산한다. 월별 ASP의 단순 평균을 전체 ASP로 쓰지 않는다.
- 고객별 데이터에서 첫 행과 마지막 행을 비교해 전체 증감률을 만들지 않는다. 같은 집계 차원과 기간을 맞춘다.
- build_sales_answer()는 Tool 밖의 최종 응답 조립 단계로 이동한다.

호출 예:

```json
{
  "start_month": "2026-04",
  "end_month": "2026-06",
  "product_groups": ["Mobile OLED", "TV OLED"],
  "customer_ids": ["CUST_A"],
  "group_by": ["month", "product_group"],
  "metrics": ["qty", "revenue", "asp"]
}
```

## 6. order_status_tool

### AS-IS

현재는 start_date, end_date, product_groups, customer_ids, statuses, group_by_customer를 입력받도록 변경 중이다. 그러나 OrderStatusRequest는 단일 product_group, customer_id, status만 지원하며 get_order_status() 결과도 월별 집계 중심이다.

### TO-BE

```python
def order_status_tool(
    start_date: str,
    end_date: str,
    product_groups: list[str],
    customer_ids: list[str] | None,
    statuses: list[str] | None,
    group_by_customer: bool,
    group_by_product_group: bool,
) -> dict[str, Any]:
    ...
```

- statuses 허용값: REQUESTED, CONFIRMED, DELAYED, SHIPPED, CANCELLED.
- Request와 get_order_status()에 복수 조건과 group_by_customer를 구현한다.
- 고객별 집계 시 OrderStatusPoint에 customer_id, customer_name을 추가한다.
- 제품별 집계도 목표 범위에 포함한다. group_by_product_group을 Request·SQL에 추가하고 결과에 product_group을 보존한다. 이 필드는 방향 문서의 제품별 집계 요구를 구체화한 제안이다.
- 기존 total_orders, total_order_qty, 상태별 건수, risk_order_count를 유지한다.
- REQUESTED는 결과의 pending_count와 연결되는 계약을 설명한다.
- 수주량을 매출로 간주하지 않는다. 판매와 비교할 때 월·고객·제품 범위를 맞춘다.
- build_order_answer()는 최종 조립 단계로 이동한다.

호출 예:

```json
{
  "start_date": "2026-04-01",
  "end_date": "2026-06-30",
  "product_groups": ["Mobile OLED"],
  "customer_ids": null,
  "statuses": ["DELAYED", "CONFIRMED"],
  "group_by_customer": true,
  "group_by_product_group": false
}
```

## 7. inventory_risk_tool

### AS-IS

```python
inventory_risk_tool(question: str)
# inventory_month=DEFAULT_INVENTORY_MONTH ("2026-06")
# product_group=extract_product_group(question)
# get_inventory_risk() → build_inventory_answer()
```

get_inventory_risk()는 기준 월을 포함한 최근 3개월을 조회한다. 현재 고객 필터는 없다.

### TO-BE

```python
def inventory_risk_tool(
    start_month: str,
    end_month: str,
    product_groups: list[str],
) -> dict[str, Any]:
    ...
```

- InventoryRiskRequest와 조회 함수를 시작·종료 월 및 복수 제품군 조건에 맞게 확장한다. 기존 inventory_month 단독 요청은 호환 어댑터에서 최근 3개월 범위로 변환할 수 있다.
- 제품별 리스크 비교를 위해 제품군별·월별 행과 제품군이 명시된 위험 신호를 반환한다.
- 고정 최근 3개월 조회를 요청한 월별 기간 조회로 변경한다. 판매·수주와 같은 기간으로 조회하고 누락 월을 표시한다.
- 기말재고·안전재고·생산량·판매량과 함께 부족량·과잉량을 반환한다. 안전재고 기준 부족량=max(안전재고-기말재고, 0), 과잉량=max(기말재고-안전재고, 0) 등 계산 기준을 명시한다. 주문 대비 부족량과는 구분한다.
- 고객별 재고가 없는 현재 데이터 의미를 유지한다. 특정 고객의 판매 감소를 그 고객의 재고 증가로 단정하지 않는다.
- 안전재고 대비 과잉·부족 계산은 조회 계층에서 수행하고 화면용 문장은 외부에서 작성한다.

호출 예:

```json
{
  "start_month": "2026-04",
  "end_month": "2026-06",
  "product_groups": ["TV OLED"]
}
```

## 8. customer_profile_tool

### AS-IS

```python
customer_profile_tool(question: str)
# customer_id=extract_customer_id(question): 없으면 CUST_A
# start_month/end_month: 고정
# get_customer_profile() → build_customer_answer()
```

### TO-BE

```python
def customer_profile_tool(
    customer_id: str,
    start_month: str,
    end_month: str,
) -> dict[str, Any]:
    ...
```

- 단일 고객 조회는 기존 CustomerProfileRequest를 재사용한다. 기간과 고객을 Wrapper 입력으로 받는다.
- 복수 고객 비교는 서버가 고객별로 호출해 결과를 모은다. 일괄 API가 필요해질 때 customer_ids를 확장한다.
- 고객명만 제시된 경우 서버의 고객 식별 절차로 ID를 확인한다. 현재 코드에는 이름 검색 전용 Tool이 없으므로 GPT가 ID를 만들어서는 안 된다.
- “고객별 매출”은 판매 Tool, 고객의 등급·지역·주요 적용 분야는 프로필 Tool로 구분한다.
- 결과의 프로필과 기간별 판매·수주 요약은 유지하며, 최종 화면 응답은 밖에서 조립한다.

호출 예:

```json
{
  "customer_id": "CUST_A",
  "start_month": "2026-04",
  "end_month": "2026-06"
}
```

## 9. competitor_news_tool

### AS-IS

question에서 회사·영향도·키워드·제품군을 추출한다. 기간은 고정하고 category=None을 전달한다. search_competitor_news()는 DB 조회와 NAVER 최근 3일 검색을 합쳐 반환하며 build_news_answer()가 화면 응답을 만든다.

### TO-BE

```python
def competitor_news_tool(
    start_date: str,
    end_date: str,
    companies: list[str] | None,
    category: str | None,
    impact_level: str | None,
    keyword: str | None,
    product_group: str | None,
) -> dict[str, Any]:
    ...
```

- 기존 CompetitorNewsRequest의 필드를 구조화 입력으로 노출한다. impact_level은 HIGH, MEDIUM, LOW 또는 null로 제한한다.
- 제품군은 기존 뉴스 검색 의미를 유지한다. OLED를 Mobile OLED로 임의 축소하지 않는다.
- DB의 요청 기간과 NAVER의 최근 3일 범위가 다름을 결과 메타데이터에 명시한다.
- 요청 기간 밖 NAVER 기사는 해당 기간 분석에서 제외하거나 별도의 최신 참고 뉴스로 분리한다. 날짜 인자를 추가하는 것만으로 NAVER 검색 범위가 바뀌지는 않는다.
- source=DB/NAVER를 유지하며 NAVER 장애 등 부분 실패를 warnings에 기록한다.
- 원문 링크가 필요하면 CompetitorNewsPoint와 수집 결과 매핑을 추가한다. 현재 응답 모델에는 URL 필드가 없다.
- 도메인 뉴스 결과를 반환하고 최종 종합 설명은 외부에서 작성한다.

호출 예:

```json
{
  "start_date": "2026-04-01",
  "end_date": "2026-06-30",
  "companies": ["BOE", "CSOT"],
  "category": null,
  "impact_level": "HIGH",
  "keyword": "OLED",
  "product_group": "OLED"
}
```

## 10. briefing_report_tool

### AS-IS

```text
briefing_report_tool(question)
  → 고객·제품 추출
  → get_sales_trend()
  → get_order_status()
  → get_inventory_risk()
  → search_competitor_news()
  → BriefingRequest(tool_results=...)
  → create_briefing_report()
  → build_briefing_answer()
```

항상 네 조회를 Wrapper 내부에서 수행한다. create_briefing_report() 자체는 DB를 조회하지 않고 전달된 결과를 섹션별로 조립한다.

### TO-BE

최종 목표는 briefing_report_tool을 모델의 데이터 Tool 목록에서 제외하고 QueryPlan.output_mode="briefing"으로 처리하는 것이다. create_briefing_report()는 서버 내부 조립 함수로 재사용할 수 있다.

과도기에 Wrapper를 유지할 경우의 서버 내부 입력 예시:

```python
def briefing_report_tool(
    topic: str,
    customer_id: str | None,
    start_date: str,
    end_date: str,
    sections: list[str],
) -> dict[str, Any]:
    ...
```

- sections는 sales, orders, inventory, competitor_news, recommended_actions 중 선택한다.
- 상위 오케스트레이터가 필요한 선행 조회를 실행하고 현재 요청의 결과 저장소에 보관한다.
- 내부 조립 단계에서 서버가 저장소에서 검증된 tool_results를 주입해 BriefingRequest를 만든다. 위 시그니처만 변경하면 결과 주입이 완성되는 것은 아니며 실행 컨텍스트 연결이 필요하다.
- tool_results의 숫자·기사 원문을 모델이 입력 인자로 다시 작성하게 하지 않는다.
- 기존 키 sales, orders, inventory, competitor_news를 유지한다.
- 같은 영역을 복수 호출했다면 섹션별 결과 합성 어댑터가 필요하다. 기존 조립기에 단순 리스트를 넣으면 요약을 읽지 못한다.
- 선행 Tool과 브리핑 조립을 같은 병렬 묶음에서 실행하지 않는다.
- 실패·누락된 섹션을 표시하고 성공한 결과로 부분 브리핑을 작성한다.
- 고정 섹션 조립은 create_briefing_report()가, 교차분석 설명은 상위 GPT가 담당한다.

## 11. Tool 결과와 최종 화면 응답

### 업무 결과

기존 ToolResponse의 summary, data, insights, risk_signals, chart_data, actions를 활용하면서 실행기가 아래 메타데이터를 정규화한다. 아래는 **신규 목표 형식**이며 현재 응답에 모두 존재하지 않는다.

```json
{
  "tool_name": "sales_trend_tool",
  "call_id": "call_sales_1",
  "status": "success",
  "filters": {
    "start_month": "2026-04",
    "end_month": "2026-06",
    "product_groups": ["Mobile OLED"]
  },
  "data": [],
  "aggregates": {},
  "summary": "조건에 해당하는 데이터가 없습니다.",
  "insights": [],
  "risk_signals": [],
  "chart_data": {},
  "actions": [],
  "warnings": []
}
```

빈 조회는 success와 빈 data로, 실행 실패는 error로 구분한다. 하위 tool_name은 get_sales_trend 등 실제 함수 이름이므로 외부 Tool 이름과 매핑한다. 문자열 위험 신호와 재고의 객체형 위험 신호도 정규화 규칙을 정한다.

### 오류

```json
{
  "tool_name": "sales_trend_tool",
  "call_id": "call_sales_1",
  "status": "error",
  "error_code": "SALES_QUERY_FAILED",
  "message": "판매 데이터를 조회하지 못했습니다.",
  "retryable": true
}
```

기존 ErrorResponse에는 message와 details만 있어 오류 코드·재시도 가능 여부를 실행기 또는 공통 모델에 추가해야 한다. 입력 오류는 재시도 가능한 DB 장애와 구분한다.

현재 일부 build_*_answer() 경로는 하위 오류도 빈 data로 취급한 뒤 success_answer()로 감쌀 수 있다. 목표 구조에서는 하위 status를 먼저 검사한다.

### 최종 화면 계약

Tool 업무 결과를 /agent/chat 응답으로 그대로 반환하지 않는다. success_answer()가 사용하는 다음 형식을 최종 조립 단계에서 유지한다.

```text
status, message, error
data.answer
data.summary
data.tables
data.charts
data.insights
data.risk_signals
data.actions
```

표와 차트 값은 검증된 Tool 데이터에서 만든다. GPT는 근거를 바탕으로 설명을 작성하고 서버가 최종 구조를 검증한다. 방향 문서에 맞춰 data.tools_used와 data.limitations를 추가한다. tools_used에는 실제 성공한 Tool만 기록하고 실패·자료 범위·추정의 한계는 limitations에 표시한다. 새 필드는 Spring Boot·Vue 계약과 함께 반영한다. 전체 호출·실패 이력은 실행 로그에 기록한다. 계획과 최종 응답에는 Structured Outputs를 적용하고 서버 검증을 유지한다.

### 교차분석용 정규화

방향 문서의 month/date, product_group, customer_id, customer_name, metric, value, unit, source_tool을 공통 차원으로 제공한다. 각 Tool 원본은 보관하고 실행기의 정규화 단계에서 지표별 행으로 변환한다.

판매·수주는 월/고객/제품, 판매·재고는 월/제품 단위로 맞춘다. 통화·수량 단위와 집계 범위가 다른 값은 직접 비교하지 않는다. 확정 수주와 기말재고만으로 예약·할당을 반영한 가용 재고를 확정할 수 없으므로 계산 가정과 추가 필요 데이터를 표시한다. 뉴스와 내부 지표 비교에서는 확인된 사실, 상관관계, 추정 원인, 추가로 필요한 데이터를 구분한다.

## 12. agent.py 주변 변경 범위

| 파일/함수 | 변경 내용 |
| --- | --- |
| agent.py의 데이터 Tool 5개와 브리핑 | 데이터 입력 구조화·업무 결과 반환, 브리핑은 output_mode 기반 내부 조립으로 이동 |
| tool_schema.py | 판매·수주·재고 복수 조건과 결과 차원 확장, 허용값·범위 검증 |
| tools/sales_tool.py, order_tool.py, inventory_tool.py | 새 조건의 필터·집계·계산·정렬 구현 |
| tools/customer_tool.py | 단일 고객 의미 유지, 필요 시 복수 호출 결과 조합 |
| tools/news_tool.py | 실제 조회 범위·출처·부분 실패 전달, 기간 정책 적용 |
| tools/briefing_tool.py | 주입된 결과 조립, 복수 결과·실패 섹션 처리 |
| schemas/common.py | 업무 결과 정규화 및 오류 계약 확장 |
| build_agent() | 데이터 Tool 5개 등록, QueryPlan·output_mode·복수 호출과 종합 정책 |
| run_agent() 및 실행기 | 결과 보관·의존성·타임아웃·최종 검증 |
| build_*_answer(), success_answer() | 최종 응답 조립 계층으로 이동·재사용 |
| choose_tool_name(), extract_*(), DEFAULT_* | GPT 경로 의존 제거, 필요한 코드 정규화만 서버에 유지 |
| main.py와 직접 Tool API 소비자 | 공유 Request 변경에 따른 기존 단수 요청 호환성 검토 |
| requirements.txt 및 환경 설정 | OpenAI 연동 패키지·모델 설정 정합화 |

기존 단수형 API를 유지해야 한다면 호환 어댑터나 별도 버전 스키마를 둔다. agent.py의 함수 시그니처만 먼저 바꾸면 현재와 같은 계층 간 불일치가 발생한다.

## 13. 다중 Tool 실행 예

질문:

> 2026년 2분기 Mobile OLED의 고객별 판매와 지연 수주를 비교하고 브리핑해줘.

1. 판매: 2026-04~06, Mobile OLED, group_by=["month","customer"].
2. 수주: 2026-04-01~06-30, Mobile OLED, statuses=["DELAYED"], group_by_customer=true.
3. 서버가 두 조회를 독립 실행하고 호출 ID별 결과를 저장한다.
4. 월·고객 기준으로 비교한다. 지연 수주만 조회했으므로 전체 수주 대비 지연 비율이 필요하면 전체 수주를 추가 조회한다.
5. output_mode="briefing"에 따라 sales, orders, recommended_actions 섹션을 실제 결과로 조립한다.
6. GPT가 판매 감소와 지연 수주의 연관 가능성을 설명하고, 서버가 근거 데이터로 표·차트를 생성한다.

뉴스·재고가 필요하지 않은 요청에는 브리핑이라는 이유만으로 항상 네 조회를 실행하지 않는다.

## 14. 단계별 전환 순서와 확인 기준

1. 현재 전환 중인 문법·Request 필드 불일치를 해소하고 모델 설정·의존성을 확인한다.
2. 업무 입력·결과 계약을 먼저 확정한 뒤 Request, SQL, Response를 함께 변경한다.
3. 데이터 Wrapper 5개를 구조화 입력·업무 결과 반환으로 통일하고 브리핑은 내부 조립으로 옮긴다.
4. 실행 계획 검증·결과 저장·부분 실패·브리핑 의존성을 구현한다.
5. GPT 설명과 화면 표·차트 생성 단계를 연결하고 최종 응답 모델로 검증한다.
6. 기존 단일 질문과 방향 문서의 30개 복합 질문을 회귀 확인한다. 문장 일치보다 계획·인자·실제 호출·핵심 수치·스키마를 검증한다.

| 확인 항목 | 기대 결과 |
| --- | --- |
| 잘못된 월·역전 기간·잘못된 상태·빈 제품 목록 | 조회 전에 검증 실패 |
| CUST_A 판매 | 판매 Tool에 해당 고객 필터 전달 |
| 고객별 매출 | 프로필 대신 판매 고객별 집계 |
| 판매와 수주 비교 | 두 결과 확보 후 같은 차원으로 비교 |
| 판매와 재고 비교 | 같은 월별 기간 조회, 고객 차원 한계 표시 |
| 제품군 두 개 비교 | 집계 차원 보존, 합계와 ASP 정확성 |
| 과거 뉴스 조회 | DB 기간과 NAVER 최신 범위 혼동 방지 |
| 선행 조회 일부 실패 | 실패 범위를 밝힌 부분 브리핑 |
| Tool이 빈 결과 반환 | 데이터 없음과 실행 실패 구분 |
| GPT의 일반 텍스트·잘못된 JSON 응답 | 파싱·스키마 오류 처리 |
| 최종 화면 응답 | 기존 answer, tables, charts 등의 계약 유지 |

이 문서 작성에서는 API·DB 호출 및 Python 구현 테스트를 실행하지 않았다. 위 표는 구현 단계에서 충족해야 할 검증 기준이다.

## 15. TO-BE 소스 전체

아래는 **Tool 계층 전체 예제**다. 데이터 Tool 5개의 함수 본문, 입력 스키마, 결과·오류 처리, 등록 목록, 호출 ID 연결, 서버 내부 브리핑 조립을 생략 없이 수록한다. 앞 절의 `...` 시그니처 설명은 이 절의 전체 코드를 참고한다.

기존 `agent.py` 전체를 교체하는 파일은 아니다. GPT 호출, QueryPlan 생성, 병렬 실행·타임아웃, 최종 화면 응답 조립은 상위 오케스트레이터의 책임이다. 하위 SQL 전체도 이 예제의 범위에 포함하지 않는다. **특히 판매·수주·재고 하위 함수를 수정하기 전에는 아래 Wrapper만 복사해 정상 동작할 수 없다.**

### 15.1 요청 스키마 전체

적용 위치: `agent-python/app/schemas/tool_schema.py`의 해당 Request 정의를 교체하고 공통 타입과 BriefingOptions를 추가한다. 기존 Response·Point 클래스는 삭제하지 않고 아래 15.4의 변경 계약에 맞춰 확장한다.

선택 필터도 필드 자체는 필수이며 미사용 값은 `null`로 받는다. Tool 호출 전에 월·날짜 정책을 확정해 모든 인자를 전달한다. `args_schema` 지정은 OpenAI strict 옵션을 자동 설정한다는 의미가 아니므로 모델 연결 시 실제 스키마와 옵션을 별도 확인한다.

```python
from datetime import date
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Month = Annotated[
    str, Field(pattern=r"^[0-9]{4}-(0[1-9]|1[0-2])$")
]
Name = Annotated[str, Field(min_length=1, max_length=50)]
CustomerId = Annotated[str, Field(min_length=1, max_length=30)]
ProductGroups = Annotated[list[Name], Field(min_length=1)]
CustomerIds = Annotated[list[CustomerId], Field(min_length=1)]
GroupBy = Literal["month", "customer", "product_group"]
Metric = Literal["qty", "revenue", "asp"]
OrderState = Literal[
    "REQUESTED", "CONFIRMED", "DELAYED", "SHIPPED", "CANCELLED"
]
ImpactLevel = Literal["HIGH", "MEDIUM", "LOW"]
Section = Literal[
    "sales", "orders", "inventory", "competitor_news",
    "recommended_actions",
]


class StrictRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    @model_validator(mode="after")
    def reject_duplicate_lists(self):
        for field_name in type(self).model_fields:
            value = getattr(self, field_name)
            if isinstance(value, list) and len(value) != len(set(value)):
                raise ValueError(f"{field_name}: 중복 항목은 허용하지 않습니다.")
        return self


class MonthRangeRequest(StrictRequest):
    start_month: Month = Field(description="조회 시작 월, YYYY-MM")
    end_month: Month = Field(description="조회 종료 월, YYYY-MM, 포함")

    @model_validator(mode="after")
    def validate_month_range(self):
        # 정규식만으로 허용될 수 있는 0000년까지 검사한다.
        date.fromisoformat(f"{self.start_month}-01")
        date.fromisoformat(f"{self.end_month}-01")
        if self.start_month > self.end_month:
            raise ValueError("start_month는 end_month보다 늦을 수 없습니다.")
        return self


class DateRangeRequest(StrictRequest):
    start_date: date = Field(description="조회 시작일, YYYY-MM-DD")
    end_date: date = Field(description="조회 종료일, YYYY-MM-DD, 포함")

    @model_validator(mode="after")
    def validate_date_range(self):
        if self.start_date > self.end_date:
            raise ValueError("start_date는 end_date보다 늦을 수 없습니다.")
        return self


class SalesTrendRequest(MonthRangeRequest):
    product_groups: ProductGroups = Field(description="조회할 제품군 목록")
    customer_ids: CustomerIds | None = Field(description="고객 필터, 없으면 null")
    group_by: Annotated[list[GroupBy], Field(min_length=1)] = Field(
        description="집계 차원: month, customer, product_group"
    )
    metrics: Annotated[list[Metric], Field(min_length=1)] = Field(
        description="반환 지표: qty, revenue, asp"
    )


class OrderStatusRequest(DateRangeRequest):
    product_groups: ProductGroups
    customer_ids: CustomerIds | None
    statuses: Annotated[list[OrderState], Field(min_length=1)] | None
    group_by_customer: bool = Field(description="고객별로 구분하여 집계")
    group_by_product_group: bool = Field(description="제품군별로 구분하여 집계")


class InventoryRiskRequest(MonthRangeRequest):
    product_groups: ProductGroups


class CustomerProfileRequest(MonthRangeRequest):
    customer_id: CustomerId


class CompetitorNewsRequest(DateRangeRequest):
    companies: Annotated[list[Name], Field(min_length=1)] | None
    category: Name | None
    impact_level: ImpactLevel | None
    keyword: Annotated[str, Field(min_length=1, max_length=100)] | None
    product_group: Name | None


class BriefingOptions(DateRangeRequest):
    """모델의 데이터 Tool 인자가 아니라 서버 내부 조립 옵션."""
    topic: Annotated[str, Field(min_length=1, max_length=200)]
    customer_id: CustomerId | None
    sections: Annotated[list[Section], Field(min_length=1)]


class BriefingRequest(BriefingOptions):
    # 서버가 실제 실행 결과로 채운다. LLM에 입력 스키마로 노출하지 않는다.
    tool_results: dict[str, Any] = Field(default_factory=dict)
```

### 15.2 agent.py의 Tool·공통 함수 전체

아래 import, 공통 함수, Wrapper, 등록 목록을 하나의 블록으로 적용한다. 같은 이름의 기존 정의를 중복으로 남기지 않는다.

- `get_sales_trend/get_order_status/get_inventory_risk`는 15.1 요청 계약을 지원하도록 변경된 함수여야 한다.
- 제품·고객 ID의 실제 존재 및 접근 가능 범위는 서버/조회 계층에서 검증한다.
- `call_id`는 GPT 업무 인자에 포함하지 않고 실행기가 부여한다.
- 브리핑에는 `@tool`을 붙이지 않는다. `results_by_call_id`를 키워드 전용 인자로 명시해 숨겨진 전역 저장소 없이 서버가 실제 결과를 주입한다.
- 브리핑용 저장소는 현재 요청에서 기간·고객·제품 범위를 검증한 결과만 담아야 한다. 이 함수가 기간 차이나 중복 조회를 자동 조정하지는 않는다.

```python
import logging
from collections.abc import Callable, Mapping
from datetime import date
from typing import Any

from langchain_core.tools import tool
from pydantic import BaseModel, ValidationError

from app.schemas.tool_schema import (
    BriefingOptions,
    BriefingRequest,
    CompetitorNewsRequest,
    CustomerProfileRequest,
    InventoryRiskRequest,
    OrderStatusRequest,
    SalesTrendRequest,
)
from app.tools.briefing_tool import create_briefing_report
from app.tools.customer_tool import get_customer_profile
from app.tools.inventory_tool import get_inventory_risk
from app.tools.news_tool import search_competitor_news
from app.tools.order_tool import get_order_status
from app.tools.sales_tool import get_sales_trend

logger = logging.getLogger(__name__)


def error_result(
    tool_name: str,
    error_code: str,
    message: str,
    retryable: bool = False,
) -> dict[str, Any]:
    return {
        "tool_name": tool_name,
        "status": "error",
        "error_code": error_code,
        "message": message,
        "retryable": retryable,
    }


def normalize_result(
    tool_name: str,
    request: BaseModel,
    raw: BaseModel | dict[str, Any],
) -> dict[str, Any]:
    payload = raw.model_dump(mode="json") if isinstance(raw, BaseModel) else raw
    if not isinstance(payload, dict):
        raise ValueError("조회 결과는 모델 또는 dict여야 합니다.")
    if payload.get("status") == "error":
        # 기존 ErrorResponse만으로 일시적 장애인지 알 수 없으므로
        # 하위 계층이 명시적으로 제공한 경우에만 재시도한다.
        return error_result(
            tool_name,
            payload.get("error_code", "TOOL_QUERY_FAILED"),
            payload.get("message", "데이터 조회에 실패했습니다."),
            payload.get("retryable") is True,
        )
    if payload.get("status") != "success":
        raise ValueError("조회 결과의 status가 잘못되었습니다.")

    rows = payload.get("data")
    if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
        raise ValueError("data는 객체 목록이어야 합니다.")

    signals = []
    for value in payload.get("risk_signals", []):
        if isinstance(value, str):
            signals.append({"message": value})
        elif isinstance(value, dict) and isinstance(value.get("message"), str):
            signals.append(value)
        else:
            raise ValueError("risk_signals 형식이 잘못되었습니다.")

    return {
        "tool_name": tool_name,
        "status": "success",
        "filters": request.model_dump(mode="json", exclude={"tool_results"}),
        "data": rows,
        "aggregates": payload.get("aggregates", {}),
        "summary": payload.get("summary", ""),
        "insights": payload.get("insights", []),
        "risk_signals": signals,
        "chart_data": payload.get("chart_data", {}),
        "actions": payload.get("actions", []),
        "warnings": payload.get("warnings", []),
        "source_ranges": payload.get("source_ranges", {}),
    }


def query_tool(
    tool_name: str,
    request_type: type[BaseModel],
    query: Callable[[Any], Any],
    arguments: dict[str, Any],
) -> dict[str, Any]:
    try:
        request = request_type.model_validate(arguments)
    except ValidationError:
        return error_result(tool_name, "INVALID_ARGUMENTS", "조회 조건이 올바르지 않습니다.")

    try:
        raw = query(request)
    except Exception:
        logger.exception("%s query failed", tool_name)
        return error_result(tool_name, "TOOL_EXECUTION_FAILED", "Tool 실행에 실패했습니다.")

    try:
        return normalize_result(tool_name, request, raw)
    except (ValueError, TypeError, KeyError):
        logger.exception("%s returned an invalid result", tool_name)
        return error_result(tool_name, "INVALID_TOOL_RESULT", "조회 결과 형식이 올바르지 않습니다.")


@tool(args_schema=SalesTrendRequest)
def sales_trend_tool(
    start_month: str,
    end_month: str,
    product_groups: list[str],
    customer_ids: list[str] | None,
    group_by: list[str],
    metrics: list[str],
) -> dict[str, Any]:
    """판매량·매출·ASP를 조회한다. 고객별 판매는 customer 집계를 사용한다.
    고객 등급·지역 등 프로필 조회는 customer_profile_tool을 사용한다.
    판매와 수주·재고 비교에는 해당 데이터 Tool도 함께 선택한다.
    """
    return query_tool(
        "sales_trend_tool", SalesTrendRequest, get_sales_trend,
        {
            "start_month": start_month,
            "end_month": end_month,
            "product_groups": product_groups,
            "customer_ids": customer_ids,
            "group_by": group_by,
            "metrics": metrics,
        },
    )


@tool(args_schema=OrderStatusRequest)
def order_status_tool(
    start_date: date,
    end_date: date,
    product_groups: list[str],
    customer_ids: list[str] | None,
    statuses: list[str] | None,
    group_by_customer: bool,
    group_by_product_group: bool,
) -> dict[str, Any]:
    """수주량·상태별 건수·지연 수주를 조회한다.
    고객별 또는 제품별 비교에는 해당 집계 인자를 true로 지정한다.
    statuses=null은 전체 상태이며 판매 매출은 sales_trend_tool로 조회한다.
    """
    return query_tool(
        "order_status_tool", OrderStatusRequest, get_order_status,
        {
            "start_date": start_date,
            "end_date": end_date,
            "product_groups": product_groups,
            "customer_ids": customer_ids,
            "statuses": statuses,
            "group_by_customer": group_by_customer,
            "group_by_product_group": group_by_product_group,
        },
    )


@tool(args_schema=InventoryRiskRequest)
def inventory_risk_tool(
    start_month: str,
    end_month: str,
    product_groups: list[str],
) -> dict[str, Any]:
    """지정 기간의 제품별 재고·안전재고·과잉·부족을 조회한다.
    고객 전용 재고를 제공하지 않는다. 판매·수주와 같은 기간으로 비교한다.
    """
    return query_tool(
        "inventory_risk_tool", InventoryRiskRequest, get_inventory_risk,
        {
            "start_month": start_month,
            "end_month": end_month,
            "product_groups": product_groups,
        },
    )


@tool(args_schema=CustomerProfileRequest)
def customer_profile_tool(
    customer_id: str,
    start_month: str,
    end_month: str,
) -> dict[str, Any]:
    """확인된 고객 ID의 프로필과 기간별 판매·수주 요약을 조회한다.
    단순 고객별 매출 질문에는 사용하지 않는다.
    복수 고객은 고객별로 호출하며 ID를 임의로 생성하지 않는다.
    """
    return query_tool(
        "customer_profile_tool", CustomerProfileRequest, get_customer_profile,
        {
            "customer_id": customer_id,
            "start_month": start_month,
            "end_month": end_month,
        },
    )


@tool(args_schema=CompetitorNewsRequest)
def competitor_news_tool(
    start_date: date,
    end_date: date,
    companies: list[str] | None,
    category: str | None,
    impact_level: str | None,
    keyword: str | None,
    product_group: str | None,
) -> dict[str, Any]:
    """경쟁사·가격·수요·공급·생산능력 뉴스를 검색한다.
    keyword로 주제를 지정한다. OLED를 Mobile OLED로 축소하지 않는다.
    DB 요청 기간과 NAVER 최신 검색 범위 차이는 결과의 warnings를 확인한다.
    """
    return query_tool(
        "competitor_news_tool", CompetitorNewsRequest, search_competitor_news,
        {
            "start_date": start_date,
            "end_date": end_date,
            "companies": companies,
            "category": category,
            "impact_level": impact_level,
            "keyword": keyword,
            "product_group": product_group,
        },
    )


# 브리핑은 데이터 Tool 등록 목록에서 제외한다.
DATA_TOOLS = [
    sales_trend_tool,
    order_status_tool,
    inventory_risk_tool,
    customer_profile_tool,
    competitor_news_tool,
]
TOOL_BY_NAME = {item.name: item for item in DATA_TOOLS}
SECTION_BY_TOOL = {
    "sales_trend_tool": "sales",
    "order_status_tool": "orders",
    "inventory_risk_tool": "inventory",
    "competitor_news_tool": "competitor_news",
}


def execute_tool_call(
    call_id: str,
    tool_name: str,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    """서버가 검증한 호출을 실행하고 실제 호출 ID를 결과에 연결한다."""
    if tool_name not in TOOL_BY_NAME:
        result = error_result(tool_name, "UNKNOWN_TOOL", "허용되지 않은 Tool입니다.")
    else:
        try:
            # args_schema 검증은 Tool 본문 실행 전에 일어나므로 여기서 처리한다.
            result = TOOL_BY_NAME[tool_name].invoke(arguments)
        except ValidationError:
            result = error_result(tool_name, "INVALID_ARGUMENTS", "Tool 인자가 올바르지 않습니다.")
        except Exception:
            logger.exception("Tool call failed: %s", call_id)
            result = error_result(tool_name, "TOOL_EXECUTION_FAILED", "Tool 실행에 실패했습니다.")
    return {**result, "call_id": call_id}


def briefing_report_tool(
    topic: str,
    customer_id: str | None,
    start_date: date,
    end_date: date,
    sections: list[str],
    *,
    results_by_call_id: Mapping[str, dict[str, Any]],
) -> dict[str, Any]:
    """서버 내부 전용. 현재 요청의 실제 결과를 받아 브리핑 섹션을 조립한다."""
    try:
        options = BriefingOptions(
            topic=topic,
            customer_id=customer_id,
            start_date=start_date,
            end_date=end_date,
            sections=sections,
        )
    except ValidationError:
        return error_result("briefing_report_tool", "INVALID_ARGUMENTS", "브리핑 조건이 올바르지 않습니다.")

    merged: dict[str, dict[str, Any]] = {}
    warnings: list[str] = []
    successful_names: list[str] = []

    for call_id, result in results_by_call_id.items():
        if result.get("call_id") != call_id:
            return error_result(
                "briefing_report_tool", "INVALID_TOOL_RESULT",
                "저장소 키와 결과의 호출 ID가 일치하지 않습니다.",
            )
        name = result.get("tool_name", "")
        section = SECTION_BY_TOOL.get(name)
        if section not in options.sections:
            continue
        if result.get("status") != "success":
            warnings.append(f"{name}({call_id}) 조회 실패로 해당 결과를 제외했습니다.")
            continue

        successful_names.append(name)
        warnings.extend(result.get("warnings", []))
        bucket = merged.setdefault(
            section,
            {
                "summary": [],
                "insights": [],
                "risk_signals": [],
                "actions": [],
                "results": [],
            },
        )
        # 다른 필터의 수치를 임의로 합산하지 않고 원본별 조건을 보존한다.
        bucket["summary"].append(
            f"[{call_id}; filters={result.get('filters', {})}] "
            f"{result.get('summary', '')}"
        )
        for field in ("insights", "risk_signals", "actions"):
            bucket[field].extend(result.get(field, []))
        bucket["results"].append(result)

    for section in options.sections:
        if section == "recommended_actions":
            continue
        if section not in merged:
            warnings.append(f"{section}: 성공한 선행 조회 결과가 없습니다.")
            merged[section] = {
                "summary": "선행 조회가 누락되었거나 실패하여 분석할 수 없습니다.",
                "insights": [],
                "risk_signals": [],
                "actions": [],
                "results": [],
            }

    if not successful_names:
        return {
            **error_result(
                "briefing_report_tool", "NO_SOURCE_RESULTS",
                "브리핑에 사용할 성공한 선행 조회 결과가 없습니다.",
            ),
            "warnings": warnings,
            "tools_used": [],
        }

    request_arguments = {
        **options.model_dump(mode="json"),
        "tool_results": merged,
    }
    result = query_tool(
        "briefing_report_tool", BriefingRequest,
        create_briefing_report, request_arguments,
    )
    result["warnings"] = list(dict.fromkeys([*warnings, *result.get("warnings", [])]))
    result["tools_used"] = list(dict.fromkeys(successful_names))
    return result
```

### 15.3 서버 내부 호출 연결 예제

다음은 모델 호출을 생략한 결정적 호출 예제다. 운영에서는 QueryPlan 검증 후 선택된 호출을 실행하고, 요청 내부에서 유일한 호출 ID로 저장한다. 복수 고객은 동일 Tool을 서로 다른 ID·인자로 여러 번 호출한다.

```python
# 15.2와 같은 모듈의 함수·import를 사용하는 예제
results_by_call_id = {}

sales_result = execute_tool_call(
    call_id="call_sales_1",
    tool_name="sales_trend_tool",
    arguments={
        "start_month": "2026-04",
        "end_month": "2026-06",
        "product_groups": ["Mobile OLED"],
        "customer_ids": ["CUST_A"],
        "group_by": ["month", "customer"],
        "metrics": ["qty", "revenue", "asp"],
    },
)
results_by_call_id[sales_result["call_id"]] = sales_result

# QueryPlan.output_mode == "briefing"일 때 서버에서 실행
briefing_result = briefing_report_tool(
    topic="2026년 2분기 CUST_A 판매 브리핑",
    customer_id="CUST_A",
    start_date=date(2026, 4, 1),
    end_date=date(2026, 6, 30),
    sections=["sales", "recommended_actions"],
    results_by_call_id=results_by_call_id,
)
# briefing_result는 업무 결과다. 최종 /agent/chat 응답으로 바로 반환하지 않는다.
```

### 15.4 이 소스와 함께 적용할 하위 계층 계약

| 함수/모델 | 반드시 함께 구현할 내용 |
| --- | --- |
| get_sales_trend / SalesTrendPoint | product_groups·customer_ids 필터, group_by별 차원, metrics 선택, 가중 ASP. month 미집계 시 해당 필드 선택 처리, product_group 차원 추가 |
| get_order_status / OrderStatusPoint | 복수 제품·고객·상태 조건, 고객/제품별 GROUP BY, 결과 customer_id/customer_name/product_group 추가 |
| get_inventory_risk / InventoryTrendPoint | start_month~end_month 기간 조회, 제품별 행, shortage_qty/excess_qty 및 제품별 위험 신호 |
| get_customer_profile | 기존 단일 고객 조회 재사용. 새 Request의 필수 인자 규칙에 맞춰 직접 API 호출자 조정 |
| search_competitor_news | 요청 기간 밖 기사 처리 후 data·summary·chart_data·insights를 같은 범위로 계산. source_ranges와 부분 실패 warnings 반환 |
| create_briefing_report | 기존 dict/list summary 취합 활용. Wrapper는 복수 호출을 섹션별 dict로 묶어 전달하며 GPT의 교차분석 자체는 상위에서 수행 |
| 성공 응답 모델 | 추가 계산은 aggregates, 경고는 warnings, 출처별 조회 범위는 source_ranges 필드로 보존. 모델에 없는 필드는 model_dump 이전에 유실될 수 있으므로 응답 모델 확장 필요 |
| 오류 응답 모델 | error_code와 retryable 추가. 기존 일반 ErrorResponse만 받은 경우 예제는 자동 재시도를 하지 않음 |

Wrapper는 하위 조회가 반환한 계산·경고를 전달한다. SQL을 대신 구현하거나 뉴스 기간을 사후에 잘라 기존 요약과 불일치시키지 않는다. SQL 조건과 GROUP BY는 허용된 필드만 조합하고 값은 파라미터로 전달한다.

이 예제의 `execute_tool_call()`은 호출 1건의 실행·오류·ID 연결을 담당한다. 병렬 스케줄러, 실제 API ToolMessage 연결, 타임아웃·재시도 정책, 최종 출력 스키마 검증은 이 함수 바깥에 구현한다.
