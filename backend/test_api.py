"""
종교별 민감 단어 필터링 API 테스트 스크립트

이 스크립트는 Flask 서버가 실행 중일 때 API 엔드포인트를 테스트합니다.
"""

import requests
import json
import time

# API 기본 URL
BASE_URL = "http://localhost:5000/api/v1/filter"

def test_filter_api():
    """필터링 API 테스트"""
    print("=== 종교별 민감 단어 필터링 API 테스트 ===\n")
    
    # 테스트 케이스들
    test_cases = [
        {
            "name": "기독교 관련 텍스트",
            "data": {
                "text": "예수 그리스도는 하나님의 아들입니다. 십자가에서 죽으시고 부활하셨습니다.",
                "mask_char": "*"
            }
        },
        {
            "name": "이슬람 관련 텍스트",
            "data": {
                "text": "무함마드는 알라의 예언자입니다. 꾸란은 성스러운 경전입니다.",
                "mask_char": "#"
            }
        },
        {
            "name": "불교 관련 텍스트",
            "data": {
                "text": "부처님은 석가모니입니다. 나무아미타불을 염불하세요.",
                "mask_char": "X"
            }
        },
        {
            "name": "우회 패턴 테스트",
            "data": {
                "text": "예 수 그 리 스 도는 하 나 님의 아들입니다",
                "mask_char": "*"
            }
        },
        {
            "name": "특수문자 우회 패턴",
            "data": {
                "text": "예@수 그#리스$도는 하%나님의 아들입니다",
                "mask_char": "*"
            }
        },
        {
            "name": "민감 단어가 없는 텍스트",
            "data": {
                "text": "안녕하세요. 오늘 날씨가 정말 좋네요. 즐거운 하루 되세요!",
                "mask_char": "*"
            }
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"테스트 {i}: {test_case['name']}")
        print(f"원본 텍스트: {test_case['data']['text']}")
        
        try:
            response = requests.post(
                f"{BASE_URL}/filter",
                json=test_case['data'],
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ 성공")
                print(f"필터링된 텍스트: {result['filtered_text']}")
                print(f"민감 정보 감지: {result['has_sensitive_content']}")
                print(f"전체 통계: {result['overall_statistics']}")
                
                if result['filter_results']:
                    print("필터별 결과:")
                    for filter_name, filter_result in result['filter_results'].items():
                        if filter_result.get('success'):
                            detected_words = filter_result.get('detected_words', [])
                            print(f"  {filter_name}: {len(detected_words)}개 감지")
                            if detected_words:
                                for word_info in detected_words[:3]:  # 처음 3개만 표시
                                    print(f"    - '{word_info['word']}' ({word_info.get('religion', 'N/A')})")
            else:
                print(f"❌ 실패 (상태 코드: {response.status_code})")
                print(f"오류: {response.text}")
        
        except requests.exceptions.RequestException as e:
            print(f"❌ 요청 실패: {e}")
        
        print("-" * 50)

def test_ocr_with_filter():
    """OCR과 종교 필터링 통합 테스트"""
    print("\n=== OCR과 종교 필터링 통합 테스트 ===\n")
    
    # OCR 테스트 (실제 이미지 파일이 필요하므로 스킵)
    print("OCR 테스트는 실제 이미지 파일이 필요하므로 스킵합니다.")
    print("실제 사용 시에는 이미지를 업로드하면 자동으로 종교 필터링이 적용됩니다.")

def test_error_cases():
    """에러 케이스 테스트"""
    print("\n=== 에러 케이스 테스트 ===\n")
    
    # 1. 빈 텍스트
    print("1. 빈 텍스트 테스트")
    try:
        response = requests.post(f"{BASE_URL}/filter", json={"text": ""}, timeout=10)
        print(f"상태 코드: {response.status_code}")
        if response.status_code != 200:
            result = response.json()
            print(f"오류 메시지: {result['error']}")
    except requests.exceptions.RequestException as e:
        print(f"❌ 요청 실패: {e}")
    
    # 2. 잘못된 JSON
    print("\n2. 잘못된 JSON 테스트")
    try:
        response = requests.post(f"{BASE_URL}/filter", data="invalid json", 
                               headers={'Content-Type': 'application/json'}, timeout=10)
        print(f"상태 코드: {response.status_code}")
        if response.status_code != 200:
            result = response.json()
            print(f"오류 메시지: {result['error']}")
    except requests.exceptions.RequestException as e:
        print(f"❌ 요청 실패: {e}")
    
    # 3. 사용 가능한 필터 목록 조회
    print("\n3. 사용 가능한 필터 목록 조회")
    try:
        response = requests.get(f"{BASE_URL}/filters", timeout=10)
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 성공: {result['filters']}")
        else:
            print(f"❌ 실패 (상태 코드: {response.status_code})")
    except requests.exceptions.RequestException as e:
        print(f"❌ 요청 실패: {e}")
    
    # 4. 통계 조회
    print("\n4. 통계 조회")
    try:
        response = requests.get(f"{BASE_URL}/statistics", timeout=10)
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 성공")
            for filter_name, stats in result['statistics'].items():
                print(f"  {filter_name}: {stats}")
        else:
            print(f"❌ 실패 (상태 코드: {response.status_code})")
    except requests.exceptions.RequestException as e:
        print(f"❌ 요청 실패: {e}")

def main():
    """메인 함수"""
    print("종교별 민감 단어 필터링 API 테스트를 시작합니다...")
    print("Flask 서버가 http://localhost:5000에서 실행 중인지 확인하세요.\n")
    
    # 서버 연결 확인
    try:
        response = requests.get("http://localhost:5000/health", timeout=5)
        if response.status_code == 200:
            print("✅ 서버 연결 확인됨\n")
        else:
            print("❌ 서버 연결 실패")
            return
    except requests.exceptions.RequestException:
        print("❌ 서버에 연결할 수 없습니다. Flask 서버가 실행 중인지 확인하세요.")
        return
    
    # 테스트 실행
    test_filter_api()
    test_ocr_with_filter()
    test_error_cases()
    
    print("\n=== 테스트 완료 ===")

if __name__ == "__main__":
    main()
