#!/usr/bin/env python3
"""
안전한 파일 정리 스크립트
서버 강제 종료 등으로 인해 남아있는 파일 정리
"""
import os
import sys
import shutil
from pathlib import Path
from datetime import datetime, timedelta

# 프로젝트 루트 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.utils.secure_storage import STORAGE_ROOT, validate_path, delete_session

# 세션 만료 시간 (기본 1시간)
SESSION_EXPIRY_HOURS = int(os.getenv("SESSION_EXPIRY_HOURS", "1"))


def safe_cleanup(dry_run=True):
    """
    안전한 파일 정리
    
    Args:
        dry_run: True면 실제 삭제하지 않고 확인만
    """
    if not os.path.exists(STORAGE_ROOT):
        print(f"저장소 디렉토리가 없습니다: {STORAGE_ROOT}")
        return
    
    cutoff_time = datetime.now() - timedelta(hours=SESSION_EXPIRY_HOURS)
    deleted_sessions = 0
    deleted_files = 0
    failed_sessions = []
    
    print(f"세션 정리 시작 (만료 시간: {SESSION_EXPIRY_HOURS}시간 이전)")
    print(f"저장소: {STORAGE_ROOT}")
    print(f"Dry run: {dry_run}\n")
    
    for session_dir in os.listdir(STORAGE_ROOT):
        session_path = os.path.join(STORAGE_ROOT, session_dir)
        
        # 경로 검증
        is_valid, error = validate_path(session_path, STORAGE_ROOT)
        if not is_valid:
            print(f"⚠️  안전하지 않은 경로 건너뜀: {session_dir}")
            continue
        
        if not os.path.isdir(session_path):
            continue
        
        try:
            # 마지막 수정 시간 확인
            latest_mtime = 0
            file_count = 0
            for file in os.listdir(session_path):
                file_path = os.path.join(session_path, file)
                if os.path.isfile(file_path):
                    mtime = os.path.getmtime(file_path)
                    latest_mtime = max(latest_mtime, mtime)
                    file_count += 1
            
            if latest_mtime == 0:
                latest_mtime = os.path.getmtime(session_path)
            
            last_modified = datetime.fromtimestamp(latest_mtime)
            
            if last_modified < cutoff_time:
                if dry_run:
                    print(f"🔍 삭제 예정: session={session_dir[:8]}..., files={file_count}, last_modified={last_modified}")
                else:
                    deleted = delete_session(session_dir)
                    if deleted >= 0:
                        deleted_sessions += 1
                        deleted_files += deleted
                        print(f"✅ 삭제 완료: session={session_dir[:8]}..., files={deleted}")
                    else:
                        failed_sessions.append(session_dir)
                        print(f"❌ 삭제 실패: session={session_dir[:8]}...")
            else:
                print(f"⏳ 유지: session={session_dir[:8]}..., last_modified={last_modified}")
                
        except Exception as e:
            print(f"❌ 오류: session={session_dir[:8]}..., error={e}")
            failed_sessions.append(session_dir)
    
    print(f"\n정리 완료:")
    print(f"  삭제된 세션: {deleted_sessions}")
    print(f"  삭제된 파일: {deleted_files}")
    print(f"  실패한 세션: {len(failed_sessions)}")
    
    if failed_sessions:
        print(f"\n실패한 세션 목록:")
        for session in failed_sessions:
            print(f"  - {session[:8]}...")


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='안전한 파일 정리 스크립트')
    parser.add_argument('--execute', action='store_true', help='실제로 삭제 실행 (기본값: dry run)')
    parser.add_argument('--hours', type=int, default=SESSION_EXPIRY_HOURS, help='세션 만료 시간 (시간)')
    
    args = parser.parse_args()
    
    if args.hours != SESSION_EXPIRY_HOURS:
        os.environ['SESSION_EXPIRY_HOURS'] = str(args.hours)
        SESSION_EXPIRY_HOURS = args.hours
    
    dry_run = not args.execute
    
    if not dry_run:
        confirm = input("정말 삭제를 실행하시겠습니까? (yes/no): ")
        if confirm.lower() != 'yes':
            print("취소되었습니다.")
            sys.exit(0)
    
    safe_cleanup(dry_run=dry_run)

