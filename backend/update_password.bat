@echo off
cd /d %~dp0
echo 관리자 계정 비밀번호 업데이트 중...
echo.

REM 현재 활성화된 Python 사용 (conda 환경 포함)
python update_admin_password.py

pause

