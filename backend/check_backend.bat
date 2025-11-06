@echo off
cd /d %~dp0
if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
) else if exist .venv\Scripts\activate.bat (
    call .venv\Scripts\activate.bat
)
echo ========================================
echo Bandit Security Scan - Backend 전체
echo ========================================
echo.
python -m bandit -r app -f screen --exclude ./venv,./.venv,./__pycache__,./.pytest_cache -s B104
echo.
echo ========================================
pause

