# Display Market Intelligence Agent 소스 흐름 안내서

## 1. 이 문서의 목적

이 문서는 현재까지 구현된 Python Agent 소스가 어떤 순서로 실행되는지 쉽게 설명한다.

처음 코드를 보는 개발자는 아래 순서로 읽으면 된다.

| 순서 | 파일 | 먼저 볼 내용 |
| --- | --- | --- |
| 1 | `agent-python/app/main.py` | FastAPI API가 어디서 시작되는지 |
| 2 | `agent-python/app/graph/agent.py` | Agent가 질문을 받고 어떤 Tool을 고르는지 |
| 3 | `agent-python/app/tools/*.py` | 실제 DB 조회와 분석을 어떻게 하는지 |
| 4 | `agent-python/app/schemas/*.py` | Request/Response 데이터 구조가 어떻게 생겼는지 |
| 5 | `agent-python/app/db.py` | PostgreSQL 연결을 어떻게 가져오는지 |

## 2. 전체 구조 한눈에 보기

```text
사용자
  |
  v
Vue 또는 curl
  |
  v
Spring Boot 또는 FastAPI 직접 호출
  |
  v
agent-python/app/main.py
  |
  +-- /agent/chat
  |     |
  |     v
  |   agent-python/app/graph/agent.py
  |     |
  |     +-- sales_trend_tool
  |     +-- order_status_tool
  |     +-- inventory_risk_tool
  |
  +-- /tools/sales-trend
  +-- /tools/order-status
  +-- /tools/inventory-risk
        |
        v
      agent-python/app/tools/*.py
        |
        v
      PostgreSQL
```

현재는 두 가지 방식으로 Tool을 실행할 수 있다.

| 방식 | API | 설명 |
| --- | --- | --- |
| Agent 방식 | `POST /agent/chat` | 자연어 질문을 Agent가 받아 적절한 Tool을 선택한다. |
| Tool 직접 실행 | `POST /tools/...` | 특정 Tool을 직접 호출한다. 개발 및 테스트에 좋다. |

## 3. main.py 흐름

`main.py`는 FastAPI 애플리케이션의 시작점이다.

주요 역할은 다음과 같다.

| 역할 | 코드 위치 | 설명 |
| --- | --- | --- |
| FastAPI 앱 생성 | `app = FastAPI(...)` | 서버 이름, 버전, 종료 처리 설정 |
| DB 종료 처리 | `lifespan()` | 서버 종료 시 DB 커넥션 풀을 닫는다. |
| 공통 오류 처리 | `validation_exception_handler()`, `unexpected_exception_handler()` | 요청 오류와 서버 오류를 공통 JSON으로 반환한다. |
| 헬스체크 | `GET /health` | 서버와 DB 연결 상태를 확인한다. |
| Agent 실행 | `POST /agent/chat` | 자연어 질문을 `run_agent()`로 넘긴다. |
| Tool 직접 실행 | `POST /tools/...` | 판매, 수주, 재고 Tool을 직접 호출한다. |

### 3.1 `/agent/chat` 실행 흐름

```text
POST /agent/chat
  |
  v
AgentChatRequest(question)
  |
  v
run_agent(request.question)
  |
  v
agent.py의 Agent 실행
```

예시 요청:

```json
{
  "question": "최근 6개월 OLED 판매 동향 분석해줘"
}
```

### 3.2 `/tools/...` 실행 흐름

Tool 직접 실행 API는 Agent를 거치지 않는다.

```text
POST /tools/sales-trend
  |
  v
SalesTrendRequest 검증
  |
  v
get_sales_trend(request)
  |
  v
SalesTrendResponse 반환
```

이 방식은 Tool 자체가 잘 동작하는지 확인할 때 사용한다.

## 4. agent.py 흐름

`agent.py`는 자연어 질문을 받아 어떤 Tool을 실행할지 결정한다.

현재는 공식 LangChain `create_agent`를 사용한다.

```python
from langchain.agents import create_agent
```

다만 실제 LLM API는 아직 연결하지 않았다. 대신 `RuleBasedChatModel`이 키워드 규칙으로 Tool을 선택한다.

### 4.1 왜 RuleBasedChatModel을 쓰는가

| 이유 | 설명 |
| --- | --- |
| 테스트가 쉽다 | OpenAI API Key 없이도 테스트할 수 있다. |
| 흐름이 명확하다 | 어떤 질문이 어떤 Tool로 가는지 코드에서 바로 보인다. |
| 나중에 교체 가능하다 | 실제 LLM을 붙일 때 `build_agent()`의 model만 바꾸면 된다. |

나중에 실제 LLM을 붙이면 아래 부분만 교체하면 된다.

```python
def build_agent():
    return create_agent(
        model=RuleBasedChatModel(),
        tools=[sales_trend_tool, order_status_tool, inventory_risk_tool],
        system_prompt="..."
    )
```

## 5. Agent 실행 상세 흐름

`/agent/chat`으로 질문이 들어오면 다음 순서로 실행된다.

```text
run_agent(question)
  |
  v
agent.invoke({"messages": [HumanMessage(content=question)]})
  |
  v
RuleBasedChatModel._generate()
  |
  v
choose_tool_name(question)
  |
  +-- sales_trend_tool
  +-- order_status_tool
  +-- inventory_risk_tool
  |
  v
Tool 실행 결과를 JSON 응답으로 반환
```

### 5.1 Tool 선택 기준

`choose_tool_name()` 함수가 질문 키워드를 보고 Tool 이름을 선택한다.

| 질문 키워드 | 선택 Tool |
| --- | --- |
| `판매`, `매출`, `동향`, `추이`, `sales`, `revenue`, `trend`, `oled` | `sales_trend_tool` |
| `수주`, `주문`, `납기`, `지연`, `order`, `delivery`, `delayed` | `order_status_tool` |
| `재고`, `안전재고`, `과잉`, `부족`, `inventory`, `stock`, `risk` | `inventory_risk_tool` |

질문에 여러 키워드가 섞일 수 있으므로 현재는 아래 순서로 먼저 검사한다.

```text
재고 질문
-> 수주 질문
-> 판매 질문
-> 미지원 질문
```

## 6. Tool Wrapper 흐름

`agent.py`에는 `@tool`이 붙은 함수 3개가 있다.

| 함수 | 실제 호출 Tool | 역할 |
| --- | --- | --- |
| `sales_trend_tool()` | `get_sales_trend()` | 판매 질문을 Tool Request로 바꾸고 판매 Tool을 실행 |
| `order_status_tool()` | `get_order_status()` | 수주 질문을 Tool Request로 바꾸고 수주 Tool을 실행 |
| `inventory_risk_tool()` | `get_inventory_risk()` | 재고 질문을 Tool Request로 바꾸고 재고 Tool을 실행 |

예를 들어 판매 질문은 아래처럼 처리된다.

```text
sales_trend_tool(question)
  |
  v
SalesTrendRequest 생성
  |
  v
get_sales_trend(request)
  |
  v
build_sales_answer(...)
  |
  v
화면 공통 응답 JSON 반환
```

## 7. Request 모델의 역할

`agent-python/app/schemas/tool_schema.py`에는 Tool별 Request/Response 모델이 있다.

예를 들어 `SalesTrendRequest`는 다음 값을 가진다.

```text
start_month
end_month
product_group
customer_id
```

이 모델을 쓰는 이유는 다음과 같다.

| 이유 | 설명 |
| --- | --- |
| 입력 검증 | 날짜 형식, 필수값, 상태값 등을 자동으로 검증한다. |
| Swagger 문서화 | FastAPI `/docs`에서 요청 구조가 자동으로 보인다. |
| 개발 실수 방지 | Tool에 잘못된 형태의 데이터가 들어가는 것을 줄인다. |

## 8. Tool 파일의 역할

`agent-python/app/tools` 아래 파일들은 실제 업무 데이터를 조회하고 분석한다.

| 파일 | 함수 | 역할 |
| --- | --- | --- |
| `sales_tool.py` | `get_sales_trend()` | 월별 판매량, 매출, ASP를 조회하고 판매 추세를 분석한다. |
| `order_tool.py` | `get_order_status()` | 월별 수주 건수, 수주량, 지연/취소 리스크를 분석한다. |
| `inventory_tool.py` | `get_inventory_risk()` | 재고, 안전재고, 생산량, 판매량 기준으로 재고 리스크를 분석한다. |

Tool 함수는 공통적으로 아래 흐름을 가진다.

```text
Request 모델 입력
  |
  v
SQL 파라미터 준비
  |
  v
get_connection()으로 DB 연결
  |
  v
PostgreSQL 조회
  |
  v
조회 결과를 Response 모델로 변환
  |
  v
insights, risk_signals, actions 작성
```

## 9. DB 연결 흐름

`agent-python/app/db.py`는 PostgreSQL 연결을 관리한다.

```text
Tool
  |
  v
get_connection()
  |
  v
Database.connection()
  |
  v
ThreadedConnectionPool에서 커넥션 대여
  |
  v
SQL 실행
  |
  v
커넥션 반납
```

중요한 점은 Tool에서 DB를 조회 전용으로 사용한다는 것이다.

```python
conn.set_session(readonly=True, autocommit=False)
```

따라서 실수로 INSERT, UPDATE, DELETE 같은 변경 쿼리를 실행하는 위험을 줄인다.

## 10. 응답 JSON 흐름

최종 응답은 Spring Boot와 Vue가 사용하기 쉬운 구조로 맞춘다.

```json
{
  "status": "success",
  "message": "요청이 정상 처리되었습니다.",
  "data": {
    "answer": "자연어 답변",
    "summary": [],
    "tables": [],
    "charts": [],
    "insights": [],
    "risk_signals": [],
    "actions": []
  },
  "error": null
}
```

`agent.py`에서는 아래 함수가 이 공통 응답 구조를 만든다.

| 함수 | 역할 |
| --- | --- |
| `success_answer()` | 성공 응답의 공통 뼈대를 만든다. |
| `table()` | Tool data를 화면 표 구조로 바꾼다. |
| `charts_from_tool_result()` | Tool chart_data를 화면 차트 구조로 바꾼다. |
| `unsupported_answer()` | 지원하지 않는 질문 안내 응답을 만든다. |

## 11. 테스트 흐름

현재 테스트는 크게 두 종류다.

| 테스트 파일 | 테스트 대상 |
| --- | --- |
| `tests/test_sales_tool.py` | 판매 Tool 함수 단위 테스트 |
| `tests/test_order_tool.py` | 수주 Tool 함수 단위 테스트 |
| `tests/test_inventory_tool.py` | 재고 Tool 함수 단위 테스트 |
| `tests/test_main_tool_routes.py` | `/tools/...` 직접 API 라우트 테스트 |
| `tests/test_workflow_tools.py` | `/agent/chat` Agent 라우팅 테스트 |

전체 테스트 실행:

```powershell
cd D:\eclipse\workspace\deepsightAgent\agent-python
.venv\Scripts\python.exe -m unittest discover -s tests
```

테스트는 DB를 직접 연결하지 않고 mock 객체를 사용한다. 그래서 `.env`나 실제 PostgreSQL 연결 없이도 빠르게 확인할 수 있다.

## 12. 직접 실행 테스트

서버 실행:

```powershell
cd D:\eclipse\workspace\deepsightAgent\agent-python
.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

Swagger 확인:

```text
http://localhost:8000/docs
```

Agent 질문 테스트:

```powershell
Invoke-RestMethod `
  -Uri "http://localhost:8000/agent/chat" `
  -Method Post `
  -ContentType "application/json" `
  -Body '{"question":"최근 6개월 OLED 판매 동향 분석해줘"}'
```

수주 질문:

```powershell
Invoke-RestMethod `
  -Uri "http://localhost:8000/agent/chat" `
  -Method Post `
  -ContentType "application/json" `
  -Body '{"question":"OLED 수주 현황과 납기 지연 확인해줘"}'
```

재고 질문:

```powershell
Invoke-RestMethod `
  -Uri "http://localhost:8000/agent/chat" `
  -Method Post `
  -ContentType "application/json" `
  -Body '{"question":"TV OLED 재고 리스크 확인해줘"}'
```

## 13. 새 Tool을 추가할 때 수정할 곳

새 Tool을 추가할 때는 아래 순서로 작업하면 된다.

| 순서 | 수정 파일 | 할 일 |
| --- | --- | --- |
| 1 | `app/tools/new_tool.py` | 실제 Tool 함수 구현 |
| 2 | `app/schemas/tool_schema.py` | Request, Response 모델 추가 |
| 3 | `app/graph/agent.py` | `@tool` wrapper 함수 추가 |
| 4 | `app/graph/agent.py` | `build_agent()`의 `tools` 목록에 추가 |
| 5 | `app/graph/agent.py` | `choose_tool_name()`에 키워드 추가 |
| 6 | `app/main.py` | 직접 테스트 API가 필요하면 `/tools/...` 엔드포인트 추가 |
| 7 | `tests/` | Tool 단위 테스트와 Agent 라우팅 테스트 추가 |

## 14. 가장 많이 수정하게 될 위치

| 하고 싶은 일 | 수정할 위치 |
| --- | --- |
| 질문 키워드 추가 | `agent.py`의 `choose_tool_name()` |
| 제품군 인식 규칙 추가 | `agent.py`의 `extract_product_group()` |
| 수주 상태 인식 규칙 추가 | `agent.py`의 `extract_order_status()` |
| 화면 응답 문장 수정 | `agent.py`의 `build_sales_answer()`, `build_order_answer()`, `build_inventory_answer()` |
| 표 컬럼 수정 | 각 `build_*_answer()` 함수의 `table_columns` |
| 차트 구조 수정 | `agent.py`의 `charts_from_tool_result()` |
| DB 연결 설정 수정 | `db.py` |
| 요청 필드 추가 | `schemas/tool_schema.py` |

## 15. 현재 구현에서 기억할 점

| 항목 | 설명 |
| --- | --- |
| 공식 Agent API | `langchain.agents.create_agent`를 사용한다. |
| 실제 LLM | 아직 연결하지 않았다. `RuleBasedChatModel`이 임시로 Tool을 선택한다. |
| ReAct helper | `create_react_agent`는 사용하지 않는다. |
| Tool 직접 API | 개발 편의를 위해 `/tools/...` 엔드포인트를 유지한다. |
| DB 테스트 | 단위 테스트는 mock DB를 사용한다. |
| 실제 API 실행 | 실제 서버에서 Tool을 호출하려면 `.env`의 `DATABASE_URL`이 필요하다. |
