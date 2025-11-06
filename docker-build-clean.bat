@echo off
chcp 65001 >nul
echo ========================================
echo Docker 이미지 완전 새로 빌드 (캐시 삭제)
echo ========================================
echo.
echo 경고: 이 스크립트는 모든 캐시를 삭제하고 처음부터 빌드합니다.
echo 빌드 시간이 매우 오래 걸립니다 (10-30분 이상).
echo.
pause

echo [1] 사용하지 않는 이미지/컨테이너/네트워크/캐시 전부 정리
docker system prune -af
echo.

echo [2] 기존 중복된 dangling 이미지 정리
docker image prune -af
echo.

echo [3] 백엔드 이미지 새로 빌드 (캐시 없이)
docker build --no-cache -t honghhj66/privalert-backend:1.5 ./backend
echo.

echo [4] 프론트엔드 이미지 새로 빌드 (캐시 없이)
docker build --no-cache -t honghhj66/privalert-frontend:1.5 ./frontend
echo.

echo [5] FastAPI 서버 이미지 새로 빌드 (캐시 없이)
docker build --no-cache -t honghhj66/privalert-fastapi:1.5 ./fastapi-backend
echo.

echo [6] 빌드된 이미지 목록 확인
docker images --format "table {{.Repository}}\t{{.Tag}}\t{{.ID}}\t{{.Size}}" | findstr "privalert"
echo.

echo ========================================
echo 완전 새로 빌드 완료!
echo ========================================
pause

