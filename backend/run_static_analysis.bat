@echo off
REM Python 정적 분석 도구 실행 스크립트
REM Bandit, Safety, Flake8을 순차적으로 실행합니다.

echo ========================================
echo Python Static Analysis Pipeline
echo ========================================
echo.

cd /d %~dp0

REM 가상환경 활성화 (있는 경우)
if exist venv\Scripts\activate.bat (
    echo Activating virtual environment...
    call venv\Scripts\activate.bat
) else if exist .venv\Scripts\activate.bat (
    echo Activating virtual environment...
    call .venv\Scripts\activate.bat
) else (
    echo WARNING: Virtual environment not found. Using system Python.
    echo Make sure flake8, bandit, and safety are installed.
    echo.
)

REM 패키지 설치 확인 및 설치
echo Checking if static analysis tools are installed...
python -m pip list | findstr /i "flake8" >nul
if %ERRORLEVEL% NEQ 0 (
    echo Installing flake8...
    python -m pip install --upgrade pip
    python -m pip install flake8==7.0.0
    echo.
)

python -m pip list | findstr /i "bandit" >nul
if %ERRORLEVEL% NEQ 0 (
    echo Installing bandit...
    python -m pip install "bandit[toml]==1.7.8"
    echo.
)

python -m pip list | findstr /i "safety" >nul
if %ERRORLEVEL% NEQ 0 (
    echo Installing safety...
    python -m pip install "safety>=2.3.5"
    echo.
) else (
    REM Safety가 설치되어 있지만 오래된 버전일 수 있으므로 업그레이드 시도
    python -m pip install --upgrade "safety>=2.3.5"
)

REM 1. Flake8 - 코드 품질 검사
echo.
echo [1/3] Running Flake8 (Code Quality Check)...
echo ========================================
python -m flake8 . --config=.flake8 --statistics --count
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo WARNING: Flake8 found code quality issues.
    echo.
) else (
    echo Flake8 check passed!
    echo.
)

REM 2. Bandit - 보안 취약점 스캔
echo.
echo [2/3] Running Bandit (Security Scan)...
echo ========================================
REM pyproject.toml을 자동으로 인식 (인코딩 문제 방지를 위해 .bandit 파일 삭제됨)
REM venv 디렉토리 명시적으로 제외
REM B104 (hardcoded_bind_all_interfaces) skip - 개발 환경에서 0.0.0.0 사용 허용
python -m bandit -r . -f screen --exclude ./venv,./.venv,./__pycache__,./.pytest_cache -s B104
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo WARNING: Bandit found security issues.
    echo.
) else (
    echo Bandit check passed!
    echo.
)

REM 3. Safety - 의존성 취약점 검사
echo.
echo [3/3] Running Safety (Dependency Vulnerability Check)...
echo ========================================
REM Safety의 새로운 scan 명령 사용 (check는 deprecated)
REM UTF-8 인코딩 강제 설정 (cp949 오류 방지)
REM 비대화형 모드로 실행 (이미 로그인된 경우 자동으로 인증 사용)
REM requirements.txt만 스캔 (pyproject.toml 자동 감지 방지)
set PYTHONIOENCODING=utf-8
REM Safety가 pyproject.toml을 읽지 않도록 requirements.txt만 명시적으로 지정
python -X utf8 -m safety scan --file requirements.txt --full-report --continue-on-error
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo WARNING: Safety found dependency vulnerabilities.
    echo.
) else (
    echo Safety check passed!
    echo.
)

echo.
echo ========================================
echo Static Analysis Complete
echo ========================================
echo.
pause

