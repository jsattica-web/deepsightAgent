# syntax=docker/dockerfile:1
# Cloud Run 배포용 이미지. `docker build -t deepsight-agent .` 로 빌드한다.

# --- 1단계: 의존성 설치 -------------------------------------------------
# 빌드 단계에서만 pip 캐시와 빌드 부산물이 생기므로 최종 이미지에 남지 않는다.
FROM python:3.12-slim AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /build

# requirements.txt만 먼저 복사해 app 코드가 바뀌어도 이 레이어를 재사용한다.
COPY requirements.txt .
RUN python -m venv /opt/venv \
 && /opt/venv/bin/pip install --requirement requirements.txt


# --- 2단계: 실행 이미지 -------------------------------------------------
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    PORT=8080

# 1단계에서 만든 가상환경만 통째로 가져온다.
COPY --from=builder /opt/venv /opt/venv

WORKDIR /app
COPY app ./app

# 루트 권한 없이 실행한다. Cloud Run은 임의 UID로도 컨테이너를 띄울 수 있다.
RUN useradd --create-home --uid 1000 appuser \
 && chown --recursive appuser:appuser /app
USER appuser

# Cloud Run은 이 값을 참고하지 않지만 로컬 실행 편의를 위해 남겨둔다.
EXPOSE 8080

# Cloud Run이 주입하는 PORT를 그대로 사용한다. 값이 없으면 8080으로 떨어진다.
# exec를 붙여 uvicorn이 PID 1이 되게 하고, 배포 교체 시 SIGTERM을 직접 받게 한다.
CMD exec uvicorn app.main:app \
    --host 0.0.0.0 \
    --port "${PORT:-8080}" \
    --workers 1 \
    --timeout-keep-alive 65
