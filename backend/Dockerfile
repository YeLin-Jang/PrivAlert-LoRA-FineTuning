# 백엔드 Dockerfile
# Python 3.11 기반 Flask 애플리케이션

FROM python:3.11-slim

# 보안: 비root 사용자 생성
RUN groupadd -r appuser && useradd -r -g appuser appuser

# 작업 디렉토리 설정
WORKDIR /app

# 시스템 의존성 설치
RUN apt-get update && apt-get install -y \
    libmagic1 \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Python 의존성 복사 및 설치
# 레이어 캐싱 최적화: requirements.txt만 먼저 복사하여 의존성 변경 시에만 재빌드
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt
# openai-whisper는 triton 의존성 충돌로 인해 별도 설치
# torch 2.8.0은 triton 3.4.0을 요구하지만, openai-whisper 20231117은 triton<3을 요구
# 해결: openai-whisper를 --no-deps로 설치 (triton은 torch에서 이미 설치됨)
RUN pip install --no-cache-dir --no-deps openai-whisper>=20231117

# 애플리케이션 코드 복사
COPY . .

# 보안: 필요한 디렉토리 생성 및 권한 설정
RUN mkdir -p /app/data/results && \
    mkdir -p /home/appuser/.cache && \
    chown -R appuser:appuser /app && \
    chown -R appuser:appuser /home/appuser

# 보안: 비root 사용자로 전환
USER appuser

# 환경 변수 설정
ENV FLASK_APP=wsgi.py
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
# Hugging Face 캐시 디렉토리 설정 (appuser 홈 디렉토리 사용, 쓰기 가능)
ENV HF_HOME=/home/appuser/.cache/huggingface
ENV TRANSFORMERS_CACHE=/home/appuser/.cache/huggingface
ENV HF_DATASETS_CACHE=/home/appuser/.cache/huggingface/datasets

# 포트 노출
EXPOSE 5000

# 헬스체크
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

# 애플리케이션 실행
CMD ["python", "wsgi.py"]

