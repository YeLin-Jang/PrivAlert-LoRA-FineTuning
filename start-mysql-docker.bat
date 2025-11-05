@echo off
REM Docker MySQL만 실행하는 스크립트
REM 로컬 MySQL이 3306 포트를 사용 중이면 중지 필요

echo ========================================
echo Docker MySQL 시작 스크립트
echo ========================================
echo.

REM 관리자 권한 확인
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo 관리자 권한이 필요합니다. 관리자 권한으로 재실행합니다...
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)

REM 로컬 MySQL 서비스 확인
echo [1/3] 로컬 MySQL 서비스 확인 중...
sc query MySQL80 >nul 2>&1
if %errorlevel% == 0 (
    echo 경고: 로컬 MySQL 서비스가 실행 중입니다.
    echo Docker MySQL을 실행하려면 로컬 MySQL을 중지해야 합니다.
    echo.
    echo 로컬 MySQL을 중지하시겠습니까? (Y/N)
    set /p stop_local=">> "
    if /i "%stop_local%"=="Y" (
        echo 로컬 MySQL 서비스 중지 중...
        net stop MySQL80
        if %errorlevel% == 0 (
            echo 로컬 MySQL 서비스가 중지되었습니다.
        ) else (
            echo 오류: 로컬 MySQL 서비스를 중지할 수 없습니다.
            echo 서비스 이름을 확인하세요: sc query | findstr MySQL
            pause
            exit /b 1
        )
    ) else (
        echo 로컬 MySQL을 중지하지 않았습니다.
        echo Docker MySQL 실행 시 포트 충돌이 발생할 수 있습니다.
        echo.
        echo 포트 충돌이 발생하면:
        echo 1. 관리자 권한으로 이 스크립트를 실행하거나
        echo 2. 작업 관리자 - 서비스에서 MySQL을 수동으로 중지하세요.
        echo.
        pause
    )
)

REM 기존 Docker MySQL 컨테이너 정리
echo.
echo [2/3] 기존 Docker MySQL 컨테이너 정리 중...
docker-compose -f docker-compose.yml -f docker-compose.dev.yml down mysql 2>nul

REM Docker MySQL 실행
echo.
echo [3/3] Docker MySQL 실행 중...
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d mysql

if %errorlevel% == 0 (
    echo.
    echo ========================================
    echo Docker MySQL이 성공적으로 시작되었습니다!
    echo ========================================
    echo.
    echo 접속 정보:
    echo   - 호스트: localhost
    echo   - 포트: 3306
    echo   - 데이터베이스: privalert
    echo   - 사용자: privalert_user
    echo.
    echo MySQL 로그 확인:
    echo   docker-compose -f docker-compose.yml -f docker-compose.dev.yml logs -f mysql
    echo.
    echo MySQL 중지:
    echo   docker-compose -f docker-compose.yml -f docker-compose.dev.yml down
    echo.
) else (
    echo.
    echo 오류: Docker MySQL 실행에 실패했습니다.
    echo 포트 3306이 이미 사용 중일 수 있습니다.
    echo.
    pause
    exit /b 1
)

pause

