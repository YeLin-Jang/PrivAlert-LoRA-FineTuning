@echo off
REM FastAPI 백엔드 빠른 설치 스크립트 (Windows)
REM Rust 컴파일 문제를 피하기 위해 사전 빌드된 패키지만 사용

echo ====================================
echo FastAPI Backend 설치 시작
echo ====================================

REM pip 업그레이드
echo [1/6] pip 업그레이드 중...
python -m pip install --upgrade pip

REM FastAPI 및 서버
echo [2/6] FastAPI 및 서버 패키지 설치 중...
pip install fastapi==0.109.0 uvicorn[standard]==0.27.0

REM Pydantic (사전 빌드된 wheel만 사용)
echo [3/6] Pydantic 설치 중...
pip install --only-binary :all: pydantic==2.6.1 pydantic-settings==2.1.0

REM 데이터베이스
echo [4/6] 데이터베이스 패키지 설치 중...
pip install sqlalchemy[asyncio]==2.0.23 aiosqlite==0.19.0

REM 비밀번호 해싱
echo [5/6] bcrypt 설치 중...
pip install --only-binary :all: bcrypt==4.1.2

REM 기타 패키지
echo [6/6] 기타 패키지 설치 중...
pip install python-dotenv==1.0.1 python-multipart==0.0.6

REM 설치 확인
echo.
echo ====================================
echo 설치 확인 중...
echo ====================================
python -c "import fastapi, bcrypt, pydantic; print('✅ 모든 패키지 설치 완료!')"

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ====================================
    echo ✅ 설치 성공!
    echo ====================================
    echo 이제 서버를 실행할 수 있습니다:
    echo   python main.py
) else (
    echo.
    echo ====================================
    echo ❌ 설치 실패
    echo ====================================
    echo INSTALL_GUIDE.md 파일을 참고하세요.
)

pause

