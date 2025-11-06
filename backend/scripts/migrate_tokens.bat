@echo off
REM 토큰 테이블 마이그레이션 스크립트 (Windows)
REM 관리자 계정만 보존하고 나머지 데이터 삭제 후 스키마 변경

echo ============================================================
echo 토큰 테이블 마이그레이션
echo ============================================================
echo.

REM 환경 변수 로드
if exist ..\.env (
    echo .env 파일 로드 중...
    for /f "usebackq tokens=1,* delims==" %%a in ("..\.env") do (
        set "%%a"
    )
)

REM Python 경로 확인
python --version >nul 2>&1
if errorlevel 1 (
    echo [오류] Python이 설치되어 있지 않습니다.
    pause
    exit /b 1
)

REM 마이그레이션 실행
cd /d %~dp0
python migrate_tokens.py

if errorlevel 1 (
    echo.
    echo [오류] 마이그레이션 실패
    pause
    exit /b 1
) else (
    echo.
    echo [성공] 마이그레이션 완료
    pause
    exit /b 0
)

