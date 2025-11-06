from flask import Blueprint, request, jsonify
from app.services.llm_service import LLMService
from app.utils.logger import get_logger

logger = get_logger(__name__)

education_bp = Blueprint("education", __name__)
_svc: LLMService | None = None

# 서비스 초기화 (지연 로딩)
def _get_service():
    global _svc
    if _svc is None:
        try:
            _svc = LLMService()
            logger.info("LLM Service 초기화 성공")
        except Exception as e:
            logger.warning(f"LLM Service 초기화 실패: {e}")
            _svc = None
    return _svc


@education_bp.route('/suggest', methods=['POST'])
def suggest():
    try:
        body = request.get_json(silent=True) or {}
        masked = (body.get('masked_text') or '').strip()
        categories = body.get('categories') or {}
        language = (body.get('language') or 'ko').strip() or 'ko'
        tone = (body.get('tone') or 'educational').strip() or 'educational'

        logger.info(f"교육 제안 요청: masked_text 길이={len(masked)}, categories={list(categories.keys()) if categories else []}")

        if not masked and not categories:
            logger.warning("교육 제안 요청: 텍스트와 카테고리가 모두 없음")
            return jsonify({"success": False, "error": "no content"}), 400

        svc = _get_service()
        if svc is not None:
            try:
                out = svc.suggest(masked, categories, language=language, tone=tone)
                logger.info(f"교육 제안 생성 성공: items={len(out.get('items', [])) if isinstance(out, dict) else 0}")
                return jsonify({"success": True, "data": out})
            except Exception as e:
                logger.error(f"LLM Service 호출 실패: {e}", exc_info=True)
                # 에러 발생 시에도 폴백으로 응답

        # 폴백: 간단 멘트만
        logger.info("교육 제안: 폴백 응답 반환")
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
    except Exception as e:
        logger.error(f"교육 제안 엔드포인트 오류: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": "교육 제안 생성 중 오류가 발생했습니다"
        }), 500


