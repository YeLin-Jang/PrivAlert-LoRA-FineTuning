@echo off
chcp 65001 >nul
REM Frontend 정적 분석 실행 스크립트 (Windows)
cd /d %~dp0

echo ========================================
echo Frontend 정적 분석 시작
echo ========================================
echo.

echo [1/3] TypeScript 타입 검사...
call npx tsc -b --noEmit
if %errorlevel% neq 0 (
    echo TypeScript 타입 검사에서 오류 발견
    echo.
) else (
    echo TypeScript 타입 검사 통과!
    echo.
)

echo [2/3] ESLint 코드 품질 검사...
call npm run lint
if %errorlevel% neq 0 (
    echo ESLint 검사에서 경고 발견
    echo.
) else (
    echo ESLint 검사 통과!
    echo.
)

echo [3/3] npm audit 보안 검사...
call npm audit
if %errorlevel% neq 0 (
    echo npm audit에서 취약점 발견
    echo.
) else (
    echo npm audit 통과!
    echo.
)

echo.
echo ========================================
echo Frontend 정적 분석 완료
echo ========================================
pause

