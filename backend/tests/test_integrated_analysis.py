"""
통합 분석 API 테스트
"""

import requests
import json
import time

BASE_URL = "http://localhost:5000/api/v1"

def test_integrated_analysis():
    """통합 분석 API 테스트"""
    print("=== 통합 분석 API 테스트 ===\n")
    
    # 텍스트만 테스트
    print("1. 텍스트 분석 테스트")
    try:
        data = {
            "text": "하나님 비하하는 말입니다. 교회에 다닌다.",
            "blur_fingers": "true",
            "show_faces": "false"
        }
        
        response = requests.post(
            f"{BASE_URL}/analyze/analyze",
            data=data,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            print("✅ 성공")
            print(f"얼굴 탐지: {result['summary']['faces_detected']}개")
            print(f"손가락 탐지: {result['summary']['fingers_detected']}개")
            print(f"정형 데이터 탐지: {result['summary']['sensitive_text_found']}")
            print(f"요약: {result['summary']['message']}")
        else:
            print(f"❌ 실패 (상태 코드: {response.status_code})")
            print(f"오류: {response.text}")
    except Exception as e:
        print(f"❌ 요청 실패: {e}")
    
    print("-" * 50)

def test_face_detection():
    """얼굴 탐지 API 테스트"""
    print("=== 얼굴 탐지 API 테스트 ===\n")
    print("이미지 파일이 필요하므로 스킵합니다.")
    print("실제 사용 시에는 이미지를 업로드하면 얼굴이 탐지됩니다.")

def test_hand_detection():
    """손가락 탐지 API 테스트"""
    print("=== 손가락 탐지 API 테스트 ===\n")
    print("이미지 파일이 필요하므로 스킵합니다.")
    print("실제 사용 시에는 이미지를 업로드하면 손가락이 탐지됩니다.")

def test_ocr():
    """OCR API 테스트"""
    print("=== OCR API 테스트 ===\n")
    print("이미지 파일이 필요하므로 스킵합니다.")
    print("실제 사용 시에는 이미지를 업로드하면 텍스트가 추출됩니다.")

def test_structured_data_filter():
    """정형 데이터 필터링 API 테스트"""
    print("=== 정형 데이터 필터링 API 테스트 ===\n")
    
    test_cases = [
        "전화번호: 010-1234-5678, 이메일: test@example.com",
        "주민등록번호: 123456-1234567",
        "계좌번호: 123-456-789012",
        "IP주소: 192.168.1.1",
        "학교명: 서울대학교, 연세대",
        "일반 텍스트입니다"
    ]
    
    for text in test_cases:
        print(f"테스트: {text}")
        try:
            data = {"text": text}
            response = requests.post(
                f"{BASE_URL}/api/v1/filter/filter",
                json=data,
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                detected = result['data']['has_sensitive_content']
                print(f"  결과: {'민감' if detected else '안전'}")
                if detected:
                    print(f"  필터링된 텍스트: {result['data']['filtered_text']}")
            else:
                print(f"  ❌ 실패: {response.status_code}")
        except Exception as e:
            print(f"  ❌ 오류: {e}")
        print()

def test_error_cases():
    """에러 케이스 테스트"""
    print("=== 에러 케이스 테스트 ===\n")
    
    # 빈 요청
    print("1. 빈 요청 테스트")
    try:
        response = requests.post(f"{BASE_URL}/analyze/analyze", timeout=10)
        print(f"상태 코드: {response.status_code}")
    except Exception as e:
        print(f"오류: {e}")
    
    # 잘못된 JSON
    print("\n2. 잘못된 JSON 테스트")
    try:
        response = requests.post(
            f"{BASE_URL}/filter/filter",
            data="invalid json",
            headers={'Content-Type': 'application/json'},
            timeout=10
        )
        print(f"상태 코드: {response.status_code}")
    except Exception as e:
        print(f"오류: {e}")

def main():
    """메인 함수"""
    print("통합 분석 API 테스트를 시작합니다...")
    print("Flask 서버가 http://localhost:5000에서 실행 중인지 확인하세요.\n")
    
    # 서버 연결 확인
    try:
        response = requests.get("http://localhost:5000/health", timeout=5)
        if response.status_code == 200:
            print("✅ 서버 연결 확인됨\n")
        else:
            print("❌ 서버 연결 실패")
            return
    except Exception:
        print("❌ 서버에 연결할 수 없습니다. Flask 서버가 실행 중인지 확인하세요.")
        return
    
    # 테스트 실행
    test_integrated_analysis()
    test_face_detection()
    test_hand_detection()
    test_ocr()
    test_structured_data_filter()
    test_error_cases()
    
    print("\n=== 테스트 완료 ===")

if __name__ == "__main__":
    main()
