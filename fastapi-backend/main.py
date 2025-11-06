"""
FastAPI 메인 애플리케이션
이메일 인증번호 전송 및 검증 기능 포함
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
from contextlib import asynccontextmanager

from app.routes import auth_routes
from app.database import init_db, close_db
from app.services.verification_service import init_redis, close_redis
from app.core.config import settings
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


# 애플리케이션 라이프사이클 관리
@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 시작/종료 시 실행"""
    # 시작 시 초기화
    await init_db()
    await init_redis()
    yield
    # 종료 시 정리
    await close_redis()
    await close_db()

# FastAPI 앱 생성
app = FastAPI(
    title="PrivAlert FastAPI Backend",
    description="이메일 인증번호 전송 및 검증 API",
    version="1.0.0",
    lifespan=lifespan
)

# CORS 설정 (보안: 허용된 오리진만)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 라우터 등록
app.include_router(auth_routes.router, prefix="/api/v1", tags=["인증"])


# 헬스 체크 엔드포인트
@app.get("/health")
async def health_check():
    """헬스 체크 엔드포인트"""
    return JSONResponse(
        content={"status": "healthy", "service": "PrivAlert FastAPI Backend"},
        status_code=200
    )


# 루트 엔드포인트
@app.get("/")
async def root():
    """루트 엔드포인트"""
    return JSONResponse(
        content={
            "service": "PrivAlert FastAPI Backend",
            "version": "1.0.0",
            "docs": "/docs"
        },
        status_code=200
    )

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
