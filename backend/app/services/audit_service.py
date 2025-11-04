"""
감사 로그 서비스
- 관리자 행위 및 중요 보안 이벤트 기록
- 민감 정보는 기록하지 않음
"""

import logging
from datetime import datetime
from typing import Optional, Dict, Any
from flask import request
from app.extensions.database import get_db
from app.models.audit_log import AuditLog, AuditAction
from app.models.user import User

logger = logging.getLogger(__name__)


class AuditService:
    """감사 로그 서비스"""
    
    def log_action(
        self,
        user_id: Optional[int],
        action: AuditAction,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        request_method: Optional[str] = None,
        request_path: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[int] = None,
        success: bool = True,
        message: Optional[str] = None,
        error_details: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[AuditLog]:
        """
        감사 로그 기록
        
        Args:
            user_id: 사용자 ID
            action: 액션 타입
            ip_address: IP 주소
            user_agent: User-Agent
            request_method: HTTP 메서드
            request_path: 요청 경로
            resource_type: 리소스 타입
            resource_id: 리소스 ID
            success: 성공 여부
            message: 메시지
            error_details: 오류 세부 정보 (민감 정보 제외)
            metadata: 추가 메타데이터
        
        Returns:
            생성된 감사 로그
        """
        db = get_db()
        
        try:
            # 사용자명 조회 (삭제된 사용자 추적용)
            username = None
            if user_id:
                user = db.query(User).filter_by(id=user_id).first()
                if user:
                    username = user.username
            
            # IP 주소 자동 추출 (제공되지 않은 경우)
            if not ip_address and request:
                ip_address = self._get_client_ip()
            
            # User-Agent 자동 추출
            if not user_agent and request:
                user_agent = request.headers.get('User-Agent', '')[:255]  # 길이 제한
            
            # HTTP 메서드/경로 자동 추출
            if not request_method and request:
                request_method = request.method
            if not request_path and request:
                request_path = request.path[:255]  # 길이 제한
            
            # 감사 로그 생성
            audit_log = AuditLog(
                user_id=user_id,
                username=username,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                ip_address=ip_address,
                user_agent=user_agent,
                request_method=request_method,
                request_path=request_path,
                success=success,
                message=message,
                error_details=error_details,
                metadata=str(metadata) if metadata else None
            )
            
            db.add(audit_log)
            db.commit()
            
            logger.info(f"감사 로그 기록: {action.value} by {username} ({user_id}) - {message}")
            
            return audit_log
        
        except Exception as e:
            db.rollback()
            logger.error(f"감사 로그 기록 실패: {e}")
            return None
    
    def _get_client_ip(self) -> str:
        """클라이언트 IP 주소 추출 (프록시 고려)"""
        if not request:
            return None
        
        # 프록시를 통한 실제 IP 추출
        if request.headers.get('X-Forwarded-For'):
            # X-Forwarded-For는 여러 IP를 포함할 수 있음
            ip_list = request.headers.get('X-Forwarded-For').split(',')
            return ip_list[0].strip()
        elif request.headers.get('X-Real-IP'):
            return request.headers.get('X-Real-IP')
        else:
            return request.remote_addr or 'unknown'
    
    def get_user_logs(
        self,
        user_id: int,
        limit: int = 100,
        action: Optional[AuditAction] = None
    ) -> list:
        """사용자별 감사 로그 조회"""
        db = get_db()
        
        query = db.query(AuditLog).filter_by(user_id=user_id)
        
        if action:
            query = query.filter_by(action=action)
        
        logs = query.order_by(AuditLog.created_at.desc()).limit(limit).all()
        
        return [log.to_dict() for log in logs]
    
    def get_admin_logs(
        self,
        limit: int = 100,
        action: Optional[AuditAction] = None
    ) -> list:
        """관리자 행위 감사 로그 조회"""
        db = get_db()
        
        query = db.query(AuditLog).filter(
            AuditLog.action.in_([
                AuditAction.ADMIN_ACTION,
                AuditAction.ROLE_ASSIGN,
                AuditAction.ROLE_REVOKE,
                AuditAction.USER_CREATE,
                AuditAction.USER_UPDATE,
                AuditAction.USER_DELETE,
                AuditAction.USER_LOCK,
                AuditAction.USER_UNLOCK
            ])
        )
        
        if action:
            query = query.filter_by(action=action)
        
        logs = query.order_by(AuditLog.created_at.desc()).limit(limit).all()
        
        return [log.to_dict() for log in logs]


# 싱글톤 인스턴스
audit_service = AuditService()

