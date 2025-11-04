"""
테스트 실행 스크립트
"""

import subprocess
import sys

def main():
    """모든 테스트 실행"""
    print("=" * 60)
    print("PrivAlert API 테스트 실행")
    print("=" * 60)
    
    # 통합 분석 테스트
    print("통합 분석 테스트 실행...")
    subprocess.run([sys.executable, "test_integrated_analysis.py"])
    
    print("\n" + "=" * 60)
    
    # 종교 필터링 테스트
    print("종교 필터링 테스트 실행...")
    subprocess.run([sys.executable, "test_religious_filter.py"])
    
    print("\n" + "=" * 60)
    print("모든 테스트 완료")
    print("=" * 60)

if __name__ == "__main__":
    main()
