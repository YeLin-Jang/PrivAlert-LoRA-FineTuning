"""SMTP 및 프롬프팅 설정 확인 스크립트"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# 프로젝트 루트의 .env 파일 로드
root_dir = Path(__file__).parent.parent
env_path = root_dir / '.env'
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
    print(f"[OK] .env 파일 로드 완료: {env_path}")
else:
    print(f"[WARNING] .env 파일을 찾을 수 없습니다: {env_path}")

print("\n=== SMTP 설정 확인 ===")
smtp_server = os.getenv("SMTP_SERVER", "NOT SET")
smtp_port = os.getenv("SMTP_PORT", "NOT SET")
smtp_email = os.getenv("SMTP_EMAIL", "NOT SET")
smtp_password = os.getenv("SMTP_PASSWORD", "NOT SET")
smtp_from = os.getenv("SMTP_FROM", "NOT SET")

print(f"SMTP_SERVER: {smtp_server}")
print(f"SMTP_PORT: {smtp_port}")
print(f"SMTP_EMAIL: {smtp_email[:20] + '...' if smtp_email != 'NOT SET' and len(smtp_email) > 20 else smtp_email}")
print(f"SMTP_PASSWORD: {'*** (설정됨)' if smtp_password != 'NOT SET' else 'NOT SET'}")
print(f"SMTP_FROM: {smtp_from}")

if smtp_server != "NOT SET" and smtp_email != "NOT SET" and smtp_password != "NOT SET":
    print("\n[OK] SMTP 설정이 완료되었습니다!")
else:
    print("\n[WARNING] SMTP 설정이 완료되지 않았습니다. .env 파일에 다음 변수를 추가하세요:")
    print("  SMTP_SERVER=smtp.gmail.com")
    print("  SMTP_PORT=587")
    print("  SMTP_EMAIL=your-email@gmail.com")
    print("  SMTP_PASSWORD=your-app-password")
    print("  SMTP_FROM=noreply@privalert.com (선택사항)")

print("\n=== 프롬프팅 설정 확인 ===")
sys.path.insert(0, str(Path(__file__).parent))
try:
    from app.services.llm_service import LLMService
    service = LLMService()
    api_key = service.api_key
    client = service.client
    model = service.model
    
    print(f"ANTHROPIC_API_KEY: {'*** (설정됨)' if api_key else 'NOT SET'}")
    print(f"Claude 클라이언트 초기화: {'YES' if client else 'NO'}")
    print(f"모델: {model}")
    
    if api_key and client:
        print("\n[OK] 프롬프팅 설정이 완료되었습니다!")
    elif api_key:
        print("\n[WARNING] API 키는 설정되었지만 클라이언트 초기화 실패")
        print("  anthropic 패키지 설치 확인: pip install anthropic")
    else:
        print("\n[WARNING] ANTHROPIC_API_KEY가 설정되지 않았습니다.")
        print("  프롬프팅은 폴백 모드로 작동합니다.")
        print("  .env 파일에 ANTHROPIC_API_KEY를 추가하세요.")
except Exception as e:
    print(f"\n[ERROR] 프롬프팅 서비스 확인 중 오류: {e}")

print("\n=== 이메일 전송 테스트 ===")
try:
    from app.services.email_service import EmailService, SMTP_EMAIL, SMTP_PASSWORD
    if SMTP_EMAIL and SMTP_PASSWORD:
        print("[OK] EmailService가 정상적으로 로드되었습니다.")
        print("  이메일 전송 기능 사용 가능")
    else:
        print("[WARNING] SMTP 설정이 없어 이메일 전송 기능을 사용할 수 없습니다.")
except Exception as e:
    print(f"[ERROR] EmailService 로드 실패: {e}")

print("\n=== 설정 요약 ===")
smtp_ok = smtp_server != "NOT SET" and smtp_email != "NOT SET" and smtp_password != "NOT SET"
prompting_ok = api_key and client if 'api_key' in locals() and 'client' in locals() else False

print(f"SMTP 설정: {'✅ 완료' if smtp_ok else '❌ 미완료'}")
print(f"프롬프팅 설정: {'✅ 완료' if prompting_ok else '⚠️  폴백 모드' if 'api_key' in locals() and not api_key else '❌ 미완료'}")

if smtp_ok and prompting_ok:
    print("\n[SUCCESS] 모든 설정이 완료되었습니다!")
elif smtp_ok:
    print("\n[INFO] SMTP 설정은 완료되었지만 프롬프팅은 폴백 모드로 작동합니다.")
elif prompting_ok:
    print("\n[INFO] 프롬프팅 설정은 완료되었지만 SMTP 설정이 필요합니다.")
else:
    print("\n[INFO] 일부 설정이 필요합니다. 위의 경고를 참고하세요.")

