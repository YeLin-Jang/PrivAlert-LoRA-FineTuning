"""
SECRET_KEY 생성 스크립트

안전한 랜덤 키 생성 (secrets 모듈 사용)
"""
import secrets

def generate_secret_key():
    """32바이트 랜덤 키 생성 (64자 hex 문자열)"""
    return secrets.token_hex(32)

if __name__ == "__main__":
    key = generate_secret_key()
    print("=" * 60)
    print("생성된 SECRET_KEY:")
    print("=" * 60)
    print(key)
    print("=" * 60)
    print("\n.env 파일에 추가하세요:")
    print(f"FLASK_SECRET_KEY={key}")
    print("=" * 60)

