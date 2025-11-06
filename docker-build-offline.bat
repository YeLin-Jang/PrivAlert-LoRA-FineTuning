@echo off
chcp 65001 >nul
echo ========================================
echo Docker 이미지 오프라인 빌드 (로컬 캐시만 사용)
echo ========================================
echo.
echo 네트워크 연결 없이 로컬에 있는 이미지만 사용합니다.
echo.

echo [1] 로컬에 있는 이미지 확인
docker images --format "table {{.Repository}}\t{{.Tag}}\t{{.ID}}\t{{.Size}}" | findstr "privalert"
echo.

echo [2] 기존 이미지로 태그 재생성 (필요시)
echo.
echo 백엔드 이미지가 없으면:
echo   docker tag honghhj66/privalert-backend:1.0 honghhj66/privalert-backend:1.5
echo.
echo 프론트엔드 이미지가 없으면:
echo   docker tag honghhj66/privalert-frontend:1.0 honghhj66/privalert-frontend:1.5
echo.
echo FastAPI 이미지가 없으면:
echo   docker tag honghhj66/privalert-fastapi:1.0 honghhj66/privalert-fastapi:1.5
echo.

echo [3] 현재 사용 가능한 이미지 목록
docker images --format "table {{.Repository}}\t{{.Tag}}\t{{.ID}}\t{{.Size}}" | findstr "privalert"
echo.

echo ========================================
echo 오프라인 모드 완료!
echo ========================================
echo.
echo 참고: 네트워크 문제 해결 방법:
echo   1. 인터넷 연결 확인
echo   2. Docker Desktop 재시작
echo   3. 방화벽/프록시 설정 확인
echo   4. DNS 설정 확인 (8.8.8.8 사용)
pause

