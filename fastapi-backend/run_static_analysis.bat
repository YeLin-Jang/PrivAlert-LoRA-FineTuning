@echo off
REM FastAPI Backend 정적 분석 실행 스크립트 (Windows)
cd /d %~dp0

REM 가상 환경 활성화 (선택사항)
if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
    echo 가상 환경 활성화됨: venv
) else if exist .venv\Scripts\activate.bat (
    call .venv\Scripts\activate.bat
    echo 가상 환경 활성화됨: .venv
) else (
    echo 가상 환경이 없습니다. 시스템 Python을 사용합니다.
    echo 가상 환경을 생성하려면: python -m venv venv
)

REM 정적 분석 도구 설치 확인 및 설치
echo ========================================
echo 정적 분석 도구 확인 중...
echo ========================================
python -m pip install --upgrade pip
python -c "import flake8" 2>nul || python -m pip install flake8==7.0.0
python -c "import bandit" 2>nul || python -m pip install "bandit[toml]==1.7.8"
python -c "import safety" 2>nul || python -m pip install --upgrade "safety>=2.3.5"

echo.
echo ========================================
echo Flake8 코드 품질 검사
echo ========================================
python -m flake8 . --config=.flake8 --format=default --statistics --count

echo.
echo ========================================
echo Bandit 보안 스캔
echo ========================================
python -m bandit -r . -f screen --exclude ./venv,./.venv,./__pycache__,./.pytest_cache -s B104

echo.
echo ========================================
echo Safety 의존성 취약점 검사
echo ========================================
set PYTHONIOENCODING=utf-8
REM extras 구문이 포함된 requirements.txt는 Safety가 파싱하지 못하므로
REM extras를 제거한 requirements-safety.txt 사용
REM Safety가 자동 감지하지 못하도록 파일 임시 이름 변경
REM pyproject.toml 자동 감지를 방지하기 위해 임시로 이름 변경
if exist pyproject.toml ren pyproject.toml pyproject.toml.bak
REM requirements.txt도 임시로 이름 변경하여 Safety가 자동 감지하지 못하도록 함
if exist requirements.txt ren requirements.txt requirements.txt.bak
REM requirements-safety.txt 사용
echo Using requirements-safety.txt...
cd /d %~dp0
REM Safety가 파일을 읽을 수 있도록 현재 디렉토리에서 실행
REM --no-api 옵션 제거 (API 사용 시 파일 읽기가 더 잘 작동할 수 있음)
python -X utf8 -m safety scan --file requirements-safety.txt --full-report --continue-on-error
REM 파일 복원 (오류 발생 시에도 복원)
if exist requirements.txt.bak ren requirements.txt.bak requirements.txt
if exist pyproject.toml.bak ren pyproject.toml.bak pyproject.toml

echo.
echo ========================================
echo 정적 분석 완료
echo ========================================
pause

