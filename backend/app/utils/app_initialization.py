"""앱 초기화 유틸리티"""
import os
import threading
import time
from flask import Flask
from app.extensions.database import db
from app.models import User, Token, UserSession, AuditLog  # noqa: F401
from app.utils.db_init import init_database
from app.utils.file_cleanup import load_session_tracker, start_cleanup_thread
from app.utils.csrf_protection import cleanup_expired_tokens
try:
    from app.tasks.cleanup_worker import start_cleanup_scheduler
    from apscheduler.triggers.interval import IntervalTrigger
    # Token과 UserSession은 이미 위에서 import됨
    CLEANUP_SCHEDULER_AVAILABLE = True
except ImportError:
    CLEANUP_SCHEDULER_AVAILABLE = False
from config import BASE_DATA_DIR
import logging

logger = logging.getLogger(__name__)


def initialize_database(app: Flask):
    """데이터베이스 초기화"""
    with app.app_context():
        try:
            init_database()
        except Exception:
            pass


def initialize_background_tasks(app: Flask):
    """백그라운드 작업 초기화"""
    with app.app_context():
        try:
            load_session_tracker(BASE_DATA_DIR)
            start_cleanup_thread(BASE_DATA_DIR)
        except Exception:
            pass
        
        try:
            def csrf_cleanup_loop():
                while True:
                    try:
                        time.sleep(3600)
                        cleanup_expired_tokens()
                    except Exception:
                        pass
            
            thread = threading.Thread(target=csrf_cleanup_loop, daemon=True)
            thread.start()
        except Exception:
            pass
        
        if not CLEANUP_SCHEDULER_AVAILABLE:
            logger.warning("APScheduler가 설치되지 않아 백그라운드 작업 스케줄러를 사용할 수 없습니다")
            return
        
        try:
            scheduler = start_cleanup_scheduler()
            
            def cleanup_tokens():
                try:
                    Token.cleanup_expired_tokens()
                except Exception:
                    pass
            
            def cleanup_sessions():
                try:
                    UserSession.cleanup_expired_sessions()
                except Exception:
                    pass
            
            scheduler.add_job(
                cleanup_tokens,
                trigger=IntervalTrigger(hours=1),
                id='cleanup_expired_tokens',
                replace_existing=True
            )
            
            scheduler.add_job(
                cleanup_sessions,
                trigger=IntervalTrigger(hours=1),
                id='cleanup_expired_sessions',
                replace_existing=True
            )
            
            import atexit
            atexit.register(lambda: scheduler.shutdown())
        except Exception:
            pass

