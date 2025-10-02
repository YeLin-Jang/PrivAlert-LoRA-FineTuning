from flask import Blueprint, request, jsonify
from app.services.llm_service import LLMService

education_bp = Blueprint("education", __name__)
_svc: LLMService | None = None

# 서비스 초기화 (지연 로딩)
def _get_service():
    global _svc
    if _svc is None:
        try:
            _svc = LLMService()
        except Exception as e:
            print(f"LLM Service 초기화 실패: {e}")
            _svc = None
    return _svc


@education_bp.route('/suggest', methods=['POST'])
def suggest():
    body = request.get_json(silent=True) or {}
    masked = (body.get('masked_text') or '').strip()
    categories = body.get('categories') or {}
    language = (body.get('language') or 'ko').strip() or 'ko'
    tone = (body.get('tone') or 'educational').strip() or 'educational'

    if not masked and not categories:
        return jsonify({"success": False, "error": "no content"}), 400

    svc = _get_service()
    if svc is not None:
        try:
            out = svc.suggest(masked, categories, language=language, tone=tone)
            return jsonify({"success": True, "data": out})
        except Exception as e:
            print(f"LLM Service 호출 실패: {e}")
            pass

    # 폴백: 간단 멘트만
    return jsonify({
        "success": True,
        "data": {
            "items": [{
                "category": "general",
                "law_summary": "민감 정보 최소 수집·최소 공개 원칙을 준수하세요.",
                "risk_scenarios": ["사칭/피싱 위험", "개인정보 유출에 따른 법적 분쟁"],
                "revised_sentence": "민감 내용을 전부 마스킹하고, 필요한 요지만 전달하세요.",
                "tips": ["목적 적합성 재검토", "필요 최소 공유"]
            }],
            "cached": False,
            "model": "fallback"
        }
    })


