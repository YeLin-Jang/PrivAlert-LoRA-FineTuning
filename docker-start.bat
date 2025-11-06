@echo off
REM Docker 로컬 테스트 시작 스크립트
REM 사용법: docker-start.bat

echo ========================================
echo PrivAlert Docker 로컬 테스트 시작
echo ========================================
echo.

REM 현재 디렉토리 확인
cd /d %~dp0
echo 현재 디렉토리: %CD%
echo.

REM .env 파일 확인
if not exist .env (
    echo [경고] .env 파일이 없습니다!
    echo .env 파일을 생성해야 합니다.
    echo.
    echo DOCKER_LOCAL_TEST.md 파일을 참조하여 .env 파일을 생성하세요.
    pause
    exit /b 1
) else (
    echo [확인] .env 파일이 존재합니다.
    echo.
)

REM Docker 및 Docker Compose 확인
docker --version >nul 2>&1
if errorlevel 1 (
    echo [오류] Docker가 설치되지 않았습니다!
    echo Docker Desktop을 설치하세요: https://www.docker.com/products/docker-desktop
    pause
    exit /b 1
)

docker-compose --version >nul 2>&1
if errorlevel 1 (
    echo [오류] Docker Compose가 설치되지 않았습니다!
    pause
    exit /b 1
)

echo [확인] Docker 및 Docker Compose가 설치되어 있습니다.
echo.

REM 기존 컨테이너 정리 (선택사항)
echo 기존 컨테이너를 정리하시겠습니까? (Y/N)
set /p cleanup=
if /i "%cleanup%"=="Y" (
    echo 기존 컨테이너 정리 중...
    docker-compose down
    echo.
)

REM 이미지 빌드
echo ========================================
echo Docker 이미지 빌드 시작
echo ========================================
echo.
echo 이 작업은 처음 실행 시 5-10분 정도 소요될 수 있습니다...
echo.

docker-compose build

if errorlevel 1 (
    echo.
    echo [오류] 이미지 빌드에 실패했습니다!
    echo 로그를 확인하세요: docker-compose build 2>&1 ^| more
    pause
    exit /b 1
)

echo.
echo [성공] 이미지 빌드 완료!
echo.

REM 컨테이너 시작
echo ========================================
echo Docker 컨테이너 시작
echo ========================================
echo.

docker-compose up -d

if errorlevel 1 (
    echo.
    echo [오류] 컨테이너 시작에 실패했습니다!
    echo 로그를 확인하세요: docker-compose logs
    pause
    exit /b 1
)

echo.
echo [성공] 컨테이너 시작 완료!
echo.

REM 잠시 대기 (서비스 초기화 시간)
echo 서비스 초기화를 위해 10초 대기 중...
timeout /t 10 /nobreak >nul

REM 상태 확인
echo.
echo ========================================
echo 컨테이너 상태 확인
echo ========================================
echo.
docker-compose ps
echo.

REM 접속 정보 출력
echo ========================================
echo 접속 정보
echo ========================================
echo.
echo 프론트엔드: http://localhost:3000
echo 백엔드 API: http://localhost:5000/health
echo FastAPI:    http://localhost:8000/health
echo.
echo 로그 확인: docker-compose logs -f
echo 중지:      docker-compose down
echo.
echo ========================================
echo 테스트 시작!
echo ========================================
echo.

pause


