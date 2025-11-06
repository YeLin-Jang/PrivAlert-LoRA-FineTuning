@echo off
REM SQLAlchemy 호환성 문제 해결 스크립트

echo ====================================
echo SQLAlchemy 재설치 중...
echo ====================================

REM 기존 SQLAlchemy 제거
echo [1/3] 기존 SQLAlchemy 제거 중...
pip uninstall sqlalchemy -y

REM SQLAlchemy 재설치 (호환 버전)
echo [2/3] SQLAlchemy 재설치 중...
pip install sqlalchemy[asyncio]==2.0.35

REM aiosqlite 재설치
echo [3/3] aiosqlite 재설치 중...
pip install aiosqlite==0.20.0

echo.
echo ====================================
echo 설치 확인 중...
echo ====================================
python -c "from sqlalchemy.ext.asyncio import AsyncSession; print('✅ SQLAlchemy 설치 완료!')"

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ====================================
    echo ✅ 성공!
    echo ====================================
    echo 이제 서버를 실행할 수 있습니다:
    echo   python main.py
) else (
    echo.
    echo ====================================
    echo ❌ 실패
    echo ====================================
    echo Python 버전을 확인하세요:
    echo   python --version
    echo Python 3.10 이상이 필요합니다.
)

pause



