@echo off
chcp 65001 >nul
echo ========================================
echo Docker 이미지 빌드 스크립트 시작
echo ========================================
echo.

REM 캐시를 삭제하면 빌드가 매우 느려집니다
REM 필요시에만 수동으로 실행: docker system prune -af
REM echo [1] 사용하지 않는 이미지/컨테이너/네트워크/캐시 전부 정리
REM docker system prune -af
REM echo.

REM echo [2] 기존 중복된 dangling 이미지 정리
REM docker image prune -af
REM echo.

echo [3] 백엔드 이미지 빌드 (캐시 활용)
docker build -t honghhj66/privalert-backend:1.5 ./backend
echo.

echo [4] 프론트엔드 이미지 빌드 (캐시 활용)
docker build -t honghhj66/privalert-frontend:1.5 ./frontend
echo.

echo [5] FastAPI 서버 이미지 빌드 (캐시 활용)
docker build -t honghhj66/privalert-fastapi:1.5 ./fastapi-backend
echo.

echo [6] 빌드된 이미지 목록 확인
docker images --format "table {{.Repository}}\t{{.Tag}}\t{{.ID}}\t{{.Size}}" | findstr "privalert"
echo.

echo ========================================
echo 빌드 완료!
echo ========================================
echo.
echo 참고: 
echo   - 빠른 빌드: docker-build-fast.bat (캐시 활용, 권장)
echo   - 완전 새로 빌드: docker-build-clean.bat (캐시 삭제 후 빌드)
pause

