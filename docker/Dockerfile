# 멀티스테이지 빌드 - Flask Backend
FROM python:3.10-slim AS backend

WORKDIR /app

# 시스템 패키지 설치
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libmagic1 \
    libpq-dev \
    default-libmysqlclient-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Python 의존성 설치
COPY backend/requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Backend 코드 복사
COPY backend/ .

ENV PYTHONUNBUFFERED=1
ENV FLASK_APP=wsgi.py
ENV FLASK_ENV=production

EXPOSE 5000

CMD ["python", "wsgi.py"]

# 멀티스테이지 빌드 - React Frontend
FROM node:18-alpine AS frontend

WORKDIR /app

# Frontend 의존성 설치
COPY frontend/package*.json ./
RUN npm ci

# Frontend 코드 복사
COPY frontend/ .

EXPOSE 3000

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "3000"]

