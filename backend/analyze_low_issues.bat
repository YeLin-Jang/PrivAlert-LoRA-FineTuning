@echo off
cd /d %~dp0
if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
) else if exist .venv\Scripts\activate.bat (
    call .venv\Scripts\activate.bat
)
echo ========================================
echo Bandit Low Issues Analysis
echo ========================================
echo.
echo JSON 리포트 생성 중...
python -m bandit -r app -f json --exclude ./venv,./.venv,./__pycache__,./.pytest_cache -s B104 -o low-issues-report.json
echo.
echo Low 이슈 요약:
python -c "import json; data=json.load(open('low-issues-report.json', 'r', encoding='utf-8')); low=[r for r in data.get('results',[]) if r.get('issue_severity')=='LOW']; print(f'총 Low 이슈: {len(low)}개'); from collections import Counter; ids=Counter([r.get('test_id') for r in low]); print('\\n테스트 ID별 분류:'); [print(f'  {tid}: {count}개') for tid,count in ids.most_common()]"
echo.
echo 상세 리포트는 low-issues-report.json 파일을 확인하세요.
echo.
pause

