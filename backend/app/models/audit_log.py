"""
감사 로그 모델
보안: 모든 중요한 이벤트 기록 (로그인, 로그아웃, 비밀번호 변경 등)
"""
from datetime import datetime, timedelta
from app.extensions.database import db
from typing import Optional
import json


class AuditLog(db.Model):
    """
    감사 로그 모델
    보안:
    - 모든 중요한 사용자 활동 기록
    - 민감 정보는 로그에 포함하지 않음
    - 보관 기간 관리 (예: 90일)
    """
    __tablename__ = 'audit_logs'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True, index=True)
    
    # 이벤트 정보
    event_type = db.Column(db.String(50), nullable=False, index=True)  # 'login', 'logout', 'password_change', etc.
    event_description = db.Column(db.Text, nullable=True)
    
    # 요청 정보 (민감 정보 제외)
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.String(500), nullable=True)
    request_method = db.Column(db.String(10), nullable=True)
    request_path = db.Column(db.String(500), nullable=True)
    
    # 결과
    success = db.Column(db.Boolean, nullable=False, default=True)
    error_message = db.Column(db.Text, nullable=True)  # 내부 로그용 (사용자에게 노출하지 않음)
    
    # 메타데이터 (JSON)
    extra_data = db.Column(db.Text, nullable=True)  # 추가 정보 (JSON 형식, metadata는 SQLAlchemy 예약어)
    
    # 타임스탬프
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # 보안: 인덱스 추가
    __table_args__ = (
        db.Index('idx_user_id', 'user_id'),
        db.Index('idx_event_type', 'event_type'),
        db.Index('idx_created_at', 'created_at'),
        db.Index('idx_user_event', 'user_id', 'event_type'),
    )
    
    # 관계 설정
    user = db.relationship('User', backref='audit_logs')
    
    @staticmethod
    def log_event(user_id: Optional[int], event_type: str, event_description: str = None,
                 ip_address: str = None, user_agent: str = None, request_method: str = None,
                 request_path: str = None, success: bool = True, error_message: str = None,
                 extra_data: dict = None):
        """
        감사 로그 기록
        보안: 민감 정보(비밀번호, 토큰 등)는 절대 포함하지 않음
        """
        log = AuditLog(
            user_id=user_id,
            event_type=event_type,
            event_description=event_description,
            ip_address=ip_address,
            user_agent=user_agent,
            request_method=request_method,
            request_path=request_path,
            success=success,
            error_message=error_message,
            extra_data=json.dumps(extra_data) if extra_data else None
        )
        
        db.session.add(log)
        db.session.commit()
        
        return log
    
    @staticmethod
    def log_login(user_id: int, success: bool, ip_address: str = None, 
                 user_agent: str = None, error_message: str = None):
        """
        로그인 이벤트 기록
        """
        return AuditLog.log_event(
            user_id=user_id if success else None,
            event_type='login',
            event_description='사용자 로그인 시도',
            ip_address=ip_address,
            user_agent=user_agent,
            success=success,
            error_message=error_message
        )
    
    @staticmethod
    def log_logout(user_id: int, ip_address: str = None, user_agent: str = None):
        """
        로그아웃 이벤트 기록
        """
        return AuditLog.log_event(
            user_id=user_id,
            event_type='logout',
            event_description='사용자 로그아웃',
            ip_address=ip_address,
            user_agent=user_agent,
            success=True
        )
    
    @staticmethod
    def log_password_change(user_id: int, ip_address: str = None, user_agent: str = None):
        """
        비밀번호 변경 이벤트 기록
        """
        return AuditLog.log_event(
            user_id=user_id,
            event_type='password_change',
            event_description='비밀번호 변경',
            ip_address=ip_address,
            user_agent=user_agent,
            success=True
        )
    
    @staticmethod
    def log_account_deletion(user_id: int, ip_address: str = None, user_agent: str = None):
        """
        계정 삭제 요청 이벤트 기록
        """
        return AuditLog.log_event(
            user_id=user_id,
            event_type='account_deletion',
            event_description='계정 삭제 요청',
            ip_address=ip_address,
            user_agent=user_agent,
            success=True
        )
    
    @staticmethod
    def log_mfa_enabled(user_id: int, ip_address: str = None, user_agent: str = None):
        """
        MFA 활성화 이벤트 기록
        """
        return AuditLog.log_event(
            user_id=user_id,
            event_type='mfa_enabled',
            event_description='MFA 활성화',
            ip_address=ip_address,
            user_agent=user_agent,
            success=True
        )
    
    @staticmethod
    def log_mfa_disabled(user_id: int, ip_address: str = None, user_agent: str = None):
        """
        MFA 비활성화 이벤트 기록
        """
        return AuditLog.log_event(
            user_id=user_id,
            event_type='mfa_disabled',
            event_description='MFA 비활성화',
            ip_address=ip_address,
            user_agent=user_agent,
            success=True
        )
    
    @staticmethod
    def cleanup_old_logs(days: int = 90):
        """
        오래된 로그 정리 (백그라운드 작업)
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        deleted = AuditLog.query.filter(
            AuditLog.created_at < cutoff_date
        ).delete()
        db.session.commit()
        return deleted
    
    def to_dict(self) -> dict:
        """
        감사 로그를 딕셔너리로 변환
        """
        extra_data_dict = None
        if self.extra_data:
            try:
                extra_data_dict = json.loads(self.extra_data)
            except:
                pass
        
        return {
            'id': self.id,
            'user_id': self.user_id,
            'event_type': self.event_type,
            'event_description': self.event_description,
            'ip_address': self.ip_address,
            'user_agent': self.user_agent,
            'request_method': self.request_method,
            'request_path': self.request_path,
            'success': self.success,
            'created_at': self.created_at.isoformat(),
            'metadata': extra_data_dict,  # API 응답에서는 metadata로 유지 (하위 호환성)
        }
    
    def __repr__(self):
        return f'<AuditLog {self.event_type} for user {self.user_id}>'

