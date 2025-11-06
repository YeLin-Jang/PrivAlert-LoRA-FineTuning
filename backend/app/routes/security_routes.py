"""
보안 관련 라우트 (CSP 리포트 등)
"""
import logging
from flask import Blueprint, request, jsonify

security_bp = Blueprint('security', __name__)

@security_bp.route('/csp-report', methods=['POST'])
def csp_report():
    """
    CSP 위반 리포트 수신 엔드포인트
    
    브라우저가 CSP 위반을 감지하면 이 엔드포인트로 리포트를 전송합니다.
    프로덕션 환경에서는 보안 모니터링 시스템(Sentry, ELK 등)으로 전송하는 것을 권장합니다.
    """
    try:
        # CSP 리포트는 JSON 형식으로 전송됨
        report_data = request.get_json(force=True)
        
        # CSP 위반 로그 기록
        logging.warning(
            f"CSP Violation Report: "
            f"document-uri={report_data.get('csp-report', {}).get('document-uri', 'unknown')}, "
            f"violated-directive={report_data.get('csp-report', {}).get('violated-directive', 'unknown')}, "
            f"blocked-uri={report_data.get('csp-report', {}).get('blocked-uri', 'unknown')}, "
            f"source-file={report_data.get('csp-report', {}).get('source-file', 'unknown')}, "
            f"line-number={report_data.get('csp-report', {}).get('line-number', 'unknown')}"
        )
        
        # TODO: 프로덕션 환경에서는 보안 모니터링 시스템으로 전송
        # 예: Sentry, ELK Stack, CloudWatch 등
        # if current_app.config.get('ENV') == 'production':
        #     send_to_monitoring_system(report_data)
        
        return jsonify({"status": "received"}), 200
        
    except Exception as e:
        logging.error(f"CSP Report Error: {e}", exc_info=True)
        # 에러가 발생해도 200 반환 (브라우저가 계속 리포트를 보내도록)
        return jsonify({"status": "error", "message": str(e)}), 200

