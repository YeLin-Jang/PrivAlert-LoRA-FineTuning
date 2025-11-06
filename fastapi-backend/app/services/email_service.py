"""
이메일 전송 서비스
보안: SMTP 설정은 환경 변수로 관리
"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

class EmailService:
    """이메일 전송 서비스 클래스"""
    
    @staticmethod
    async def send_verification_code(email: str, code: str) -> bool:
        """
        인증번호 이메일 전송
        보안: 로그에 인증번호나 이메일 내용을 기록하지 않음
        
        Args:
            email: 수신자 이메일 주소
            code: 인증번호 (6자리)
        
        Returns:
            bool: 전송 성공 여부
        """
        try:
            # 이메일 메시지 생성
            message = MIMEMultipart("alternative")
            message["Subject"] = "PrivAlert 회원가입 인증번호"
            message["From"] = settings.SMTP_FROM
            message["To"] = email
            
            # 이메일 본문 (HTML 형식)
            html_body = f"""
            <html>
              <body>
                <h2>안녕하세요, PrivAlert입니다.</h2>
                <p>회원가입을 위한 인증번호는 다음과 같습니다:</p>
                <h1 style="color: #4CAF50; font-size: 32px;">{code}</h1>
                <p>이 인증번호는 5분간 유효합니다.</p>
                <p>만약 본인이 요청하지 않았다면 이 이메일을 무시하세요.</p>
                <hr>
                <p style="color: #666; font-size: 12px;">이 메일은 자동으로 발송된 메일입니다.</p>
              </body>
            </html>
            """
            
            # 텍스트 형식 본문 (HTML을 지원하지 않는 클라이언트용)
            text_body = f"""
            안녕하세요, PrivAlert입니다.
            
            회원가입을 위한 인증번호는 다음과 같습니다:
            
            {code}
            
            이 인증번호는 5분간 유효합니다.
            만약 본인이 요청하지 않았다면 이 이메일을 무시하세요.
            """
            
            # 메시지 본문 추가
            text_part = MIMEText(text_body, "plain", "utf-8")
            html_part = MIMEText(html_body, "html", "utf-8")
            
            message.attach(text_part)
            message.attach(html_part)
            
            # SMTP 서버 연결 및 이메일 전송
            with smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT) as server:
                server.starttls()  # TLS 암호화 활성화
                server.login(settings.SMTP_EMAIL, settings.SMTP_PASSWORD)
                server.send_message(message)
            
            # 보안: 로그에 인증번호는 기록하지 않음 (이메일 주소만 기록)
            logger.info(f"인증번호 이메일 전송 성공: {email}")
            return True
            
        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"SMTP 인증 실패: {e}")
            return False
        except smtplib.SMTPException as e:
            logger.error(f"SMTP 오류 발생: {e}")
            return False
        except Exception as e:
            # 보안: 상세한 오류 메시지는 내부 로그에만 기록
            logger.error(f"이메일 전송 실패: {str(e)}")
            return False



