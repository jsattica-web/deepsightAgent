# Cloud Run 배포 가이드

front(Vue+nginx)와 agent-python(FastAPI)을 **각각 별도 Cloud Run 서비스**로 띄우고,
front의 nginx가 `/api` 요청을 agent-python으로 중계하는 구성이다.

```
브라우저 ──> front (nginx, Cloud Run) ──/api/*──> agent-python (FastAPI, Cloud Run) ──> Supabase
```

브라우저 입장에서 오리진이 front 하나뿐이라 **CORS 설정이 필요 없다.**
(agent-python에는 CORS 미들웨어가 없으므로 이 프록시 구조가 필수다.)

---

## 1. 포트

컨테이너가 리스닝하는 포트다. Cloud Run은 `PORT` 환경변수를 주입하며 아래 기본값을 덮어쓴다.

| 서비스 | 컨테이너 기본 포트 | 비고 |
| --- | --- | --- |
| front | **8088** | nginx가 `${PORT}`로 listen |
| agent-python | **8080** | uvicorn이 `${PORT:-8080}`으로 bind |

---

## 2. 환경변수

### agent-python

| 변수 | 필수 | 설명 |
| --- | --- | --- |
| `DATABASE_URL` | O | Supabase PostgreSQL 접속 문자열. **Secret Manager 사용 권장** |
| `DB_POOL_MAX_SIZE` | X | 커넥션 풀 최대 수. 기본 5 |
| `PORT` | 자동 | Cloud Run이 주입 |

### front

| 변수 | 필수 | 설명 |
| --- | --- | --- |
| `BACKEND_URL` | O | agent-python의 Cloud Run URL. **끝에 슬래시 금지** |
| `INTERNAL_TOKEN` | X | 공유 시크릿 헤더. 현재 agent-python에 검증 로직이 없어 비워 둔다 |
| `PORT` | 자동 | Cloud Run이 주입 |

> `BACKEND_URL` 기본값은 자리표시자(`https://agent-python-REPLACE-ME.a.run.app`)다.
> 배포 시 반드시 실제 URL로 덮어써야 한다.

---

## 3. 배포 순서

agent-python을 먼저 올려 URL을 받고, 그 값을 front에 주입한다. 순환 의존이 없다.

### 3-1. agent-python 배포

```bash
gcloud run deploy agent-python --source agent-python --region asia-northeast3
```

DB 접속 정보 주입 (Secret Manager 권장):

```bash
gcloud run services update agent-python --region asia-northeast3 --set-secrets DATABASE_URL=agent-db-url:latest
```

### 3-2. 발급된 URL 확인

```bash
gcloud run services describe agent-python --region asia-northeast3 --format "value(status.url)"
```

### 3-3. front 배포

위에서 얻은 URL을 `BACKEND_URL`로 넣는다.

```bash
gcloud run deploy front --source front --region asia-northeast3 --allow-unauthenticated --set-env-vars BACKEND_URL=https://agent-python-xxxxx.a.run.app
```

---

## 4. 경로 규칙

agent-python은 `/api` 프리픽스 **없이** 서빙한다. nginx가 rewrite로 프리픽스를 제거한다.

| 브라우저 요청 | agent-python 수신 |
| --- | --- |
| `/api/agent/chat` | `/agent/chat` |
| `/api/tools/sales-trend` | `/tools/sales-trend` |
| `/api/health` | `/health` |

프론트 코드에서는 **반드시 상대경로 `/api/...`** 를 쓴다. 절대 URL을 쓰면 CORS가 발생한다.

---

## 5. 주의사항

- **타임아웃**: nginx는 `proxy_read_timeout 300s`, Cloud Run 기본 요청 타임아웃도 300초다. 응답이 더 길어지면 양쪽을 함께 올린다.
- **DB 연결**: agent-python은 공개 인터넷으로 Supabase에 접속한다. VPC 커넥터는 필요 없다.
- **인증**: agent-python을 `--allow-unauthenticated`로 열면 URL을 아는 누구나 호출할 수 있다.
  DB 커넥션이 readonly라 변조 위험은 없지만 조회는 노출된다. 인증 방식은 팀 결정 필요.

---

## 6. 로컬 Docker 실행 (배포 전 검증)

Cloud Run에 올리기 전 두 컨테이너를 같은 네트워크에 띄워 동일한 구조를 재현한다.
컨테이너끼리는 **서비스명(컨테이너명)으로 통신**하므로, `BACKEND_URL`만 Cloud Run URL 대신
컨테이너명으로 바꿔주면 된다.

### 6-1. 이미지 빌드

```bash
docker build -t deepsight-agent:local ./agent-python
docker build -t deepsight-front:local ./front
```

### 6-2. 네트워크 생성

같은 네트워크에 있어야 front가 `http://deepsight-agent:8080` 으로 agent를 찾을 수 있다.

```bash
docker network create deepsight-net
```

### 6-3. 컨테이너 실행

agent-python (DB 접속 정보는 `agent-python/.env` 에서 주입):

```bash
docker run -d --name deepsight-agent --network deepsight-net --env-file agent-python/.env -p 8080:8080 deepsight-agent:local
```

front (`BACKEND_URL` 을 agent 컨테이너로 지정):

```bash
docker run -d --name deepsight-front --network deepsight-net -e BACKEND_URL=http://deepsight-agent:8080 -p 8088:8088 deepsight-front:local
```

### 6-4. 확인

브라우저에서 `http://localhost:8088` 접속.

| 확인 항목 | 명령 | 기대 결과 |
| --- | --- | --- |
| agent 직접 | `curl http://localhost:8080/health` | `"database":"connected"` |
| front 정적 | `curl http://localhost:8088/healthz` | `ok` |
| **프록시 경유** | `curl http://localhost:8088/api/health` | `"database":"connected"` |

세 번째가 200이면 `/api` 프리픽스 제거와 컨테이너 간 통신이 모두 정상이다.

### 6-5. 정리

```bash
docker rm -f deepsight-front deepsight-agent
docker network rm deepsight-net
```

---

## 7. 검증 기록 (2026-08-28)

로컬 Docker에서 위 구성으로 실행해 프론트 화면에서 질문 3건을 테스트했다. **전부 정상 동작.**

| # | 질문 | 결과 |
| --- | --- | --- |
| 1 | 최근 6개월 OLED 판매 동향 분석해줘 | 판매량 69,340 → 81,677개 (+17.8%), 6행 표 |
| 2 | TV OLED 재고 리스크 확인해줘 | 과잉재고 판정, 기말재고 13,630 / 안전재고 5,000 |
| 3 | CUST_A 고객사 프로필 확인해줘 | Aster Mobile Systems, 판매 119,294개 / 수주 105,408개 |

경로 변환도 로그로 확인했다. 브라우저 콘솔 오류는 0건이었다.

```
nginx  : "POST /api/agent/chat HTTP/1.1" 200
agent  : "POST /agent/chat HTTP/1.1" 200 OK      <- /api 가 제거되어 도착
```

### 미구현 사항

- **차트 렌더링**: 응답의 `charts` 데이터는 정상 수신되지만 그래프로 그리지 않는다.
  `front/package.json` 의존성이 `vue` 하나뿐이라 차트 라이브러리 도입 여부는 결정 필요.
  현재는 "차트 데이터 N건이 함께 도착했습니다" 안내만 표시한다.
- **인증**: 5장 주의사항 참고.
