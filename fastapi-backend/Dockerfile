# FastAPI 백엔드 Dockerfile
# Python 3.11 기반 FastAPI 애플리케이션

FROM python:3.11-slim

# 보안: 비root 사용자 생성
RUN groupadd -r appuser && useradd -r -g appuser appuser

# 작업 디렉토리 설정
WORKDIR /app

# 시스템 의존성 설치
RUN apt-get update && apt-get install -y \
    curl \
    gcc \
    g++ \
    default-libmysqlclient-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Python 의존성 복사 및 설치
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 시스템 빌드 도구 제거 (이미지 크기 최적화)
RUN apt-get purge -y gcc g++ pkg-config && \
    apt-get autoremove -y && \
    apt-get clean

# 애플리케이션 코드 복사
COPY . .

# 보안: 필요한 디렉토리 생성 및 권한 설정
RUN mkdir -p /app/data && \
    chown -R appuser:appuser /app

# 보안: 비root 사용자로 전환
USER appuser

# 환경 변수 설정
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# 포트 노출
EXPOSE 8000

# 헬스 체크
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 애플리케이션 실행
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

