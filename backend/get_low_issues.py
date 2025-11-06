#!/usr/bin/env python3
"""Bandit Low 이슈만 추출하는 스크립트"""
import json
import subprocess  # nosec B404 - 정적 분석 도구 자체이므로 subprocess 사용 필요
import sys
from collections import defaultdict

# Bandit JSON 리포트 생성
# 보안: 신뢰할 수 있는 시스템 명령어만 실행 (사용자 입력 없음)
result = subprocess.run(  # nosec B603 - 신뢰할 수 있는 시스템 명령어만 실행
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
    
    # Low 이슈만 필터링
    low_issues = []
    for result_item in report.get('results', []):
        if result_item.get('issue_severity') == 'LOW':
            low_issues.append(result_item)
    
    # 테스트 ID별로 그룹화
    issues_by_test = defaultdict(list)
    for issue in low_issues:
        test_id = issue.get('test_id', 'UNKNOWN')
        issues_by_test[test_id].append(issue)
    
    # 결과 출력
    print(f"\n{'='*80}")
    print(f"Low Severity Issues: {len(low_issues)} (Grouped by Test ID)")
    print(f"{'='*80}\n")
    
    for test_id, issues in sorted(issues_by_test.items()):
        print(f"\n[{test_id}] {issues[0].get('test_name', 'Unknown')} - {len(issues)}개")
        print(f"    설명: {issues[0].get('issue_text', '')[:100]}...")
        print(f"    자세한 정보: {issues[0].get('more_info', '')}")
        print(f"    발생 위치:")
        for i, issue in enumerate(issues[:5], 1):  # 최대 5개만 표시
            print(f"      {i}. {issue.get('filename')}:{issue.get('line_number')}")
            print(f"         코드: {issue.get('code', '').strip()[:80]}...")
        if len(issues) > 5:
            print(f"      ... 외 {len(issues) - 5}개 더")
    
    print(f"\n{'='*80}")
    print(f"총 Low 이슈: {len(low_issues)}개")
    print(f"테스트 ID 종류: {len(issues_by_test)}개")
    print(f"{'='*80}\n")
    
except json.JSONDecodeError:
    print("JSON 파싱 실패. Bandit 출력:")
    print(result.stdout)
    print("\nStderr:")
    print(result.stderr)



