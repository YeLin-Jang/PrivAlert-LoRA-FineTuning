@echo off
REM 백엔드 로그 확인 스크립트
cd /d %~dp0
echo ========================================
echo 백엔드 로그 (최근 100줄)
echo ========================================
echo.
docker-compose logs --tail=100 backend
echo.
echo ========================================
echo 전체 로그를 보려면: docker-compose logs -f backend
echo ========================================
pause




