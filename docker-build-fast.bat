@echo off
chcp 65001 >nul
echo ========================================
echo Docker 이미지 빠른 빌드 (캐시 활용)
echo ========================================
echo.

echo [1] 백엔드 이미지 빌드 (캐시 활용)
docker build --network=host -t honghhj66/privalert-backend:1.5 ./backend
if errorlevel 1 (
    echo.
    echo 경고: 백엔드 빌드 실패 (네트워크 문제 가능)
    echo 로컬에 이미지가 있으면 docker-build-offline.bat 사용
    echo.
)
echo.

echo [2] 프론트엔드 이미지 빌드 (캐시 활용)
docker build --network=host -t honghhj66/privalert-frontend:1.5 ./frontend
if errorlevel 1 (
    echo.
    echo 경고: 프론트엔드 빌드 실패 (네트워크 문제 가능)
    echo 로컬에 이미지가 있으면 docker-build-offline.bat 사용
    echo.
)
echo.

echo [3] FastAPI 서버 이미지 빌드 (캐시 활용)
docker build --network=host -t honghhj66/privalert-fastapi:1.5 ./fastapi-backend
if errorlevel 1 (
    echo.
    echo 경고: FastAPI 빌드 실패 (네트워크 문제 가능)
    echo 로컬에 이미지가 있으면 docker-build-offline.bat 사용
    echo.
)
echo.

echo [4] 빌드된 이미지 목록 확인
docker images --format "table {{.Repository}}\t{{.Tag}}\t{{.ID}}\t{{.Size}}" | findstr "privalert"
echo.

echo ========================================
echo 빌드 완료! (캐시를 활용하여 빠르게 빌드됨)
echo ========================================
echo.
echo 참고: 완전히 새로 빌드하려면 docker-build-all.bat 사용
pause

