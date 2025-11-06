#!/usr/bin/env python3
"""Bandit Medium 이슈만 추출하는 스크립트"""
import json
import subprocess
import sys

# Bandit JSON 리포트 생성
result = subprocess.run(
    [
        sys.executable, '-m', 'bandit',
        '-r', 'app',
        '-f', 'json',
        '--exclude', './venv,./.venv,./__pycache__,./.pytest_cache',
        '-s', 'B104'
    ],
    capture_output=True,
    text=True,
    cwd='.'
)

# JSON 파싱
try:
    report = json.loads(result.stdout)
    
    # Medium 이슈만 필터링
    medium_issues = []
    for result_item in report.get('results', []):
        if result_item.get('issue_severity') == 'MEDIUM':
            medium_issues.append(result_item)
    
    # 결과 출력
    print(f"\n{'='*80}")
    print(f"Medium Severity Issues: {len(medium_issues)}")
    print(f"{'='*80}\n")
    
    for i, issue in enumerate(medium_issues, 1):
        print(f"[{i}] {issue.get('test_id')}: {issue.get('test_name')}")
        print(f"    Severity: {issue.get('issue_severity')}")
        print(f"    Confidence: {issue.get('issue_confidence')}")
        print(f"    Location: {issue.get('filename')}:{issue.get('line_number')}")
        print(f"    Code: {issue.get('code', '')[:100]}...")
        print(f"    More Info: {issue.get('more_info', '')}")
        print()
    
except json.JSONDecodeError:
    print("JSON 파싱 실패. Bandit 출력:")
    print(result.stdout)
    print("\nStderr:")
    print(result.stderr)



