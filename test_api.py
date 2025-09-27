import requests
import json

# 백엔드 API 테스트
try:
    url = "http://localhost:5000/api/v1/analyze/analyze"
    data = {
        "text": "테스트 텍스트입니다",
        "blur_fingers": "true",
        "show_faces": "false"
    }
    
    print("API 테스트 시작...")
    print(f"URL: {url}")
    print(f"Data: {data}")
    
    response = requests.post(url, data=data)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
    
except Exception as e:
    print(f"오류 발생: {e}")
