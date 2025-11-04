"""관리자 페이지 라우트"""
from flask import Blueprint, request, jsonify
from datetime import datetime, timedelta
from app.utils.admin_decorators import admin_required, role_required
from app.utils.logger import get_logger

logger = get_logger(__name__)

admin_bp = Blueprint('admin', __name__)

# 임시 데이터 (실제로는 데이터베이스에서 조회)
# 실제 구현 시에는 ORM 또는 SQL 쿼리 사용
MOCK_USERS = [
    {
        "id": 1,
        "username": "user1",
        "email": "user1@example.com",
        "role": "user",
        "is_active": True,
        "created_at": "2024-01-15T10:00:00",
        "last_login": "2024-01-20T14:30:00"
    },
    {
        "id": 2,
        "username": "user2",
        "email": "user2@example.com",
        "role": "user",
        "is_active": False,
        "created_at": "2024-01-10T09:00:00",
        "last_login": "2024-01-18T11:20:00"
    },
    {
        "id": 3,
        "username": "admin",
        "email": "admin@example.com",
        "role": "admin",
        "is_active": True,
        "created_at": "2024-01-01T00:00:00",
        "last_login": "2024-01-20T15:00:00"
    }
]

MOCK_DETECTIONS = [
    {
        "id": 1,
        "user_id": 1,
        "type": "phone",
        "text": "010-1234-5678",
        "risk_score": 85,
        "detected_at": "2024-01-20T10:00:00",
        "status": "detected"
    },
    {
        "id": 2,
        "user_id": 1,
        "type": "email",
        "text": "user@example.com",
        "risk_score": 70,
        "detected_at": "2024-01-20T11:00:00",
        "status": "detected"
    }
]

MOCK_LOGS = [
    {
        "id": 1,
        "user_id": 1,
        "action": "upload",
        "timestamp": "2024-01-20T10:00:00",
        "ip_address": "192.168.1.100",
        "details": "이미지 업로드"
    },
    {
        "id": 2,
        "user_id": 2,
        "action": "analyze",
        "timestamp": "2024-01-20T11:00:00",
        "ip_address": "192.168.1.101",
        "details": "텍스트 분석"
    }
]

# ============ 사용자 관리 ============

@admin_bp.route('/users', methods=['GET'])
@admin_required
def get_users():
    """사용자 목록 조회 (페이지네이션, 검색, 필터링)"""
    try:
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 10))
        search = request.args.get('search', '').lower()
        role_filter = request.args.get('role')
        status_filter = request.args.get('is_active')
        
        # 필터링
        filtered_users = MOCK_USERS.copy()
        
        if search:
            filtered_users = [
                u for u in filtered_users
                if search in u['username'].lower() or search in u.get('email', '').lower()
            ]
        
        if role_filter:
            filtered_users = [u for u in filtered_users if u['role'] == role_filter]
        
        if status_filter is not None:
            is_active = status_filter.lower() == 'true'
            filtered_users = [u for u in filtered_users if u['is_active'] == is_active]
        
        # 페이지네이션
        total = len(filtered_users)
        start = (page - 1) * per_page
        end = start + per_page
        paginated_users = filtered_users[start:end]
        
        return jsonify({
            "success": True,
            "data": {
                "users": paginated_users,
                "pagination": {
                    "page": page,
                    "per_page": per_page,
                    "total": total,
                    "pages": (total + per_page - 1) // per_page
                }
            }
        }), 200
        
    except Exception as e:
        logger.error(f"사용자 목록 조회 오류: {e}")
        return jsonify({
            "success": False,
            "error": "사용자 목록 조회 중 오류가 발생했습니다",
            "code": 500
        }), 500

@admin_bp.route('/users/<int:user_id>', methods=['GET'])
@admin_required
def get_user(user_id):
    """사용자 상세 정보"""
    try:
        user = next((u for u in MOCK_USERS if u['id'] == user_id), None)
        if not user:
            return jsonify({
                "success": False,
                "error": "사용자를 찾을 수 없습니다",
                "code": 404
            }), 404
        
        return jsonify({
            "success": True,
            "data": user
        }), 200
        
    except Exception as e:
        logger.error(f"사용자 조회 오류: {e}")
        return jsonify({
            "success": False,
            "error": "사용자 조회 중 오류가 발생했습니다",
            "code": 500
        }), 500

@admin_bp.route('/users/<int:user_id>/status', methods=['PATCH'])
@role_required('admin', 'super_admin')
def update_user_status(user_id):
    """계정 상태 변경 (활성/비활성)"""
    try:
        data = request.get_json()
        is_active = data.get('is_active')
        
        if is_active is None:
            return jsonify({
                "success": False,
                "error": "is_active 필드가 필요합니다",
                "code": 400
            }), 400
        
        user = next((u for u in MOCK_USERS if u['id'] == user_id), None)
        if not user:
            return jsonify({
                "success": False,
                "error": "사용자를 찾을 수 없습니다",
                "code": 404
            }), 404
        
        user['is_active'] = is_active
        logger.info(f"사용자 상태 변경: user_id={user_id}, is_active={is_active}")
        
        return jsonify({
            "success": True,
            "data": user,
            "message": f"계정이 {'활성화' if is_active else '비활성화'}되었습니다"
        }), 200
        
    except Exception as e:
        logger.error(f"사용자 상태 변경 오류: {e}")
        return jsonify({
            "success": False,
            "error": "상태 변경 중 오류가 발생했습니다",
            "code": 500
        }), 500

@admin_bp.route('/users/<int:user_id>/role', methods=['PATCH'])
@role_required('super_admin')  # 슈퍼 관리자만 역할 변경 가능
def update_user_role(user_id):
    """역할 변경"""
    try:
        data = request.get_json()
        new_role = data.get('role')
        
        if new_role not in ['user', 'admin', 'super_admin']:
            return jsonify({
                "success": False,
                "error": "유효하지 않은 역할입니다",
                "code": 400
            }), 400
        
        user = next((u for u in MOCK_USERS if u['id'] == user_id), None)
        if not user:
            return jsonify({
                "success": False,
                "error": "사용자를 찾을 수 없습니다",
                "code": 404
            }), 404
        
        user['role'] = new_role
        logger.info(f"사용자 역할 변경: user_id={user_id}, role={new_role}")
        
        return jsonify({
            "success": True,
            "data": user,
            "message": f"역할이 {new_role}로 변경되었습니다"
        }), 200
        
    except Exception as e:
        logger.error(f"역할 변경 오류: {e}")
        return jsonify({
            "success": False,
            "error": "역할 변경 중 오류가 발생했습니다",
            "code": 500
        }), 500

@admin_bp.route('/users/<int:user_id>/activity', methods=['GET'])
@admin_required
def get_user_activity(user_id):
    """사용자 활동 로그 조회"""
    try:
        user_logs = [log for log in MOCK_LOGS if log['user_id'] == user_id]
        
        return jsonify({
            "success": True,
            "data": {
                "user_id": user_id,
                "logs": user_logs,
                "total": len(user_logs)
            }
        }), 200
        
    except Exception as e:
        logger.error(f"활동 로그 조회 오류: {e}")
        return jsonify({
            "success": False,
            "error": "활동 로그 조회 중 오류가 발생했습니다",
            "code": 500
        }), 500

# ============ 로그 및 모니터링 ============

@admin_bp.route('/logs/activity', methods=['GET'])
@admin_required
def get_activity_logs():
    """활동 로그 조회"""
    try:
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 20))
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        filtered_logs = MOCK_LOGS.copy()
        
        # 날짜 필터링 (실제로는 DB 쿼리)
        if start_date or end_date:
            # 간단한 필터링 예시
            pass
        
        total = len(filtered_logs)
        start = (page - 1) * per_page
        end = start + per_page
        paginated_logs = filtered_logs[start:end]
        
        return jsonify({
            "success": True,
            "data": {
                "logs": paginated_logs,
                "pagination": {
                    "page": page,
                    "per_page": per_page,
                    "total": total,
                    "pages": (total + per_page - 1) // per_page
                }
            }
        }), 200
        
    except Exception as e:
        logger.error(f"활동 로그 조회 오류: {e}")
        return jsonify({
            "success": False,
            "error": "활동 로그 조회 중 오류가 발생했습니다",
            "code": 500
        }), 500

@admin_bp.route('/logs/detection', methods=['GET'])
@admin_required
def get_detection_logs():
    """탐지 로그 조회"""
    try:
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 20))
        
        total = len(MOCK_DETECTIONS)
        start = (page - 1) * per_page
        end = start + per_page
        paginated_detections = MOCK_DETECTIONS[start:end]
        
        return jsonify({
            "success": True,
            "data": {
                "detections": paginated_detections,
                "pagination": {
                    "page": page,
                    "per_page": per_page,
                    "total": total,
                    "pages": (total + per_page - 1) // per_page
                }
            }
        }), 200
        
    except Exception as e:
        logger.error(f"탐지 로그 조회 오류: {e}")
        return jsonify({
            "success": False,
            "error": "탐지 로그 조회 중 오류가 발생했습니다",
            "code": 500
        }), 500

@admin_bp.route('/stats/detection', methods=['GET'])
@admin_required
def get_detection_stats():
    """탐지 통계"""
    try:
        # 간단한 통계 계산 (실제로는 DB 집계 쿼리)
        total_detections = len(MOCK_DETECTIONS)
        avg_risk_score = sum(d['risk_score'] for d in MOCK_DETECTIONS) / total_detections if total_detections > 0 else 0
        
        stats = {
            "total_detections": total_detections,
            "average_risk_score": round(avg_risk_score, 2),
            "by_type": {
                "phone": len([d for d in MOCK_DETECTIONS if d['type'] == 'phone']),
                "email": len([d for d in MOCK_DETECTIONS if d['type'] == 'email'])
            },
            "today": {
                "count": len([d for d in MOCK_DETECTIONS if d['detected_at'].startswith('2024-01-20')]),
                "avg_risk": 75.5
            }
        }
        
        return jsonify({
            "success": True,
            "data": stats
        }), 200
        
    except Exception as e:
        logger.error(f"탐지 통계 조회 오류: {e}")
        return jsonify({
            "success": False,
            "error": "탐지 통계 조회 중 오류가 발생했습니다",
            "code": 500
        }), 500

@admin_bp.route('/stats/usage', methods=['GET'])
@admin_required
def get_usage_stats():
    """사용량 통계"""
    try:
        stats = {
            "total_users": len(MOCK_USERS),
            "active_users": len([u for u in MOCK_USERS if u['is_active']]),
            "total_detections": len(MOCK_DETECTIONS),
            "today_uploads": 15,
            "this_week_uploads": 120,
            "this_month_uploads": 450
        }
        
        return jsonify({
            "success": True,
            "data": stats
        }), 200
        
    except Exception as e:
        logger.error(f"사용량 통계 조회 오류: {e}")
        return jsonify({
            "success": False,
            "error": "사용량 통계 조회 중 오류가 발생했습니다",
            "code": 500
        }), 500

# ============ 탐지 관리 ============

@admin_bp.route('/detections', methods=['GET'])
@admin_required
def get_detections():
    """탐지 결과 조회"""
    try:
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 20))
        detection_type = request.args.get('type')
        min_risk = request.args.get('min_risk', type=int)
        
        filtered = MOCK_DETECTIONS.copy()
        
        if detection_type:
            filtered = [d for d in filtered if d['type'] == detection_type]
        
        if min_risk is not None:
            filtered = [d for d in filtered if d['risk_score'] >= min_risk]
        
        total = len(filtered)
        start = (page - 1) * per_page
        end = start + per_page
        paginated = filtered[start:end]
        
        return jsonify({
            "success": True,
            "data": {
                "detections": paginated,
                "pagination": {
                    "page": page,
                    "per_page": per_page,
                    "total": total,
                    "pages": (total + per_page - 1) // per_page
                }
            }
        }), 200
        
    except Exception as e:
        logger.error(f"탐지 결과 조회 오류: {e}")
        return jsonify({
            "success": False,
            "error": "탐지 결과 조회 중 오류가 발생했습니다",
            "code": 500
        }), 500

@admin_bp.route('/detections/<int:detection_id>', methods=['GET'])
@admin_required
def get_detection(detection_id):
    """탐지 상세 정보"""
    try:
        detection = next((d for d in MOCK_DETECTIONS if d['id'] == detection_id), None)
        if not detection:
            return jsonify({
                "success": False,
                "error": "탐지 결과를 찾을 수 없습니다",
                "code": 404
            }), 404
        
        return jsonify({
            "success": True,
            "data": detection
        }), 200
        
    except Exception as e:
        logger.error(f"탐지 조회 오류: {e}")
        return jsonify({
            "success": False,
            "error": "탐지 조회 중 오류가 발생했습니다",
            "code": 500
        }), 500

@admin_bp.route('/detections/<int:detection_id>', methods=['PATCH'])
@admin_required
def update_detection(detection_id):
    """탐지 결과 수정"""
    try:
        data = request.get_json()
        detection = next((d for d in MOCK_DETECTIONS if d['id'] == detection_id), None)
        
        if not detection:
            return jsonify({
                "success": False,
                "error": "탐지 결과를 찾을 수 없습니다",
                "code": 404
            }), 404
        
        # 업데이트 가능한 필드
        if 'risk_score' in data:
            detection['risk_score'] = data['risk_score']
        if 'status' in data:
            detection['status'] = data['status']
        if 'masked_text' in data:
            detection['masked_text'] = data['masked_text']
        
        logger.info(f"탐지 결과 수정: detection_id={detection_id}")
        
        return jsonify({
            "success": True,
            "data": detection,
            "message": "탐지 결과가 수정되었습니다"
        }), 200
        
    except Exception as e:
        logger.error(f"탐지 결과 수정 오류: {e}")
        return jsonify({
            "success": False,
            "error": "탐지 결과 수정 중 오류가 발생했습니다",
            "code": 500
        }), 500

@admin_bp.route('/dashboard/overview', methods=['GET'])
@admin_required
def get_dashboard_overview():
    """대시보드 종합 데이터"""
    try:
        overview = {
            "users": {
                "total": len(MOCK_USERS),
                "active": len([u for u in MOCK_USERS if u['is_active']]),
                "new_today": 2
            },
            "detections": {
                "total": len(MOCK_DETECTIONS),
                "today": 5,
                "avg_risk_score": 75.5
            },
            "system": {
                "uptime": "99.9%",
                "response_time": "120ms",
                "error_rate": "0.1%"
            }
        }
        
        return jsonify({
            "success": True,
            "data": overview
        }), 200
        
    except Exception as e:
        logger.error(f"대시보드 데이터 조회 오류: {e}")
        return jsonify({
            "success": False,
            "error": "대시보드 데이터 조회 중 오류가 발생했습니다",
            "code": 500
        }), 500

