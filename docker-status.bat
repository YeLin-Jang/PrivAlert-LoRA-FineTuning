@echo off
REM Docker 컨테이너 상태 확인 스크립트
REM 사용법: docker-status.bat

cd /d %~dp0

echo ========================================
echo PrivAlert Docker 컨테이너 상태
echo ========================================
echo.

docker-compose ps

echo.
echo ========================================
echo 헬스체크
echo ========================================
echo.

echo Backend 헬스체크:
curl -s http://localhost:5000/health 2>nul
if errorlevel 1 (
    echo [오류] Backend에 연결할 수 없습니다
) else (
    echo [성공] Backend 정상 작동
)
echo.

echo FastAPI 헬스체크:
curl -s http://localhost:8000/health 2>nul
if errorlevel 1 (
    echo [오류] FastAPI에 연결할 수 없습니다
) else (
    echo [성공] FastAPI 정상 작동
)
echo.

pause




