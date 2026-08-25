# agent-python

Python 3.12, FastAPI, psycopg2 기반의 DeepSight Agent Tool API입니다.

## 로컬 실행

```powershell
cd agent-python
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
$env:DATABASE_URL="postgresql://USER:PASSWORD@HOST:5432/postgres?sslmode=require"
uvicorn app.main:app --reload
```

`DATABASE_URL`에는 실제 접속 정보를 환경변수로 설정합니다. `.env`나 비밀번호는 저장소에 커밋하지 마세요.

## Docker 실행

```powershell
docker build -t deepsight-agent-python .
docker run --rm -p 8000:8000 -e DATABASE_URL="$env:DATABASE_URL" deepsight-agent-python
```

## 서버 띄우기 (Supabase)

프로젝트의 `.env.example`에 유효한 Supabase `DATABASE_URL`이 설정되어 있다는 전제에서 `agent-python` 폴더에서 실행합니다.

```powershell
python -m uvicorn app.main:app --reload --env-file .env.example
```

정상 기동 후 아래 주소에서 확인할 수 있습니다.

- API 서버: `http://localhost:8000`
- Swagger UI: `http://localhost:8000/docs`
- OpenAPI JSON: `http://localhost:8000/openapi.json`

> `.env.example`의 `DATABASE_URL`이 샘플/마스킹 값이면 실제 Supabase 접속 정보로 교체해야 DB를 사용하는 Tool 테스트가 성공합니다.

## curl 테스트

Windows PowerShell에서는 아래 예시처럼 `curl.exe`를 사용하면 됩니다.

### 상태 확인

```powershell
curl.exe "http://localhost:8000/health"
```

### 판매 동향 조회

```powershell
curl.exe -X POST "http://localhost:8000/tools/sales-trend" `
  -H "Content-Type: application/json" `
  -d '{
    "start_month": "2026-01",
    "end_month": "2026-06",
    "product_group": "Mobile OLED",
    "customer_id": null
  }'
```

### 수주 현황 조회

```powershell
curl.exe -X POST "http://localhost:8000/tools/order-status" `
  -H "Content-Type: application/json" `
  -d '{
    "start_date": "2026-01-01",
    "end_date": "2026-06-30",
    "customer_id": null,
    "product_group": "Mobile OLED",
    "status": null
  }'
```

### 재고 리스크 조회 (기존 12번 Tool)

```powershell
curl.exe -X POST "http://localhost:8000/tools/inventory-risk" `
  -H "Content-Type: application/json" `
  -d '{
    "inventory_month": "2026-06",
    "product_group": "TV OLED"
  }'
```

### 13. Customer Profile / Customer Brief

API 경로는 프로젝트 `api-spec.md`에 맞춰 `/tools/customer-brief`를 사용하고, 내부 Tool 함수는 `get_customer_profile`입니다.

```powershell
curl.exe -X POST "http://localhost:8000/tools/customer-brief" `
  -H "Content-Type: application/json" `
  -d '{
    "customer_id": "CUST_A",
    "start_month": "2026-01",
    "end_month": "2026-06"
  }'
```

### 14. Competitor News

```powershell
curl.exe -X POST "http://localhost:8000/tools/competitor-news" `
  -H "Content-Type: application/json" `
  -d '{
    "start_date": "2026-04-01",
    "end_date": "2026-06-30",
    "companies": ["BOE", "CSOT", "LGD"],
    "category": null,
    "impact_level": null,
    "keyword": "OLED",
    "product_group": null
  }'
```

### 15. Briefing Report

`create_briefing_report`는 DB를 직접 조회하지 않고 앞선 Tool들의 결과(`tool_results`)를 조합합니다. 아래 요청은 endpoint 자체를 확인할 수 있는 최소 테스트입니다.

```powershell
curl.exe -X POST "http://localhost:8000/agent/briefing" `
  -H "Content-Type: application/json" `
  -d '{
    "topic": "2026년 2분기 사업 리뷰",
    "customer_id": "CUST_A",
    "start_date": "2026-04-01",
    "end_date": "2026-06-30",
    "sections": [
      "sales",
      "orders",
      "inventory",
      "competitor_news",
      "recommended_actions"
    ],
    "tool_results": {}
  }'
```

다른 Tool 결과까지 넣어 브리핑 통합을 테스트하려면 `tool_results`에 `sales`, `orders`, `inventory`, `competitor_news` 결과를 넣으면 됩니다.

## Swagger UI 테스트

서버 실행 후 브라우저에서 아래 주소로 접속합니다.

```text
http://localhost:8000/docs
```

Swagger 화면에서 다음 endpoint를 직접 펼쳐 `Try it out`으로 테스트할 수 있습니다.

- `POST /tools/customer-brief`
- `POST /tools/competitor-news`
- `POST /agent/briefing`
