@echo off
REM 백엔드 재빌드 및 재시작 스크립트
cd /d %~dp0

echo ========================================
echo 백엔드 재빌드 및 재시작
echo ========================================
echo.

echo 백엔드 컨테이너 중지 중...
docker-compose stop backend
echo.

echo 백엔드 이미지 재빌드 중...
docker-compose build --no-cache backend

if errorlevel 1 (
    echo.
    echo [오류] 이미지 빌드에 실패했습니다!
    pause
    exit /b 1
)

echo.
echo 백엔드 컨테이너 시작 중...
docker-compose up -d backend

if errorlevel 1 (
    echo.
    echo [오류] 컨테이너 시작에 실패했습니다!
    pause
    exit /b 1
)

echo.
echo [성공] 백엔드 재시작 완료!
echo.
echo 로그 확인: docker-compose logs -f backend
echo.

timeout /t 5 /nobreak >nul

echo 최근 로그 확인 중...
docker-compose logs --tail=20 backend

echo.
pause




