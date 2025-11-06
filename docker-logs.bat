@echo off
REM Docker 로그 확인 스크립트
REM 사용법: docker-logs.bat [서비스명]

cd /d %~dp0

if "%1"=="" (
    echo 모든 서비스 로그 확인 중...
    docker-compose logs -f
) else (
    echo %1 서비스 로그 확인 중...
    docker-compose logs -f %1
)


