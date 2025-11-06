#!/bin/bash
# Python 정적 분석 도구 실행 스크립트
# Bandit, Safety, Flake8을 순차적으로 실행합니다.

set -e

echo "========================================"
echo "Python Static Analysis Pipeline"
echo "========================================"
echo ""

# 스크립트 디렉토리로 이동
cd "$(dirname "$0")"

# 가상환경 활성화 (있는 경우)
if [ -f "venv/bin/activate" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
elif [ -f ".venv/bin/activate" ]; then
    echo "Activating virtual environment..."
    source .venv/bin/activate
fi

# 패키지 설치 확인 및 설치
echo "Checking if static analysis tools are installed..."
# 각 도구별로 설치 확인 및 업그레이드
if ! python -m pip list | grep -qi "flake8"; then
    echo "Installing flake8..."
    python -m pip install flake8==7.0.0
fi

if ! python -m pip list | grep -qi "bandit"; then
    echo "Installing bandit..."
    python -m pip install 'bandit[toml]==1.7.8'
else
    python -m pip install --upgrade 'bandit[toml]>=1.7.8'
fi

if ! python -m pip list | grep -qi "safety"; then
    echo "Installing safety..."
    python -m pip install "safety>=2.3.5"
else
    # Safety 버전 호환성 문제 해결을 위해 항상 업그레이드
    echo "Upgrading safety to latest compatible version..."
    python -m pip install --upgrade "safety>=2.3.5"
fi

# 1. Flake8 - 코드 품질 검사
echo ""
echo "[1/3] Running Flake8 (Code Quality Check)..."
echo "========================================"
if python -m flake8 . --config=.flake8 --statistics --count; then
    echo "Flake8 check passed!"
else
    echo ""
    echo "WARNING: Flake8 found code quality issues."
fi
echo ""

# 2. Bandit - 보안 취약점 스캔
echo ""
echo "[2/3] Running Bandit (Security Scan)..."
echo "========================================"
# pyproject.toml을 자동으로 인식 (인코딩 문제 방지를 위해 .bandit 파일 삭제됨)
# venv 디렉토리 명시적으로 제외
# B104 (hardcoded_bind_all_interfaces) skip - 개발 환경에서 0.0.0.0 사용 허용
if python -m bandit -r . -f screen --exclude ./venv,./.venv,./__pycache__,./.pytest_cache -s B104; then
    echo "Bandit check passed!"
else
    echo ""
    echo "WARNING: Bandit found security issues."
fi
echo ""

# 3. Safety - 의존성 취약점 검사
echo ""
echo "[3/3] Running Safety (Dependency Vulnerability Check)..."
echo "========================================"
# Safety의 새로운 scan 명령 사용 (check는 deprecated)
# UTF-8 인코딩 강제 설정 (cp949 오류 방지)
# 비대화형 모드로 실행 (이미 로그인된 경우 자동으로 인증 사용)
# requirements.txt만 스캔 (pyproject.toml 자동 감지 방지)
export PYTHONIOENCODING=utf-8
# Safety가 pyproject.toml을 읽지 않도록 requirements.txt만 명시적으로 지정
if python -X utf8 -m safety scan --file requirements.txt --full-report --continue-on-error; then
    echo "Safety check passed!"
else
    echo ""
    echo "WARNING: Safety found dependency vulnerabilities."
fi
echo ""

echo ""
echo "========================================"
echo "Static Analysis Complete"
echo "========================================"
echo ""

