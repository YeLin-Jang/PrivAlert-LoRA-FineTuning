@echo off
REM Frontend 정적 분석 실행 스크립트 (Windows)
cd /d %~dp0

echo ========================================
echo Frontend 정적 분석 시작
echo ========================================
echo.

echo [1/3] TypeScript 타입 검사...
call npm run type-check
if %errorlevel% neq 0 (
    echo TypeScript 타입 검사 실패
    pause
    exit /b 1
)

echo.
echo [2/3] ESLint 코드 품질 검사...
call npm run lint:warn
if %errorlevel% neq 0 (
    echo ESLint 검사에서 경고 발견 (자동 수정 시도: npm run lint:fix)
)

echo.
echo [3/3] npm audit 보안 검사...
call npm run audit
if %errorlevel% neq 0 (
    echo npm audit에서 취약점 발견 (자동 수정 시도: npm run audit:fix)
)

echo.
echo ========================================
echo Frontend 정적 분석 완료
echo ========================================
pause

