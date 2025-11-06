"""
이메일 전송 서비스 (SMTP)
보안: SMTP 설정은 환경 변수로 관리
"""
import smtplib
import os
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
from pathlib import Path
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# 환경 변수 로드
try:
    root_dir = Path(__file__).parent.parent.parent.parent  # backend/app/services/email_service.py -> 프로젝트 루트
    env_path = root_dir / '.env'
    if env_path.exists():
        load_dotenv(dotenv_path=env_path, override=False)
except Exception as e:
    logger.warning(f".env 파일 로드 중 오류 (무시됨): {e}")

# SMTP 설정 (환경 변수에서 로드)
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_EMAIL = os.getenv("SMTP_EMAIL", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM = os.getenv("SMTP_FROM", os.getenv("SMTP_EMAIL", "noreply@privalert.com") or "noreply@privalert.com")


class EmailService:
    """이메일 전송 서비스 클래스"""
    
    @staticmethod
    def send_verification_code(email: str, code: str) -> bool:
        """
        이메일 인증 코드 전송
        
        Args:
            email: 수신자 이메일 주소
            code: 6자리 인증 코드
        
        Returns:
            bool: 전송 성공 여부
        """
        if not SMTP_EMAIL or not SMTP_PASSWORD:
            logger.warning("SMTP 설정이 완료되지 않았습니다. SMTP_EMAIL과 SMTP_PASSWORD를 확인하세요.")
            return False
        
        try:
            # 이메일 메시지 생성
            message = MIMEMultipart("alternative")
            message["Subject"] = "PrivAlert 이메일 인증 코드"
            message["From"] = SMTP_FROM
            message["To"] = email
            
            # 이메일 본문 (HTML 형식)
            html_body = f"""
            <html>
              <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                  <h2 style="color: #1e3a8a;">안녕하세요, PrivAlert입니다.</h2>
                  <p>회원가입을 완료하기 위해 아래 인증 코드를 입력해주세요.</p>
                  <div style="text-align: center; margin: 30px 0;">
                    <div style="background-color: #f3f4f6; border: 2px solid #3b82f6; 
                                border-radius: 12px; padding: 20px; display: inline-block;">
                      <div style="font-size: 32px; font-weight: bold; color: #1e3a8a; 
                                  letter-spacing: 8px; font-family: 'Courier New', monospace;">
                        {code}
                      </div>
                    </div>
                  </div>
                  <p style="color: #666; font-size: 14px;">
                    이 코드는 10분 동안 유효합니다.<br>
                    만약 본인이 요청하지 않았다면 이 이메일을 무시하세요.
                  </p>
                  <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
                  <p style="color: #999; font-size: 12px; text-align: center;">
                    이 메일은 자동으로 발송된 메일입니다.
                  </p>
                </div>
              </body>
            </html>
            """
            
            # 텍스트 형식 본문
            text_body = f"""
안녕하세요, PrivAlert입니다.

회원가입을 완료하기 위해 아래 인증 코드를 입력해주세요.

인증 코드: {code}

이 코드는 10분 동안 유효합니다.
만약 본인이 요청하지 않았다면 이 이메일을 무시하세요.

---
이 메일은 자동으로 발송된 메일입니다.
            """
            
            # 메시지 본문 추가
            text_part = MIMEText(text_body, "plain", "utf-8")
            html_part = MIMEText(html_body, "html", "utf-8")
            
            message.attach(text_part)
            message.attach(html_part)
            
            # SMTP 서버 연결 및 이메일 전송
            with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
                server.starttls()
                server.login(SMTP_EMAIL, SMTP_PASSWORD)
                server.send_message(message)
            
            logger.info(f"이메일 인증 코드 전송 성공: {email}")
            return True
            
        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"SMTP 인증 실패: {e}")
            return False
        except smtplib.SMTPException as e:
            logger.error(f"SMTP 오류 발생: {e}")
            return False
        except Exception as e:
            logger.error(f"이메일 전송 실패: {str(e)}", exc_info=True)
            return False
    
    @staticmethod
    def send_verification_email(email: str, token: str, verification_url: Optional[str] = None) -> bool:
        """
        이메일 인증 메일 전송
        
        Args:
            email: 수신자 이메일 주소
            token: 인증 토큰
            verification_url: 인증 URL (없으면 자동 생성)
        
        Returns:
            bool: 전송 성공 여부
        """
        if not SMTP_EMAIL or not SMTP_PASSWORD:
            logger.warning("SMTP 설정이 완료되지 않았습니다. SMTP_EMAIL과 SMTP_PASSWORD를 확인하세요.")
            return False
        
        try:
            # 인증 URL 생성
            if not verification_url:
                from flask import request
                base_url = request.host_url.rstrip('/') if request else 'http://localhost:5000'
                verification_url = f"{base_url}/api/v1/auth/verify?token={token}"
            
            # 이메일 메시지 생성
            message = MIMEMultipart("alternative")
            message["Subject"] = "PrivAlert 이메일 인증"
            message["From"] = SMTP_FROM
            message["To"] = email
            
            # 이메일 본문 (HTML 형식)
            html_body = f"""
            <html>
              <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                  <h2 style="color: #1e3a8a;">안녕하세요, PrivAlert입니다.</h2>
                  <p>회원가입을 완료하기 위해 아래 링크를 클릭하여 이메일 인증을 완료해주세요.</p>
                  <div style="text-align: center; margin: 30px 0;">
                    <a href="{verification_url}" 
                       style="background-color: #3b82f6; color: white; padding: 12px 24px; 
                              text-decoration: none; border-radius: 8px; display: inline-block; 
                              font-weight: bold;">
                      이메일 인증하기
                    </a>
                  </div>
                  <p style="color: #666; font-size: 14px;">
                    또는 아래 링크를 복사하여 브라우저에 붙여넣으세요:<br>
                    <a href="{verification_url}" style="color: #3b82f6; word-break: break-all;">{verification_url}</a>
                  </p>
                  <p style="color: #666; font-size: 14px;">
                    이 링크는 24시간 동안 유효합니다.<br>
                    만약 본인이 요청하지 않았다면 이 이메일을 무시하세요.
                  </p>
                  <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
                  <p style="color: #999; font-size: 12px; text-align: center;">
                    이 메일은 자동으로 발송된 메일입니다.
                  </p>
                </div>
              </body>
            </html>
            """
            
            # 텍스트 형식 본문 (HTML을 지원하지 않는 클라이언트용)
            text_body = f"""
안녕하세요, PrivAlert입니다.

회원가입을 완료하기 위해 아래 링크를 클릭하여 이메일 인증을 완료해주세요.

{verification_url}

이 링크는 24시간 동안 유효합니다.
만약 본인이 요청하지 않았다면 이 이메일을 무시하세요.

---
이 메일은 자동으로 발송된 메일입니다.
            """
            
            # 메시지 본문 추가
            text_part = MIMEText(text_body, "plain", "utf-8")
            html_part = MIMEText(html_body, "html", "utf-8")
            
            message.attach(text_part)
            message.attach(html_part)
            
            # SMTP 서버 연결 및 이메일 전송
            with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
                server.starttls()  # TLS 암호화 활성화
                server.login(SMTP_EMAIL, SMTP_PASSWORD)
                server.send_message(message)
            
            logger.info(f"이메일 인증 메일 전송 성공: {email}")
            return True
            
        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"SMTP 인증 실패: {e}")
            return False
        except smtplib.SMTPException as e:
            logger.error(f"SMTP 오류 발생: {e}")
            return False
        except Exception as e:
            logger.error(f"이메일 전송 실패: {str(e)}", exc_info=True)
            return False
    
    @staticmethod
    def send_password_reset_email(email: str, token: str, reset_url: Optional[str] = None) -> bool:
        """
        비밀번호 재설정 메일 전송
        
        Args:
            email: 수신자 이메일 주소
            token: 재설정 토큰
            reset_url: 재설정 URL (없으면 자동 생성)
        
        Returns:
            bool: 전송 성공 여부
        """
        if not SMTP_EMAIL or not SMTP_PASSWORD:
            logger.warning("SMTP 설정이 완료되지 않았습니다. SMTP_EMAIL과 SMTP_PASSWORD를 확인하세요.")
            return False
        
        try:
            # 재설정 URL 생성
            if not reset_url:
                from flask import request
                base_url = request.host_url.rstrip('/') if request else 'http://localhost:5000'
                reset_url = f"{base_url}/api/v1/auth/reset-password?token={token}"
            
            # 이메일 메시지 생성
            message = MIMEMultipart("alternative")
            message["Subject"] = "PrivAlert 비밀번호 재설정"
            message["From"] = SMTP_FROM
            message["To"] = email
            
            # 이메일 본문 (HTML 형식)
            html_body = f"""
            <html>
              <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                  <h2 style="color: #1e3a8a;">비밀번호 재설정 요청</h2>
                  <p>비밀번호를 재설정하기 위해 아래 링크를 클릭해주세요.</p>
                  <div style="text-align: center; margin: 30px 0;">
                    <a href="{reset_url}" 
                       style="background-color: #3b82f6; color: white; padding: 12px 24px; 
                              text-decoration: none; border-radius: 8px; display: inline-block; 
                              font-weight: bold;">
                      비밀번호 재설정하기
                    </a>
                  </div>
                  <p style="color: #666; font-size: 14px;">
                    또는 아래 링크를 복사하여 브라우저에 붙여넣으세요:<br>
                    <a href="{reset_url}" style="color: #3b82f6; word-break: break-all;">{reset_url}</a>
                  </p>
                  <p style="color: #dc2626; font-size: 14px;">
                    ⚠️ 본인이 요청하지 않았다면 이 이메일을 무시하세요.
                  </p>
                  <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
                  <p style="color: #999; font-size: 12px; text-align: center;">
                    이 메일은 자동으로 발송된 메일입니다.
                  </p>
                </div>
              </body>
            </html>
            """
            
            # 텍스트 형식 본문
            text_body = f"""
비밀번호 재설정 요청

비밀번호를 재설정하기 위해 아래 링크를 클릭해주세요.

{reset_url}

⚠️ 본인이 요청하지 않았다면 이 이메일을 무시하세요.

---
이 메일은 자동으로 발송된 메일입니다.
            """
            
            # 메시지 본문 추가
            text_part = MIMEText(text_body, "plain", "utf-8")
            html_part = MIMEText(html_body, "html", "utf-8")
            
            message.attach(text_part)
            message.attach(html_part)
            
            # SMTP 서버 연결 및 이메일 전송
            with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
                server.starttls()
                server.login(SMTP_EMAIL, SMTP_PASSWORD)
                server.send_message(message)
            
            logger.info(f"비밀번호 재설정 메일 전송 성공: {email}")
            return True
            
        except Exception as e:
            logger.error(f"비밀번호 재설정 메일 전송 실패: {str(e)}", exc_info=True)
            return False

