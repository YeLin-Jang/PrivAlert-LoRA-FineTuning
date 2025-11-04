"""
감사 로그 모델
- 관리자 행위 및 중요 보안 이벤트 기록
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Enum, Boolean
import enum
from app.extensions.database import db, Base


class AuditAction(enum.Enum):
    """감사 로그 액션 타입"""
    LOGIN = "login"
    LOGOUT = "logout"
    LOGIN_FAILED = "login_failed"
    REGISTER = "register"
    PASSWORD_CHANGE = "password_change"
    ROLE_ASSIGN = "role_assign"
    ROLE_REVOKE = "role_revoke"
    USER_CREATE = "user_create"
    USER_UPDATE = "user_update"
    USER_DELETE = "user_delete"
    USER_LOCK = "user_lock"
    USER_UNLOCK = "user_unlock"
    ADMIN_ACTION = "admin_action"
    SENSITIVE_DATA_ACCESS = "sensitive_data_access"
    API_ACCESS = "api_access"


class AuditLog(Base):
    """
    감사 로그 모델
    - 관리자 행위 및 중요 보안 이벤트 기록
    - 민감 정보는 기록하지 않음
    """
    __tablename__ = 'audit_logs'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # 사용자 정보
    user_id = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    username = Column(String(50), nullable=True)  # 사용자명 저장 (삭제된 사용자 추적용)
    
    # 액션 정보
    action = Column(Enum(AuditAction), nullable=False, index=True)
    resource_type = Column(String(50), nullable=True)  # 리소스 타입 (예: 'user', 'role')
    resource_id = Column(Integer, nullable=True)  # 리소스 ID
    
    # 요청 정보
    ip_address = Column(String(45), nullable=True)  # IPv6 지원
    user_agent = Column(String(255), nullable=True)
    request_method = Column(String(10), nullable=True)
    request_path = Column(String(255), nullable=True)
    
    # 결과
    success = Column(Boolean, default=True, nullable=False)
    message = Column(Text, nullable=True)
    error_details = Column(Text, nullable=True)  # 오류 세부 정보 (민감 정보 제외)
    
    # 메타데이터
    metadata = Column(Text, nullable=True)  # JSON 형태 추가 정보
    
    # 타임스탬프
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    def __repr__(self):
        return f'<AuditLog {self.action.value} by {self.username} at {self.created_at}>'
    
    def to_dict(self):
        """감사 로그를 딕셔너리로 변환"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'username': self.username,
            'action': self.action.value if isinstance(self.action, AuditAction) else self.action,
            'resource_type': self.resource_type,
            'resource_id': self.resource_id,
            'ip_address': self.ip_address,
            'success': self.success,
            'message': self.message,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

