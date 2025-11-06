@echo off
cd /d %~dp0
set PYTHONIOENCODING=utf-8
echo Testing Safety with requirements-safety.txt...
echo.
echo File contents check:
type requirements-safety.txt | findstr /v "^#" | findstr /v "^$"
echo.
REM Safety가 자동 감지하지 못하도록 파일 임시 이름 변경
if exist pyproject.toml ren pyproject.toml pyproject.toml.bak
if exist requirements.txt ren requirements.txt requirements.txt.bak
echo.
echo Running Safety scan...
REM --no-api 옵션 제거하고 API 사용 시도
python -X utf8 -m safety scan --file requirements-safety.txt --full-report --continue-on-error
echo.
REM 파일 복원
if exist requirements.txt.bak ren requirements.txt.bak requirements.txt
if exist pyproject.toml.bak ren pyproject.toml.bak pyproject.toml
pause

