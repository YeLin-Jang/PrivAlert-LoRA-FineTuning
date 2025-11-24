"""
파일 자동 삭제 유틸리티
사용자 세션별 파일 추적 및 자동 삭제
"""
import os
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Set
from pathlib import Path
import json
from app.utils.logger import get_logger

logger = get_logger(__name__)

# 세션별 파일 추적 (메모리 내)
# ⚠️ 프로덕션 주의: 메모리 기반 추적은 서버 재시작 시 데이터 손실
# 프로덕션에서는 DB 또는 Redis 사용 권장 (REDIS_URL 환경 변수 설정 필요)
# {session_id: {files: Set[str], created_at: datetime}}
_session_files: Dict[str, Dict] = {}

# 파일별 세션 추적 (메모리 내)
# ⚠️ 프로덕션 주의: 메모리 기반 추적은 서버 재시작 시 데이터 손실
# {file_path: session_id}
_file_sessions: Dict[str, str] = {}

# 세션별 파일 추적 파일 (영속성)
SESSION_TRACKER_FILE = "session_tracker.json"

# 락 (스레드 안전성)
_lock = threading.Lock()

# 파일 유지 시간 (기본 1시간)
FILE_RETENTION_HOURS = int(os.getenv("FILE_RETENTION_HOURS", "1"))

# 정리 주기 (기본 10분)
CLEANUP_INTERVAL_SECONDS = int(os.getenv("CLEANUP_INTERVAL_SECONDS", "600"))


def load_session_tracker(base_dir: str) -> None:
    """세션 추적 파일 로드 (서버 재시작 시)"""
    global _session_files, _file_sessions
    tracker_path = os.path.join(base_dir, SESSION_TRACKER_FILE)
    
    if not os.path.exists(tracker_path):
        return
    
    try:
        with open(tracker_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        with _lock:
            for session_id, session_data in data.items():
                files = set(session_data.get("files", []))
                created_at_str = session_data.get("created_at")
                
                if created_at_str:
                    try:
                        created_at = datetime.fromisoformat(created_at_str)
                    except:
                        created_at = datetime.now()
                else:
                    created_at = datetime.now()
                
                _session_files[session_id] = {
                    "files": files,
                    "created_at": created_at
                }
                
                for file_path in files:
                    _file_sessions[file_path] = session_id
        
        # 세션 추적 파일 로드 완료 (로그 제거)
    except Exception as e:
        logger.error(f"세션 추적 파일 로드 실패: {e}")


def save_session_tracker(base_dir: str) -> None:
    """세션 추적 파일 저장"""
    tracker_path = os.path.join(base_dir, SESSION_TRACKER_FILE)
    
    try:
        with _lock:
            data = {}
            for session_id, session_data in _session_files.items():
                data[session_id] = {
                    "files": list(session_data["files"]),
                    "created_at": session_data["created_at"].isoformat()
                }
        
        os.makedirs(os.path.dirname(tracker_path), exist_ok=True)
        with open(tracker_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"세션 추적 파일 저장 실패: {e}")


def register_file(session_id: str, file_path: str, base_dir: str) -> None:
    """파일을 세션에 등록"""
    if not session_id or not file_path:
        return
    
    abs_path = os.path.abspath(file_path)
    base_abs = os.path.abspath(base_dir)
    
    # 보안: 경로 검증
    if not abs_path.startswith(base_abs):
        logger.warning(f"안전하지 않은 파일 경로: {file_path}")
        return
    
    with _lock:
        if session_id not in _session_files:
            _session_files[session_id] = {
                "files": set(),
                "created_at": datetime.now()
            }
        
        _session_files[session_id]["files"].add(abs_path)
        _file_sessions[abs_path] = session_id
    
    # 주기적으로 저장 (성능 최적화)
    save_session_tracker(base_dir)


def unregister_file(session_id: str, file_path: str, base_dir: str) -> None:
    """파일을 세션에서 제거"""
    if not session_id or not file_path:
        return
    
    abs_path = os.path.abspath(file_path)
    
    with _lock:
        if session_id in _session_files:
            _session_files[session_id]["files"].discard(abs_path)
            
            # 세션에 파일이 없으면 세션도 제거
            if not _session_files[session_id]["files"]:
                del _session_files[session_id]
        
        if abs_path in _file_sessions:
            del _file_sessions[abs_path]
    
    save_session_tracker(base_dir)


def delete_file_safe(file_path: str) -> bool:
    """안전하게 파일 삭제"""
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            # 파일 삭제 완료 (로그 제거)
            return True
    except Exception as e:
        logger.error(f"파일 삭제 실패: {file_path}, 오류: {e}")
    return False


def cleanup_session_files(session_id: str, base_dir: str) -> int:
    """세션의 모든 파일 삭제"""
    deleted_count = 0
    
    with _lock:
        if session_id not in _session_files:
            return 0
        
        files_to_delete = list(_session_files[session_id]["files"])
        del _session_files[session_id]
        
        for file_path in files_to_delete:
            if file_path in _file_sessions:
                del _file_sessions[file_path]
    
    # 락 해제 후 파일 삭제 (파일 I/O는 락 밖에서)
    for file_path in files_to_delete:
        if delete_file_safe(file_path):
            deleted_count += 1
    
    save_session_tracker(base_dir)
    # 세션 파일 정리 완료 (로그 제거)
    return deleted_count


def cleanup_old_files(base_dir: str, max_age_hours: int = None) -> int:
    """오래된 파일 자동 삭제"""
    if max_age_hours is None:
        max_age_hours = FILE_RETENTION_HOURS
    
    deleted_count = 0
    cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
    
    with _lock:
        sessions_to_clean = []
        for session_id, session_data in list(_session_files.items()):
            if session_data["created_at"] < cutoff_time:
                sessions_to_clean.append(session_id)
    
    # 락 해제 후 파일 삭제
    for session_id in sessions_to_clean:
        deleted_count += cleanup_session_files(session_id, base_dir)
    
    return deleted_count


def cleanup_file(file_path: str, base_dir: str) -> bool:
    """특정 파일 삭제 (세션에서도 제거)"""
    abs_path = os.path.abspath(file_path)
    
    with _lock:
        session_id = _file_sessions.get(abs_path)
        if session_id and session_id in _session_files:
            _session_files[session_id]["files"].discard(abs_path)
            if not _session_files[session_id]["files"]:
                del _session_files[session_id]
        
        if abs_path in _file_sessions:
            del _file_sessions[abs_path]
    
    save_session_tracker(base_dir)
    return delete_file_safe(abs_path)


def start_cleanup_thread(base_dir: str) -> None:
    """백그라운드 정리 스레드 시작"""
    def cleanup_loop():
        while True:
            try:
                time.sleep(CLEANUP_INTERVAL_SECONDS)
                cleanup_old_files(base_dir)
            except Exception as e:
                logger.error(f"자동 정리 오류: {e}")
    
    thread = threading.Thread(target=cleanup_loop, daemon=True)
    thread.start()
    # 파일 자동 정리 스레드 시작 (로그 제거)


def get_session_files(session_id: str) -> List[str]:
    """세션에 등록된 파일 목록 반환"""
    with _lock:
        if session_id in _session_files:
            return list(_session_files[session_id]["files"])
    return []


def get_file_session(file_path: str) -> str | None:
    """파일 경로로 세션 ID 조회"""
    abs_path = os.path.abspath(file_path)
    with _lock:
        return _file_sessions.get(abs_path)


def generate_session_id() -> str:
    """세션 ID 생성"""
    import uuid
    return uuid.uuid4().hex

