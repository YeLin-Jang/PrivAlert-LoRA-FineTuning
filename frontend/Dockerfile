# 프론트엔드 Dockerfile
# Node.js 기반 React 애플리케이션

# 빌드 단계
FROM node:20-alpine AS builder

WORKDIR /app

# 의존성 파일 복사 및 설치
COPY package*.json ./
RUN npm ci --only=production=false

# 소스 코드 복사 및 빌드
COPY . .
# 빌드 시 환경 변수 (docker-compose에서 전달)
ARG VITE_API_BASE_URL=http://localhost:5000
ARG VITE_FASTAPI_BASE_URL=http://localhost:8000
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
ENV VITE_FASTAPI_BASE_URL=$VITE_FASTAPI_BASE_URL
RUN npm run build

# 프로덕션 단계
FROM nginx:alpine

# 보안: nginx 사용자로 실행 (이미 기본 설정됨)
# 보안 헤더 설정을 위한 nginx 설정 파일은 docker-compose에서 volumes로 마운트됨

# 빌드된 파일을 nginx로 복사
COPY --from=builder /app/dist /usr/share/nginx/html

# 보안: 불필요한 파일 제거
RUN rm -rf /usr/share/nginx/html/*.map

# 포트 노출
EXPOSE 80

# nginx 실행
CMD ["nginx", "-g", "daemon off;"]

