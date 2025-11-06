"""로깅 유틸리티"""
import logging
import os
import sys

def get_logger(name):
    """로거 인스턴스 반환 (중복 핸들러 방지)"""
    logger = logging.getLogger(name)
    
    # 이미 핸들러가 설정되어 있으면 기존 로거 반환
    if logger.handlers:
        return logger
    
    # 로거 레벨 설정
    logger.setLevel(os.getenv("LOG_LEVEL", "INFO").upper())
    
    # 핸들러 추가 (중복 방지)
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logger.level)
    
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


