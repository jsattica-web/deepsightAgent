# Front (Vue 3 + Vite)

Display Market Intelligence Agent PoC의 프론트엔드입니다.
Google Cloud Run에 **nginx 컨테이너**로 배포되며, `/api` 요청을 Spring Boot 서비스로 중계합니다.

---

## 1. 아키텍처 (A안 - 리버스 프록시)

```
[개발]  브라우저 --> vite dev (8088) --/api/*--> localhost:8080        (Spring Boot)
[운영]  브라우저 --> nginx  (Cloud Run) --/api/*--> ${BACKEND_URL}      (Spring Boot)
                                                        |
                                                        v
                                                  agent-python (FastAPI)
```

브라우저 입장에서 오리진이 하나이므로 **CORS 설정이 필요 없습니다.**
개발과 운영 모두 `/api` 규칙이 동일하므로 환경별 재빌드도 필요 없습니다.

### API 호출 규칙

컴포넌트에서는 **반드시 상대경로**를 사용합니다.

```js
// O 올바른 방법
const res = await fetch('/api/chat', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ question: '3분기 판매 현황 알려줘' })
})

// X 절대 URL 금지 - A안의 장점이 전부 사라지고 CORS가 발생합니다
const res = await fetch('https://spring-api-xxxx.run.app/api/chat')
```

---

## 2. 포트 정리

| 대상 | 포트 | 비고 |
| --- | --- | --- |
| Front (vite dev / preview) | **8088** | `strictPort: true` - 충돌 시 즉시 실패 |
| Front (docker 컨테이너) | **8088** | Cloud Run에서는 주입된 `PORT`로 덮어써짐 |
| Backend (Spring Boot 로컬) | 8080 | 프록시 대상 |

---

## 3. 사전 요구사항

| 항목 | 버전 | 확인 |
| --- | --- | --- |
| Node.js | **20 이상** (Vite 6 요구사항) | `node --version` |
| npm | 10 이상 | `npm --version` |
| Docker Desktop | 최신 | `docker --version` |

---

## 4. 로컬 개발 (Node)

### 4.1 의존성 설치

최초 1회, 또는 `package.json`이 변경되었을 때 실행합니다.

```bash
npm ci
```

> `npm install`이 아니라 `npm ci`를 권장합니다. `package-lock.json`에 고정된 버전을
> 그대로 설치하므로 팀원 간 의존성이 어긋나지 않습니다.

### 4.2 개발 서버 실행

```bash
npm run dev
```

- 접속: http://localhost:8088
- 소스 저장 시 HMR로 즉시 반영됩니다.
- `/api/*` 요청은 `http://localhost:8080`(Spring Boot)으로 자동 프록시됩니다.

> **백엔드가 아직 없어도 화면 개발은 가능합니다.** 다만 `/api` 호출은
> `ECONNREFUSED`로 실패합니다. Spring Boot를 8080으로 띄우면 바로 연결됩니다.

### 4.3 프로덕션 빌드

```bash
npm run build
```

`dist/` 에 산출물이 생성됩니다. 파일명에 해시가 붙습니다. (예: `dist/assets/index-BVS_7nZK.js`)

### 4.4 빌드 결과 미리보기

```bash
npm run preview
```

빌드된 `dist/`를 http://localhost:8088 로 서빙합니다. 프록시 설정도 동일하게 적용됩니다.
배포 전 최종 확인용입니다.

---

## 5. Docker 빌드 및 실행

컨테이너는 **2단계(멀티스테이지)** 로 구성됩니다.

1. `node:22-alpine` - `npm ci` 후 `npm run build`
2. `nginx:1.27-alpine` - `dist/`만 복사해 서빙 + `/api` 프록시

최종 이미지에 `node_modules`가 포함되지 않아 크기가 작습니다.

### 5.1 이미지 빌드

```bash
docker build --platform linux/amd64 -t deepsight-front:local .
```

> **`--platform linux/amd64`는 필수입니다.** Apple Silicon(M1~M4) 맥에서 생략하면
> arm64 이미지가 만들어지고, Cloud Run 배포 직후 `Container failed to start`로 죽습니다.
> Windows/Intel 환경에서는 없어도 되지만, 팀 전체가 동일한 명령을 쓰도록 붙여 둡니다.

### 5.2 컨테이너 실행 (백엔드 없이 UI만 확인)

```bash
docker run --rm -p 8088:8088 deepsight-front:local
```

접속: http://localhost:8088

### 5.3 컨테이너 실행 (로컬 Spring Boot와 연동)

```bash
docker run --rm -p 8088:8088 -e BACKEND_URL=http://host.docker.internal:8080 deepsight-front:local
```

> 컨테이너 안에서 호스트 PC를 가리키려면 `localhost`가 아니라
> **`host.docker.internal`** 을 써야 합니다.

### 5.4 배포된 백엔드와 연동

```bash
docker run --rm -p 8088:8088 -e BACKEND_URL=https://spring-api-xxxxx.asia-northeast3.run.app -e INTERNAL_TOKEN=local-test-token deepsight-front:local
```

---

## 6. 환경변수

`nginx.conf.template`의 값이 컨테이너 시작 시 `envsubst`로 치환됩니다.

| 변수 | 기본값 | 설명 |
| --- | --- | --- |
| `PORT` | `8088` | nginx 리슨 포트. **Cloud Run이 자동 주입하므로 배포 시 설정 금지** |
| `BACKEND_URL` | `http://localhost:8080` | `/api` 프록시 대상. Spring Boot 서비스 URL |
| `INTERNAL_TOKEN` | (빈 값) | 백엔드 직접호출 차단용 공유 시크릿. `X-Internal-Token` 헤더로 전달 |

### `BACKEND_URL` 주의사항

**끝에 슬래시를 붙이면 안 됩니다.** nginx `proxy_pass` 동작이 달라집니다.

| 설정값 | `/api/chat` 요청이 전달되는 경로 | 결과 |
| --- | --- | --- |
| `https://host` | `/api/chat` | O 의도한 동작 |
| `https://host/` | `/chat` | X `/api` prefix가 잘림 |

---

## 7. 동작 테스트

### 7.1 헬스체크

컨테이너가 정상 기동했는지 확인합니다.

```bash
curl -i http://localhost:8088/healthz
```

`HTTP/1.1 200 OK` 와 본문 `ok`가 나오면 정상입니다.

### 7.2 정적 파일 서빙 확인

```bash
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8088/
```

`200`이 나와야 합니다.

### 7.3 SPA 라우팅 폴백 확인

존재하지 않는 경로도 `index.html`을 반환해야 합니다. (vue-router 도입 대비)

```bash
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8088/some/unknown/route
```

`404`가 아니라 `200`이 나와야 정상입니다.

### 7.4 API 프록시 확인

Spring Boot를 8080으로 띄운 뒤 실행합니다.

```bash
curl -i http://localhost:8088/api/health
```

nginx를 거쳐 백엔드 응답이 돌아오면 프록시가 동작하는 것입니다.
`502 Bad Gateway`면 `BACKEND_URL`이 잘못됐거나 백엔드가 떠 있지 않은 상태입니다.

### 7.5 nginx 설정 문법 검사

치환된 최종 설정을 눈으로 확인할 때 사용합니다.

```bash
docker run --rm deepsight-front:local sh -c "nginx -T 2>/dev/null | sed -n '/server {/,/^}/p'"
```

---

## 8. Cloud Run 배포

### 8.1 배포 (Dockerfile 자동 인식)

```bash
gcloud run deploy vue-web --source . --region asia-northeast3 --allow-unauthenticated --memory 512Mi --cpu 1 --set-env-vars "BACKEND_URL=https://spring-api-xxxxx.asia-northeast3.run.app"
```

> `PORT`는 **절대 `--set-env-vars`에 넣지 마세요.** Cloud Run이 예약한 변수라 배포가 거부됩니다.

### 8.2 백엔드 URL만 변경

```bash
gcloud run services update vue-web --region asia-northeast3 --update-env-vars "BACKEND_URL=https://spring-api-yyyyy.asia-northeast3.run.app"
```

프론트 재빌드 없이 갱신됩니다. (A안의 핵심 장점)

### 8.3 공유 시크릿을 Secret Manager로 주입

```bash
gcloud run services update vue-web --region asia-northeast3 --update-secrets "INTERNAL_TOKEN=internal-token:latest"
```

---

## 9. 트러블슈팅

| 증상 | 원인과 해결 |
| --- | --- |
| `Port 8088 is already in use` | 다른 프로세스가 점유 중입니다. `netstat -ano \| findstr :8088` 로 PID 확인 후 종료 |
| 배포 후 `Container failed to start` | arm64 이미지입니다. `--platform linux/amd64`로 다시 빌드하세요 |
| `/api` 호출이 502 (nginx) / 500 (vite dev) | 백엔드 미기동이거나 `BACKEND_URL` 오타입니다. vite dev 로그에 `ECONNREFUSED`가 찍히면 8080에 Spring Boot가 떠 있지 않은 것입니다 |
| `/api` 호출이 404 | `BACKEND_URL` 끝에 슬래시가 붙어 `/api` prefix가 잘렸습니다 |
| 프록시 응답이 Cloud Run 404 페이지 | `proxy_ssl_server_name on` 누락 시 발생. 현재 설정에는 포함되어 있습니다 |
| 새로고침하면 404 | `try_files` 폴백 문제. 현재 설정에는 포함되어 있습니다 |
| 배포했는데 예전 화면 | 브라우저 캐시. `index.html`은 no-cache라 강력 새로고침(Ctrl+F5)이면 해결됩니다 |
| LLM 응답 중 504 | `proxy_read_timeout`(현재 300s)과 Cloud Run `--timeout`을 함께 늘리세요 |
| 브라우저 콘솔에 CORS 에러 | 코드에서 절대 URL을 호출하고 있습니다. 상대경로 `/api/...`로 바꾸세요 |

---

## 10. 파일 구조

```
front/
├── Dockerfile              # 멀티스테이지 빌드 (node:22 -> nginx:1.27)
├── nginx.conf.template     # PORT/BACKEND_URL 치환, /api 프록시, SPA 폴백
├── vite.config.js          # 포트 8088, 개발용 /api 프록시
├── .dockerignore           # node_modules, dist 제외
├── .gitignore
├── index.html              # Vite 진입점
├── package.json
├── package-lock.json
└── src/
    ├── main.js
    ├── App.vue
    ├── assets/styles/      # base, icon, deepsight-panel, content-area
    └── components/
        ├── ContentArea.vue
        ├── DeepSightPanel.vue
        ├── content/        # PromptComposer, SessionDisplay
        ├── deepsight/      # SessionList, SessionItem
        └── icons/
```
