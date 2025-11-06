"""
로깅 유틸리티
보안: 민감 정보(비밀번호, 토큰, 세션키) 마스킹
시큐어코딩 가이드(2023 개정) 준수
"""
import logging
import os
import sys
import re
from typing import Any


class SensitiveDataFilter(logging.Filter):
    """
    민감 정보 마스킹 필터
    보안: 비밀번호, 토큰, 세션키 등이 로그에 노출되지 않도록 마스킹
    """
    
    # 민감 정보 패턴 (키워드 기반)
    SENSITIVE_PATTERNS = [
        (r'(?i)(password|pwd|pass)\s*[:=]\s*["\']?([^"\'\s]+)["\']?', r'\1=***'),
        (r'(?i)(token|access_token|refresh_token|csrf_token)\s*[:=]\s*["\']?([^"\'\s]+)["\']?', r'\1=***'),
        (r'(?i)(session_id|session_key|session_token)\s*[:=]\s*["\']?([^"\'\s]+)["\']?', r'\1=***'),
        (r'(?i)(secret|api_key|apikey|secret_key)\s*[:=]\s*["\']?([^"\'\s]+)["\']?', r'\1=***'),
        (r'(?i)(authorization)\s*[:=]\s*["\']?([^"\'\s]+)["\']?', r'\1=***'),
        # 이메일 주소의 일부 마스킹 (전체는 유지하되 일부만)
        (r'([a-zA-Z0-9._%+-]+)@([a-zA-Z0-9.-]+)\.([a-zA-Z]{2,})', lambda m: f'{m.group(1)[:2]}***@{m.group(2)[:2]}***.{m.group(3)}'),
    ]
    
    # 민감 정보가 포함된 JSON 필드명
    SENSITIVE_JSON_FIELDS = [
        'password', 'pwd', 'pass', 'token', 'access_token', 'refresh_token',
        'csrf_token', 'session_id', 'session_key', 'session_token',
        'secret', 'api_key', 'apikey', 'secret_key', 'authorization'
    ]
    
    def filter(self, record: logging.LogRecord) -> bool:
        """
        로그 레코드 필터링 및 민감 정보 마스킹
        """
        if hasattr(record, 'msg') and record.msg:
            # 문자열 메시지 마스킹
            if isinstance(record.msg, str):
                record.msg = self._mask_string(record.msg)
            # args 튜플의 문자열 요소 마스킹
            if hasattr(record, 'args') and record.args:
                masked_args = []
                for arg in record.args:
                    if isinstance(arg, str):
                        masked_args.append(self._mask_string(arg))
                    else:
                        masked_args.append(arg)
                record.args = tuple(masked_args)
        
        return True
    
    def _mask_string(self, text: str) -> str:
        """
        문자열에서 민감 정보 마스킹
        """
        if not isinstance(text, str):
            return text
        
        masked = text
        
        # 패턴 기반 마스킹
        for pattern, replacement in self.SENSITIVE_PATTERNS:
            if callable(replacement):
                masked = re.sub(pattern, replacement, masked)
            else:
                masked = re.sub(pattern, replacement, masked)
        
        # JSON 형식 문자열 처리 (간단한 패턴)
        # "password": "value" -> "password": "***"
        for field in self.SENSITIVE_JSON_FIELDS:
            pattern = rf'["\']?{field}["\']?\s*[:=]\s*["\']([^"\']+)["\']'
            masked = re.sub(pattern, f'"{field}": "***"', masked, flags=re.IGNORECASE)
        
        return masked


def get_logger(name):
    """
    로거 인스턴스 반환 (중복 핸들러 방지)
    보안: 민감 정보 마스킹 필터 자동 적용
    """
    logger = logging.getLogger(name)
    
    # 이미 핸들러가 설정되어 있으면 기존 로거 반환
    if logger.handlers:
        return logger
    
    # 로거 레벨 설정
    logger.setLevel(os.getenv("LOG_LEVEL", "INFO").upper())
    
    # 핸들러 추가 (중복 방지)
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logger.level)
    
    # 민감 정보 마스킹 필터 추가
    handler.addFilter(SensitiveDataFilter())
    
    # 포맷터 설정 (일관된 형식)
    formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    handler.setFormatter(formatter)
    
    # 상위 로거로 전파 방지 (중복 출력 방지)
    logger.propagate = False
    logger.addHandler(handler)
    
    return logger


