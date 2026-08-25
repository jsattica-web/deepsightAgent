# agent-python

Python 3.12, FastAPI, psycopg2 기반의 최소 판매 동향 Agent API입니다.

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

## Supabase 연결

현재 Supabase 프로젝트:

- Project: `deepSightAgent`
- Project ref: `gcnzhbhhitiahvgchjty`
- Region: `ap-northeast-1`
- Direct DB host: `db.gcnzhbhhitiahvgchjty.supabase.co`

Supabase Dashboard의 **Connect** 메뉴에서 데이터베이스 비밀번호가 포함된 Postgres connection string을 복사한 뒤 `DATABASE_URL`로 설정합니다.

```powershell
cd agent-python
Copy-Item .env.example .env
# .env의 [YOUR-PASSWORD]를 Supabase DB password로 교체하거나,
# 아래처럼 현재 PowerShell 세션에 직접 설정하세요.
$env:DATABASE_URL="postgresql://postgres:[YOUR-PASSWORD]@db.gcnzhbhhitiahvgchjty.supabase.co:5432/postgres?sslmode=require"
uvicorn app.main:app --reload
```

Supabase 공식 문서 기준으로, 장시간 실행되는 FastAPI 백엔드에서는 Direct connection을 우선 사용할 수 있습니다. 실행 환경이 IPv4-only라 direct host 접속이 실패하면 Dashboard의 Session pooler connection string을 `DATABASE_URL`에 넣어 사용하세요.

## Docker 실행

```powershell
docker build -t deepsight-agent-python .
docker run --rm -p 8000:8000 -e DATABASE_URL="$env:DATABASE_URL" deepsight-agent-python
```

## 서버 띄우기 (supabase)
python -m uvicorn app.main:app --reload --env-file .env.example

## curl 테스트

상태 확인:

```bash
curl http://localhost:8000/health
```

판매 동향 조회:

```bash
curl -X POST "http://localhost:8000/docs#/default/sales_trend_tools_sales_trend_post" \
  -H "Content-Type: application/json" \
  -d '{
    "start_month": "2026-01",
    "end_month": "2026-06",
    "product_group": "Mobile OLED",
    "customer_id": null
  }'
```

판매 동향 조회:

```bash
curl -X POST "http://localhost:8000/docs#/default/order_status_tools_order_status_post"\
  -H "Content-Type: application/json" \
  -d '{
    "start_date": "2026-01-01",
    "end_date": "2026-06-30",
    "customer_id": null,
    "product_group": "Mobile OLED",
    "status": null
}'
```

재고 조회:
```bash
curl -X POST "http://localhost:8000/docs#/default/inventory_risk_tools_inventory_risk_post"\
  -H "Content-Type: application/json" \
  -d '{
    "inventory_month": "2026-06",
    "product_group": "TV OLED",
}'
```

Swagger UI는 `http://localhost:8000/docs`에서 확인할 수 있습니다.


## 13~15번 Tool curl 테스트

### 13. Customer Profile / Customer Brief

```bash
curl -X POST "http://localhost:8000/tools/customer-brief" \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": "CUST_A",
    "start_month": "2026-01",
    "end_month": "2026-06"
  }'
```

### 14. Competitor News

```bash
curl -X POST "http://localhost:8000/tools/competitor-news" \
  -H "Content-Type: application/json" \
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

```bash
curl -X POST "http://localhost:8000/agent/briefing" \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "2026년 2분기 사업 리뷰",
    "customer_id": "CUST_A",
    "start_date": "2026-04-01",
    "end_date": "2026-06-30",
    "sections": ["sales", "orders", "inventory", "competitor_news", "recommended_actions"],
    "tool_results": {}
  }'
```
