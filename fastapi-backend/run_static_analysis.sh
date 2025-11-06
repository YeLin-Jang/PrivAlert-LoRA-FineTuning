#!/bin/bash
# FastAPI Backend 정적 분석 실행 스크립트 (Linux/Mac)

cd "$(dirname "$0")"

# 가상 환경 활성화 (선택사항)
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
    echo "가상 환경 활성화됨: venv"
elif [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
    echo "가상 환경 활성화됨: .venv"
else
    echo "가상 환경이 없습니다. 시스템 Python을 사용합니다."
    echo "가상 환경을 생성하려면: python -m venv venv"
fi

# 정적 분석 도구 설치 확인 및 설치
echo "========================================"
echo "정적 분석 도구 확인 중..."
echo "========================================"
python -m pip install --upgrade pip
python -c "import flake8" 2>/dev/null || python -m pip install flake8==7.0.0
python -c "import bandit" 2>/dev/null || python -m pip install "bandit[toml]==1.7.8"
python -c "import safety" 2>/dev/null || python -m pip install --upgrade "safety>=2.3.5"

echo ""
echo "========================================"
echo "Flake8 코드 품질 검사"
echo "========================================"
python -m flake8 . --config=.flake8 --format=default --statistics --count

echo ""
echo "========================================"
echo "Bandit 보안 스캔"
echo "========================================"
python -m bandit -r . -f screen --exclude ./venv,./.venv,./__pycache__,./.pytest_cache -s B104

echo ""
echo "========================================"
echo "Safety 의존성 취약점 검사"
echo "========================================"
export PYTHONIOENCODING=utf-8
# extras 구문이 포함된 requirements.txt는 Safety가 파싱하지 못하므로
# extras를 제거한 requirements-safety.txt 사용
# pyproject.toml 자동 감지를 방지하기 위해 임시로 이름 변경
if [ -f "pyproject.toml" ]; then
    mv pyproject.toml pyproject.toml.bak
fi
if [ -f "requirements-safety.txt" ]; then
    echo "requirements-safety.txt 파일 사용 중..."
    python -X utf8 -m safety scan --file requirements-safety.txt --full-report --continue-on-error --no-api
else
    echo "requirements-safety.txt가 없습니다. requirements.txt를 사용합니다 (extras 구문으로 인해 오류 발생 가능)"
    python -X utf8 -m safety scan --file requirements.txt --full-report --continue-on-error --no-api || echo "Safety 스캔 중 오류 발생 (requirements.txt의 extras 구문 때문일 수 있음)"
fi
# pyproject.toml 복원
if [ -f "pyproject.toml.bak" ]; then
    mv pyproject.toml.bak pyproject.toml
fi

echo ""
echo "========================================"
echo "정적 분석 완료"
echo "========================================"

