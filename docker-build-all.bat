@echo off
chcp 65001 >nul
echo ========================================
echo Docker 이미지 빌드 스크립트 시작
echo ========================================
echo.

echo [1] 사용하지 않는 이미지/컨테이너/네트워크/캐시 전부 정리
docker system prune -af
echo.

echo [2] 기존 중복된 dangling 이미지 정리
docker image prune -af
echo.

echo [3] 백엔드 이미지 새로 빌드 (1.5 버전)
docker build -t honghhj66/privalert-backend:1.5 ./backend
echo.

echo [4] 프론트엔드 이미지 새로 빌드 (1.5 버전)
docker build -t honghhj66/privalert-frontend:1.5 ./frontend
echo.

echo [5] FastAPI 서버 이미지 새로 빌드 (1.5 버전)
docker build -t honghhj66/privalert-fastapi:1.5 ./fastapi-backend
echo.

echo [6] 완료 후 빌드된 이미지 목록 확인
docker images --format "table {{.Repository}}\t{{.Tag}}\t{{.ID}}\t{{.Size}}"
echo.

echo ========================================
echo 모든 작업이 완료되었습니다!
echo ========================================
pause

