"""
백그라운드 파일 정리 작업
보안: 오래된 세션 자동 삭제, 실패 재시도
"""
import os
import time
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from app.utils.logger import get_logger
from app.utils.secure_storage import STORAGE_ROOT, delete_session, validate_path

logger = get_logger(__name__)

# 재시도 큐 (실제로는 Redis나 DB에 저장해야 함)
_retry_queue: List[Dict] = []

# 세션 만료 시간 (기본 1시간)
SESSION_EXPIRY_HOURS = int(os.getenv("SESSION_EXPIRY_HOURS", "1"))

# 정리 주기 (기본 10분)
CLEANUP_INTERVAL_MINUTES = int(os.getenv("CLEANUP_INTERVAL_MINUTES", "10"))


def cleanup_old_sessions():
    """
    오래된 세션 정리
    보안: 마지막 수정 시간 기준으로 오래된 세션 삭제
    """
    try:
        if not os.path.exists(STORAGE_ROOT):
            return
        
        cutoff_time = datetime.now() - timedelta(hours=SESSION_EXPIRY_HOURS)
        deleted_sessions = 0
        deleted_files = 0
        failed_sessions = []
        
        # 모든 세션 디렉토리 스캔
        for session_dir in os.listdir(STORAGE_ROOT):
            session_path = os.path.join(STORAGE_ROOT, session_dir)
            
            # 보안: 경로 검증
            is_valid, error = validate_path(session_path, STORAGE_ROOT)
            if not is_valid:
                logger.warning(f"안전하지 않은 세션 경로 발견: {session_dir}")
                continue
            
            if not os.path.isdir(session_path):
                continue
            
            try:
                # 세션 디렉토리의 마지막 수정 시간 확인
                # (가장 최근 파일의 수정 시간 사용)
                latest_mtime = 0
                for file in os.listdir(session_path):
                    file_path = os.path.join(session_path, file)
                    if os.path.isfile(file_path):
                        mtime = os.path.getmtime(file_path)
                        latest_mtime = max(latest_mtime, mtime)
                
                if latest_mtime == 0:
                    # 파일이 없는 빈 세션 디렉토리
                    latest_mtime = os.path.getmtime(session_path)
                
                last_modified = datetime.fromtimestamp(latest_mtime)
                
                # 만료된 세션 삭제
                if last_modified < cutoff_time:
                    file_count = delete_session(session_dir)
                    if file_count >= 0:
                        deleted_sessions += 1
                        deleted_files += file_count
                        logger.info(f"오래된 세션 삭제: session_id={session_dir[:8]}..., files={file_count}")
                    else:
                        # 삭제 실패 시 재시도 큐에 추가
                        failed_sessions.append({
                            "session_id": session_dir,
                            "attempts": 1,
                            "last_attempt": datetime.now()
                        })
                        logger.warning(f"세션 삭제 실패 (재시도 큐 추가): session_id={session_dir[:8]}...")
                        
            except Exception as e:
                logger.error(f"세션 정리 중 오류: {session_dir[:8]}..., error={e}")
                failed_sessions.append({
                    "session_id": session_dir,
                    "attempts": 1,
                    "last_attempt": datetime.now()
                })
        
        # 재시도 큐에 추가
        _retry_queue.extend(failed_sessions)
        
        if deleted_sessions > 0:
            logger.info(f"세션 정리 완료: sessions={deleted_sessions}, files={deleted_files}")
        
        return deleted_sessions, deleted_files
        
    except Exception as e:
        logger.error(f"세션 정리 작업 오류: {e}", exc_info=True)
        return 0, 0


def retry_failed_deletions():
    """
    실패한 삭제 작업 재시도
    보안: 최대 재시도 횟수 제한
    """
    MAX_RETRY_ATTEMPTS = 3
    RETRY_DELAY_MINUTES = 5
    
    if not _retry_queue:
        return
    
    retry_cutoff = datetime.now() - timedelta(minutes=RETRY_DELAY_MINUTES)
    retried = []
    
    for item in _retry_queue[:]:
        if item["attempts"] > MAX_RETRY_ATTEMPTS:
            logger.error(f"최대 재시도 횟수 초과, 포기: session_id={item['session_id'][:8]}...")
            _retry_queue.remove(item)
            continue
        
        if item["last_attempt"] < retry_cutoff:
            session_id = item["session_id"]
            try:
                file_count = delete_session(session_id)
                if file_count >= 0:
                    logger.info(f"재시도 성공: session_id={session_id[:8]}..., files={file_count}")
                    _retry_queue.remove(item)
                else:
                    item["attempts"] += 1
                    item["last_attempt"] = datetime.now()
                    logger.warning(f"재시도 실패 (재시도 횟수: {item['attempts']}): session_id={session_id[:8]}...")
            except Exception as e:
                item["attempts"] += 1
                item["last_attempt"] = datetime.now()
                logger.error(f"재시도 중 오류: session_id={session_id[:8]}..., error={e}")


def start_cleanup_scheduler():
    """
    백그라운드 정리 스케줄러 시작
    """
    scheduler = BackgroundScheduler()
    
    # 세션 정리 작업 (10분마다)
    scheduler.add_job(
        cleanup_old_sessions,
        trigger=IntervalTrigger(minutes=CLEANUP_INTERVAL_MINUTES),
        id='cleanup_old_sessions',
        replace_existing=True
    )
    
    # 재시도 작업 (5분마다)
    scheduler.add_job(
        retry_failed_deletions,
        trigger=IntervalTrigger(minutes=5),
        id='retry_failed_deletions',
        replace_existing=True
    )
    
    scheduler.start()
    logger.info(f"백그라운드 정리 스케줄러 시작 (주기: {CLEANUP_INTERVAL_MINUTES}분)")
    
    return scheduler

