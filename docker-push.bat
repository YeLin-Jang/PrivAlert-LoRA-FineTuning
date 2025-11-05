@echo off
REM Docker 이미지 빌드 및 푸시 스크립트 (Windows)
REM Git 푸시 전에 Docker 이미지를 Docker Hub에 푸시

echo === PrivAlert Docker 이미지 빌드 및 푸시 ===
echo.

REM Docker Hub 사용자명 확인
if "%DOCKER_USERNAME%"=="" (
    set /p DOCKER_USERNAME="Docker Hub 사용자명을 입력하세요: "
)

echo Docker Hub 사용자명: %DOCKER_USERNAME%
echo.

REM 이미지 태그 설정
set BACKEND_IMAGE=%DOCKER_USERNAME%/privalert-backend:latest
set FRONTEND_IMAGE=%DOCKER_USERNAME%/privalert-frontend:latest

REM 1. 이미지 빌드
echo 1. Docker 이미지 빌드 중...
docker-compose build --no-cache
if errorlevel 1 (
    echo 오류: 이미지 빌드 실패
    pause
    exit /b 1
)

echo.
echo 2. 이미지 태그 지정 중...

REM 백엔드 이미지 태그
docker tag privalert-backend:latest %BACKEND_IMAGE%
if errorlevel 1 (
    echo 오류: 백엔드 이미지를 찾을 수 없습니다. docker-compose build를 먼저 실행하세요.
    pause
    exit /b 1
)

REM 프론트엔드 이미지 태그
docker tag privalert-frontend:latest %FRONTEND_IMAGE%
if errorlevel 1 (
    echo 오류: 프론트엔드 이미지를 찾을 수 없습니다. docker-compose build를 먼저 실행하세요.
    pause
    exit /b 1
)

echo ✓ 이미지 태그 지정 완료
echo   - %BACKEND_IMAGE%
echo   - %FRONTEND_IMAGE%
echo.

REM 3. Docker Hub 로그인 확인
echo 3. Docker Hub 로그인 확인 중...
docker info | findstr /C:"Username" >nul
if errorlevel 1 (
    echo Docker Hub에 로그인이 필요합니다.
    docker login
)

REM 4. 이미지 푸시
echo.
echo 4. Docker Hub에 이미지 푸시 중...
echo 백엔드 이미지 푸시 중...
docker push %BACKEND_IMAGE%
if errorlevel 1 (
    echo 오류: 백엔드 이미지 푸시 실패
    pause
    exit /b 1
)

echo 프론트엔드 이미지 푸시 중...
docker push %FRONTEND_IMAGE%
if errorlevel 1 (
    echo 오류: 프론트엔드 이미지 푸시 실패
    pause
    exit /b 1
)

echo.
echo ✓ 모든 작업 완료!
echo.
echo 푸시된 이미지:
echo   - %BACKEND_IMAGE%
echo   - %FRONTEND_IMAGE%
echo.
echo 이제 Git에 푸시할 수 있습니다!
pause

