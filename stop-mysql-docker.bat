@echo off
REM Docker MySQL 중지 스크립트

echo ========================================
echo Docker MySQL 중지 스크립트
echo ========================================
echo.

echo Docker MySQL 컨테이너 중지 중...
docker-compose -f docker-compose.yml -f docker-compose.dev.yml down mysql

if %errorlevel% == 0 (
    echo.
    echo Docker MySQL이 성공적으로 중지되었습니다.
    echo.
) else (
    echo.
    echo 오류: Docker MySQL 중지에 실패했습니다.
    echo.
)

pause

