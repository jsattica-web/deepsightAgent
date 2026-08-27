# Display Market Intelligence Agent 테스트 명령어 모음

## 1. 문서 목적

이 문서는 현재 구현된 Python Agent를 직접 테스트할 때 사용할 수 있는 명령어를 정리한다.

PowerShell 기준으로 작성했으며, 명령어는 `agent-python` 폴더에서 실행하는 것을 기본으로 한다.

## 2. 기본 위치

Python Agent 위치:

```powershell
D:\eclipse\workspace\deepsightAgent\agent-python
```

## 3. 전체 단위 테스트 실행

가장 먼저 확인할 명령어다.

이 테스트는 DB를 직접 연결하지 않고 mock 객체를 사용한다. 따라서 `.env`의 `DATABASE_URL`이 없어도 실행 가능하다.

```powershell
cd D:\eclipse\workspace\deepsightAgent\agent-python
.venv\Scripts\python.exe -m unittest discover -s tests
```

정상 결과 예시:

```text
Ran 31 tests
OK
```

## 4. Tool 단위 테스트만 실행

### 4.1 판매 Tool 테스트

```powershell
cd D:\eclipse\workspace\deepsightAgent\agent-python
.venv\Scripts\python.exe -m unittest tests.test_sales_tool
```

### 4.2 수주 Tool 테스트

```powershell
cd D:\eclipse\workspace\deepsightAgent\agent-python
.venv\Scripts\python.exe -m unittest tests.test_order_tool
```

### 4.3 재고 Tool 테스트

```powershell
cd D:\eclipse\workspace\deepsightAgent\agent-python
.venv\Scripts\python.exe -m unittest tests.test_inventory_tool
```

### 4.4 고객사 프로필 Tool 테스트

```powershell
cd D:\eclipse\workspace\deepsightAgent\agent-python
.venv\Scripts\python.exe -m unittest tests.test_customer_tool
```

### 4.5 경쟁사 뉴스 Tool 테스트

```powershell
cd D:\eclipse\workspace\deepsightAgent\agent-python
.venv\Scripts\python.exe -m unittest tests.test_news_tool
```

### 4.6 브리핑 Tool 테스트

```powershell
cd D:\eclipse\workspace\deepsightAgent\agent-python
.venv\Scripts\python.exe -m unittest tests.test_briefing_tool
```

## 5. FastAPI Tool 라우트 테스트

`main.py`에 등록된 `/tools/...` API가 각 Tool 함수를 호출하는지 확인한다.

```powershell
cd D:\eclipse\workspace\deepsightAgent\agent-python
.venv\Scripts\python.exe -m unittest tests.test_main_tool_routes
```

## 6. Agent 라우팅 테스트

`/agent/chat` 흐름에서 자연어 질문이 알맞은 Tool로 연결되는지 확인한다.

```powershell
cd D:\eclipse\workspace\deepsightAgent\agent-python
.venv\Scripts\python.exe -m unittest tests.test_workflow_tools
```

확인 대상:

| 질문 예시 | 기대 Tool |
| --- | --- |
| `최근 6개월 OLED 판매 동향 분석해줘` | `sales_trend_tool` |
| `OLED 수주 현황과 납기 지연 확인해줘` | `order_status_tool` |
| `TV OLED 재고 리스크 확인해줘` | `inventory_risk_tool` |
| `CUST_A 고객사 프로필 확인해줘` | `customer_profile_tool` |
| `LGD 경쟁사 뉴스 확인해줘` | `competitor_news_tool` |
| `CUST_A 대상 브리핑 보고서 만들어줘` | `briefing_report_tool` |

## 7. 문법 체크

코드 수정 후 Python 문법 오류가 없는지 빠르게 확인할 때 사용한다.

```powershell
cd D:\eclipse\workspace\deepsightAgent\agent-python
.venv\Scripts\python.exe -m py_compile `
  app\main.py `
  app\db.py `
  app\agent\agent.py `
  app\schemas\common.py `
  app\schemas\tool_schema.py
```

아무 출력 없이 종료되면 성공이다.

## 8. FastAPI 서버 실행

실제 API를 직접 호출하려면 서버를 먼저 실행한다.

```powershell
cd D:\eclipse\workspace\deepsightAgent\agent-python
.\run.bat
```

Swagger 문서:

```text
http://localhost:8000/docs
```

주의:

`/tools/...` API와 `/agent/chat` API를 실제로 실행하면 Tool 내부에서 PostgreSQL을 조회한다. 따라서 `.env`의 `DATABASE_URL`이 정상이어야 한다.

## 9. Health Check API 테스트

```powershell
Invoke-RestMethod `
  -Uri "http://localhost:8000/health" `
  -Method Get
```

## 10. Agent Chat API 테스트

Windows PowerShell에서 한글이 깨져 보이면 먼저 아래 명령을 실행한다.

```powershell
chcp 65001
$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
```

### 10.1 판매 동향 질문

```powershell
Invoke-RestMethod `
  -Uri "http://localhost:8000/agent/chat" `
  -Method Post `
  -ContentType "application/json" `
  -Body '{"question":"최근 6개월 OLED 판매 동향 분석해줘"}'
```

### 10.2 수주 현황 질문

```powershell
Invoke-RestMethod `
  -Uri "http://localhost:8000/agent/chat" `
  -Method Post `
  -ContentType "application/json" `
  -Body '{"question":"OLED 수주 현황과 납기 지연 확인해줘"}'
```

### 10.3 재고 리스크 질문

```powershell
Invoke-RestMethod `
  -Uri "http://localhost:8000/agent/chat" `
  -Method Post `
  -ContentType "application/json" `
  -Body '{"question":"TV OLED 재고 리스크 확인해줘"}'
```

### 10.4 고객사 프로필 질문

```powershell
Invoke-RestMethod `
  -Uri "http://localhost:8000/agent/chat" `
  -Method Post `
  -ContentType "application/json" `
  -Body '{"question":"CUST_A 고객사 프로필 확인해줘"}'
```

### 10.5 경쟁사 뉴스 질문

```powershell
Invoke-RestMethod `
  -Uri "http://localhost:8000/agent/chat" `
  -Method Post `
  -ContentType "application/json" `
  -Body '{"question":"LGD 경쟁사 뉴스 확인해줘"}'
```

### 10.6 브리핑 보고서 질문

```powershell
Invoke-RestMethod `
  -Uri "http://localhost:8000/agent/chat" `
  -Method Post `
  -ContentType "application/json" `
  -Body '{"question":"CUST_A 대상 브리핑 보고서 만들어줘"}'
```

## 11. Tool 직접 API 테스트

### 11.1 판매 동향 Tool

```powershell
Invoke-RestMethod `
  -Uri "http://localhost:8000/tools/sales-trend" `
  -Method Post `
  -ContentType "application/json" `
  -Body '{"start_month":"2026-01","end_month":"2026-06","product_group":"Mobile OLED","customer_id":null}'
```

### 11.2 수주 현황 Tool

```powershell
Invoke-RestMethod `
  -Uri "http://localhost:8000/tools/order-status" `
  -Method Post `
  -ContentType "application/json" `
  -Body '{"start_date":"2026-01-01","end_date":"2026-06-30","customer_id":null,"product_group":"Mobile OLED","status":null}'
```

### 11.3 재고 리스크 Tool

```powershell
Invoke-RestMethod `
  -Uri "http://localhost:8000/tools/inventory-risk" `
  -Method Post `
  -ContentType "application/json" `
  -Body '{"inventory_month":"2026-06","product_group":"TV OLED"}'
```

### 11.4 고객사 프로필 Tool

```powershell
Invoke-RestMethod `
  -Uri "http://localhost:8000/tools/customer-brief" `
  -Method Post `
  -ContentType "application/json" `
  -Body '{"customer_id":"CUST_A","start_month":"2026-01","end_month":"2026-06"}'
```

### 11.5 경쟁사 뉴스 Tool

```powershell
Invoke-RestMethod `
  -Uri "http://localhost:8000/tools/competitor-news" `
  -Method Post `
  -ContentType "application/json" `
  -Body '{"start_date":"2026-04-01","end_date":"2026-06-30","companies":["BOE","CSOT","LGD"],"category":null,"impact_level":null,"keyword":"OLED","product_group":null}'
```

### 11.6 브리핑 Report Tool

```powershell
Invoke-RestMethod `
  -Uri "http://localhost:8000/agent/briefing" `
  -Method Post `
  -ContentType "application/json" `
  -Body '{"topic":"2026년 2분기 사업 리뷰","customer_id":"CUST_A","start_date":"2026-04-01","end_date":"2026-06-30","sections":["sales","orders","inventory","competitor_news","recommended_actions"],"tool_results":{}}'
```

## 12. curl.exe로 테스트하는 방법

PowerShell에서 `curl`은 `Invoke-WebRequest` 별칭이다. 일반 curl 문법을 쓰려면 반드시 `curl.exe`를 사용한다.

```powershell
curl.exe -X POST "http://localhost:8000/agent/chat" `
  -H "Content-Type: application/json" `
  -d "{\"question\":\"최근 6개월 OLED 판매 동향 분석해줘\"}"
```

PowerShell에서는 보통 `Invoke-RestMethod`를 쓰는 편이 응답 확인이 쉽다.

## 13. 테스트 로그 참고

전체 테스트 실행 중 아래 로그가 보일 수 있다.

```text
Failed to execute get_sales_trend
Failed to execute get_order_status
Failed to execute get_inventory_risk
Failed to execute get_customer_profile
Failed to execute search_competitor_news
RuntimeError: database unavailable
```

이 로그는 각 Tool의 DB 오류 처리 테스트에서 의도적으로 발생시키는 값이다. 마지막 결과가 `OK`이면 테스트는 성공이다.

아래 경고도 테스트 실패 원인은 아니다.

```text
StarletteDeprecationWarning
```
