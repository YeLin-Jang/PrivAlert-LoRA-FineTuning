@echo off
chcp 65001 >nul
echo ========================================
echo 전체 정적 분석 실행
echo ========================================
echo.

cd /d %~dp0

echo [1/3] Backend 정적 분석 시작...
echo ========================================
cd backend
call run_static_analysis.bat
cd ..
echo.

echo [2/3] Frontend 정적 분석 시작...
echo ========================================
cd frontend
call run_static_analysis.bat
cd ..
echo.

echo [3/3] FastAPI Backend 정적 분석 시작...
echo ========================================
cd fastapi-backend
call run_static_analysis.bat
cd ..
echo.

echo ========================================
echo 모든 정적 분석 완료!
echo ========================================
pause

