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
