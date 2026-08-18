# syntax=docker/dockerfile:1

# ---------- build stage ----------
# Vite 6은 Node 18 이상을 요구한다. LTS인 22를 사용한다.
FROM node:22-alpine AS build

WORKDIR /app

# package.json이 바뀌지 않으면 의존성 레이어를 캐시한다.
COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build

# ---------- runtime stage ----------
FROM nginx:1.27-alpine

# 기본 설정을 제거하고 템플릿만 사용한다.
RUN rm -f /etc/nginx/conf.d/default.conf

COPY --from=build /app/dist /usr/share/nginx/html

# nginx 공식 이미지는 /etc/nginx/templates/*.template 을 envsubst로 치환해
# /etc/nginx/conf.d/ 에 배치한다. 여기서 PORT와 BACKEND_URL이 주입된다.
COPY nginx.conf.template /etc/nginx/templates/default.conf.template

# nginx 내장 변수($uri 등)가 치환되지 않도록 대상 변수를 명시적으로 제한한다.
ENV NGINX_ENVSUBST_FILTER="^(PORT|BACKEND_URL|INTERNAL_TOKEN)$"

# Cloud Run은 PORT를 직접 주입하므로 이 값을 덮어쓴다.
# 아래 기본값은 로컬에서 docker run 할 때만 쓰인다. (프론트는 8088로 통일)
ENV PORT=8088
ENV BACKEND_URL=http://localhost:8080
ENV INTERNAL_TOKEN=""

EXPOSE 8088

CMD ["nginx", "-g", "daemon off;"]
