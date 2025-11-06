@echo off
REM Docker 컨테이너 중지 스크립트
REM 사용법: docker-stop.bat

echo ========================================
echo PrivAlert Docker 컨테이너 중지
echo ========================================
echo.

cd /d %~dp0

REM 컨테이너 중지
echo 컨테이너 중지 중...
docker-compose down

if errorlevel 1 (
    echo [오류] 컨테이너 중지에 실패했습니다!
    pause
    exit /b 1
)

echo.
echo [성공] 모든 컨테이너가 중지되었습니다!
echo.

pause




