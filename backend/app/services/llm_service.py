import os
import json
import hashlib
import time
import re
import logging
from typing import Any, Dict, List, Optional

# 로거 설정
logger = logging.getLogger(__name__)

# 디버그 모드 (환경 변수로 제어)
DEBUG_LLM = os.getenv("DEBUG_LLM", "false").lower() == "true"

# Claude 모델 설정
# 환경변수 CLAUDE_MODEL이 없으면 기본값 사용
# 사용자 제공 모델명: claude-sonnet-4-5-20250929
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-5-20250929")
CACHE_TTL_SEC = int(os.getenv("LLMSERVICE_CACHE_TTL_SEC", "86400"))

# 간단 메모리 캐시 (재시도/요금 절약)
# ⚠️ 프로덕션 주의: 메모리 기반 캐시는 서버 재시작 시 데이터 손실 및 멀티 인스턴스 환경에서 공유 불가
# 프로덕션에서는 Redis 사용 필수 (REDIS_URL 환경 변수 설정 필요)
# Redis 전환 예시: redis_client.setex(cache_key, ttl, json.dumps(value))
_CACHE: Dict[str, tuple[float, Any]] = {}

# 스타일 프리셋
STYLE_PRESETS = {
    "casual_kr": {
        "name": "casual_kr",
        "tone": "일상 대화체",
        "formality": "존댓말 유지, 반말 금지",
        "length": "간결",
        "audience": "지인/동료",
        "forbidden_phrases": ["개인정보는 나중에 알려줄게요.", "해당 정보는 별도로 전달드릴게요."],
        "awkward_patterns": [
            r"개인정보는.*알려드리겠습니다",
            r"해당 정보는.*개인적으로",
            r"별도로 전달드릴게요"
        ]
    },
    "formal_notice": {
        "name": "formal_notice",
        "tone": "공식 공지체",
        "formality": "격식 유지",
        "length": "간결",
        "audience": "외부 공지/문서",
        "forbidden_phrases": ["개인정보는 나중에 알려드리겠습니다."],
        "awkward_patterns": [
            r"개인정보는.*나중에",
            r"추후에.*드리겠습니다"
        ]
    }
}

def _choose_style(tone: str) -> dict:
    """톤에 따라 스타일 프리셋 선택"""
    tone = (tone or "").lower()
    if "notice" in tone or "공지" in tone or "formal" in tone:
        return STYLE_PRESETS["formal_notice"]
    return STYLE_PRESETS["casual_kr"]

def _fewshot_block() -> str:
    """Few-shot 예시 블록"""
    return """
[나쁜 → 좋은 예시]
- "내 연락처는 [전화번호]야, 나중에 연락해." → "연락처는 필요 시 전달할게."
- "내 주민등록번호는 [주민등록번호]이야." → "신원 확인은 공식 문서로 가능해."
- "주소는 [주소]야. 택배 보내줄래?" → "주소는 개인적으로 전달할게. 택배 부탁해."
""".strip()


class LLMService:
    """LLM 기반 교육/수정 제안 서비스 (Claude API 사용, 키 없으면 폴백)"""

    def __init__(self) -> None:
        import logging
        self.logger = logging.getLogger(__name__)
        
        # 환경변수가 로드되지 않았을 수 있으므로 다시 로드 시도
        try:
            from dotenv import load_dotenv
            from pathlib import Path
            # 프로젝트 루트의 .env 파일 로드 시도
            root_dir = Path(__file__).parent.parent.parent  # backend/app/services/llm_service.py -> 프로젝트 루트
            env_path = root_dir / '.env'
            if env_path.exists():
                load_dotenv(dotenv_path=env_path, override=False)
                self.logger.info(f".env 파일 로드 완료: {env_path}")
            else:
                # 루트 디렉토리에서 찾기 시도
                backend_dir = Path(__file__).parent.parent  # backend/app/services/llm_service.py -> backend
                root_dir2 = backend_dir.parent  # backend -> 프로젝트 루트
                env_path2 = root_dir2 / '.env'
                if env_path2.exists():
                    load_dotenv(dotenv_path=env_path2, override=False)
                    self.logger.info(f".env 파일 로드 완료: {env_path2}")
                else:
                    self.logger.warning(f".env 파일을 찾을 수 없습니다. 경로: {env_path}, {env_path2}")
        except Exception as e:
            self.logger.warning(f".env 파일 로드 중 오류 (무시됨): {e}")
        
        self.api_key = os.getenv("ANTHROPIC_API_KEY")
        self.model = CLAUDE_MODEL
        
        # 디버깅: 환경변수 확인
        if self.api_key:
            self.logger.info(f"ANTHROPIC_API_KEY 발견됨 (길이: {len(self.api_key)}자)")
            self.logger.debug(f"API 키 앞 10자: {self.api_key[:10]}...")
        else:
            self.logger.error("ANTHROPIC_API_KEY 환경변수를 찾을 수 없습니다.")
            self.logger.debug("환경변수 확인:")
            self.logger.debug(f"  - os.getenv('ANTHROPIC_API_KEY'): {os.getenv('ANTHROPIC_API_KEY')}")
            # 다른 환경변수로 확인
            test_env = os.getenv("FLASK_SECRET_KEY")
            if test_env:
                self.logger.debug(f"  - FLASK_SECRET_KEY는 로드됨 (길이: {len(test_env)}자)")
            else:
                self.logger.warning("  - FLASK_SECRET_KEY도 로드되지 않음 (환경변수 로드 문제 가능성)")
        
        # Anthropic Claude 클라이언트 초기화 (키가 있을 때만)
        if self.api_key:
            try:
                from anthropic import Anthropic
                # Anthropic 클라이언트 초기화 (proxies 파라미터 제외)
                self.client = Anthropic(api_key=self.api_key)
                self.logger.info(f"Claude 클라이언트 초기화 완료: 모델={self.model}")
            except ImportError:
                self.logger.error("anthropic package가 설치되지 않았습니다. pip install anthropic 실행 필요")
                self.client = None
            except Exception as e:
                self.logger.error(f"Claude 클라이언트 초기화 실패: {e}", exc_info=True)
                self.client = None
        else:
            self.logger.error("ANTHROPIC_API_KEY 환경변수가 설정되지 않았습니다.")
            self.logger.error("Claude API를 사용할 수 없어 폴백 모드를 사용합니다.")
            self.logger.error("프롬프팅이 작동하지 않습니다. LLM 기능을 사용하려면 .env 파일에 ANTHROPIC_API_KEY를 설정하세요.")
            self.client = None

    def _cache_key(self, masked_text: str, categories: dict, language: str, style_name: str) -> str:
        raw = json.dumps({
            "masked_text": masked_text,
            "categories": categories,
            "language": language,
            "style": style_name,
        }, ensure_ascii=False, sort_keys=True)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()
    
    def _cache_get(self, key: str) -> Optional[Any]:
        """캐시에서 값 조회 (TTL 확인 포함)"""
        # ⚠️ 프로덕션: Redis로 전환 필요
        if key in _CACHE:
            timestamp, data = _CACHE[key]
            if time.time() - timestamp < CACHE_TTL_SEC:
                return data
            else:
                del _CACHE[key]
        return None
    
    def _cache_set(self, key: str, value: Any) -> None:
        """캐시에 값 저장"""
        # ⚠️ 프로덕션: Redis로 전환 필요
        _CACHE[key] = (time.time(), value)
        
        # 프로덕션 환경에서 Redis 미사용 시 경고 (최초 1회만)
        if not hasattr(self, '_redis_warning_logged'):
            flask_env = os.getenv("FLASK_ENV", "development")
            redis_url = os.getenv("REDIS_URL", "")
            if flask_env == "production" and not redis_url:
                logger.warning("⚠️ 프로덕션 환경에서 메모리 기반 캐시 사용 중. Redis 전환 권장.")
                self._redis_warning_logged = True
    
    def _cache_ttl_remaining(self, key: str) -> int:
        """캐시 TTL 남은 시간 반환 (초)"""
        if key in _CACHE:
            timestamp, _ = _CACHE[key]
            remaining = CACHE_TTL_SEC - (time.time() - timestamp)
            return max(0, int(remaining))
        return 0

    def suggest(self, masked_text: str, categories: dict, language: str = "ko", tone: str = "educational") -> dict:
        """기존 API 유지, 내부적으로 2단계 파이프라인 사용"""
        try:
            style = _choose_style(tone)
            key = self._cache_key(masked_text, categories, language, style["name"])
            
            # 캐시 확인
            cached_data = self._cache_get(key)
            if cached_data:
                result = {
                    "items": cached_data.get("items", []),
                    "revised_sentence": cached_data.get("revised_sentence", masked_text),
                    "cached": True,
                    "model": CLAUDE_MODEL,
                    "ttl_remaining": self._cache_ttl_remaining(key),
                }
                # 캐시된 rationale도 포함
                if "revised_sentence_rationale" in cached_data:
                    result["revised_sentence_rationale"] = cached_data["revised_sentence_rationale"]
                return result

            # 교육파트: LLM 사용 (Claude API)
            if DEBUG_LLM:
                logger.debug(f"교육파트 로딩 시작: categories={list(categories.keys()) if categories else []}")
                logger.debug(f"Claude 클라이언트 상태: {'있음' if self.client else '없음 (폴백 사용)'}")
            items = []
            revised_from_llm = None  # LLM에서 가져온 revised_sentence 저장
            revised_sentence_rationale = None  # LLM에서 가져온 revised_sentence_rationale 저장
            
            if self.client:
                if DEBUG_LLM:
                    logger.debug("Claude 클라이언트 사용 가능, LLM 호출 시작 (Claude API 사용)")
                try:
                    # LLM을 사용해서 교육 항목 생성
                    prompt = self._build_prompt(masked_text, categories, language, tone)
                    self.logger.debug(f"프롬프트 생성 완료, 프롬프트 길이: {len(prompt)}자")
                    self.logger.debug(f"프롬프트 마스킹된 텍스트: {masked_text}")
                    self.logger.debug(f"프롬프트 카테고리: {list(categories.keys())}")
                    self.logger.info("Claude API 호출 시작...")
                    
                    result = self._call_claude(prompt)
                    self.logger.debug(f"Claude API 응답 받음, result 타입: {type(result)}")
                    keys = (list(result.keys()) if isinstance(result, dict) else 'None')
                    self.logger.debug(f"Claude API 응답 키: {keys}")
                    
                    # revised_sentence_rationale은 항상 추출 시도 (revised_sentence 유효성과 무관)
                    if result and "revised_sentence_rationale" in result:
                        revised_sentence_rationale = result["revised_sentence_rationale"]
                        if DEBUG_LLM:
                            preview = (revised_sentence_rationale[:100]
                                      if revised_sentence_rationale else 'None')
                            logger.debug(f"revised_sentence_rationale 추출: {preview}...")
                    else:
                        logger.warning("Claude 응답에 revised_sentence_rationale이 없습니다!")
                        if DEBUG_LLM and isinstance(result, dict):
                            logger.debug(f"Claude 응답의 모든 키: {list(result.keys())}")
                    
                    if result and "items" in result and len(result["items"]) > 0:
                        items = result["items"]
                        # revised_sentence도 LLM 응답에서 가져오기 (있는 경우)
                        if "revised_sentence" in result and result["revised_sentence"]:
                            revised_from_llm = result["revised_sentence"]
                            # revised_sentence가 실제로 수정된 문장인지 확인 (예시 문장이 아닌지)
                            if revised_from_llm and len(revised_from_llm) > 10 and not any(
                                placeholder in revised_from_llm for placeholder in [
                                    "전체 마스킹된 텍스트를 자연스럽고 안전한 문장으로 수정한 결과입니다",
                                    "위의 마스킹된 텍스트를 실제로 수정한",
                                    "예시 문장을 복사하지 마세요"
                                ]
                            ):
                                self.logger.info(f"LLM으로 revised_sentence도 함께 생성됨: {revised_from_llm[:100]}...")
                            else:
                                preview = revised_from_llm[:100] if revised_from_llm else 'None'
                                msg = f"revised_sentence가 예시 문장으로 보임, 무시하고 2-pass 사용: {preview}..."
                                self.logger.warning(msg)
                                revised_from_llm = None
                        else:
                            logger.warning(f"LLM 응답에 revised_sentence가 없음. result 키: {list(result.keys())}")
                            if DEBUG_LLM:
                                if isinstance(result, dict):
                                    preview = json.dumps(result, ensure_ascii=False, indent=2)[:500]
                                else:
                                    preview = str(result)[:500]
                                logger.debug(f"LLM 응답 전체: {preview}")
                        if DEBUG_LLM:
                            logger.debug(f"LLM(Claude API)으로 교육파트 생성 완료: {len(items)}개 항목")
                        # rationale 필드가 items에 포함되어 있는지 확인
                        if DEBUG_LLM:
                            for idx, item in enumerate(items):
                                cat = item.get('category', 'unknown')
                                logger.debug(f"Item {idx} ({cat}) 키 목록: {list(item.keys())}")
                                if "law_summary_rationale" in item:
                                    preview = (item['law_summary_rationale'][:100]
                                              if item['law_summary_rationale'] else 'None')
                                    logger.debug(f"law_summary_rationale 발견: {preview}...")
                                else:
                                    logger.warning("law_summary_rationale 없음")
                                if "risk_scenarios_rationale" in item:
                                    preview = (item['risk_scenarios_rationale'][:100]
                                              if item['risk_scenarios_rationale'] else 'None')
                                    logger.debug(f"risk_scenarios_rationale 발견: {preview}...")
                                else:
                                    logger.warning("risk_scenarios_rationale 없음")
                                if "tips_rationale" in item:
                                    preview = (item['tips_rationale'][:100]
                                              if item['tips_rationale'] else 'None')
                                    logger.debug(f"tips_rationale 발견: {preview}...")
                                else:
                                    logger.warning("tips_rationale 없음")
                    else:
                        logger.warning("LLM 응답에 items가 없음, 폴백 사용")
                        if DEBUG_LLM:
                            if isinstance(result, dict):
                                preview = json.dumps(result, ensure_ascii=False, indent=2)[:500]
                            else:
                                preview = str(result)[:500]
                            logger.debug(f"LLM 응답 내용: {preview}")
                        logger.info("폴백 아이템 사용 (하드코딩된 데이터)")
                        items = self._fallback_items(categories)
                except Exception as e:
                    self.logger.error(f"LLM 교육파트 생성 실패, 폴백 사용: {e}", exc_info=True)
                    items = self._fallback_items(categories)
            else:
                # 클라이언트가 없으면 레퍼런스 또는 폴백 사용
                logger.warning("Claude 클라이언트가 없습니다! ANTHROPIC_API_KEY 환경변수를 확인하세요.")
                logger.info("폴백 아이템을 사용합니다 (하드코딩된 데이터, Claude API 미사용)")
                try:
                    items = self._educ_reference(categories)
                    if not items:
                        items = self._fallback_items(categories)
                        if DEBUG_LLM:
                            logger.debug(f"폴백 아이템 사용 (하드코딩): {len(items)}개 항목")
                except Exception as e:
                    self.logger.error(f"레퍼런스 로딩 실패, 폴백 사용: {e}", exc_info=True)
                    items = self._fallback_items(categories)
                    if DEBUG_LLM:
                        logger.debug(f"폴백 아이템 사용 (하드코딩): {len(items)}개 항목")
            
            if not items:
                # 최종 폴백: general 항목 하나
                items = [{
                    "category": "general",
                    "law_summary": "민감 정보 최소 수집·최소 공개 원칙을 준수하세요.",
                    "risk_scenarios": ["사칭/피싱 위험", "개인정보 유출에 따른 법적 분쟁"],
                    "tips": ["목적 적합성 재검토", "필요 최소한만 공유"]
                }]
            
            self.logger.info(f"교육파트 로딩 완료: {len(items)}개 항목")

            # revised_sentence 생성 (LLM에서 가져온 것이 있으면 사용, 없으면 2패스로 생성)
            self.logger.debug(f"revised_sentence 생성 시작. revised_from_llm: {revised_from_llm}")
            if revised_from_llm:
                revised = revised_from_llm
                self.logger.debug(f"LLM 응답에서 revised_sentence 사용: {revised[:100]}...")
            elif self.client:
                self.logger.debug("revised_from_llm이 없으므로 2-pass pipeline 사용")
                try:
                    revised = self._rewrite_then_critique(masked_text, style)
                    self.logger.debug(f"2-pass pipeline 완료: {revised[:100] if revised else 'None'}...")
                    if not revised or revised == masked_text:
                        self.logger.warning("2-pass pipeline이 원문과 동일, 폴백 사용")
                        revised = self._generate_revised_sentence(masked_text)
                        self.logger.debug(f"폴백 revised_sentence 생성: {revised[:100]}...")
                except Exception as e:
                    self.logger.error(f"2-pass pipeline failed, using fallback: {e}", exc_info=True)
                    try:
                        revised = self._generate_revised_sentence(masked_text)
                        self.logger.debug(f"예외 후 폴백 revised_sentence 생성: {revised[:100]}...")
                    except Exception as e2:
                        self.logger.error(f"폴백 생성도 실패: {e2}", exc_info=True)
                        revised = masked_text
            else:
                # 클라이언트 없으면 폴백
                self.logger.debug("Claude 클라이언트 없음, 폴백 사용")
                try:
                    revised = self._generate_revised_sentence(masked_text)
                    self.logger.debug(f"폴백 revised_sentence 생성: {revised[:100]}...")
                except Exception as e:
                    self.logger.error(f"폴백 생성 실패: {e}", exc_info=True)
                    revised = masked_text
            
            self.logger.debug(f"최종 revised_sentence: {revised[:100]}...")

            # 모든 item에 revised_sentence 채우기
            for it in items:
                it["revised_sentence"] = revised

            # revised_sentence_rationale 가져오기 (LLM에서 가져온 것이 있으면 사용)
            revised_sentence_rationale_final = revised_sentence_rationale

            # 캐시 저장
            try:
                cache_data = {"items": items, "revised_sentence": revised}
                if revised_sentence_rationale_final:
                    cache_data["revised_sentence_rationale"] = revised_sentence_rationale_final
                self._cache_set(key, cache_data)
            except Exception as e:
                self.logger.warning(f"캐시 저장 실패: {e}")
            
            result_dict = {
                "items": items,
                "revised_sentence": revised,
                "cached": False,
                "model": CLAUDE_MODEL if self.client else "fallback",
                "ttl_remaining": CACHE_TTL_SEC,
            }
            
            # revised_sentence_rationale이 있으면 추가
            if revised_sentence_rationale_final:
                result_dict["revised_sentence_rationale"] = revised_sentence_rationale_final
                if DEBUG_LLM:
                    logger.debug("revised_sentence_rationale 최종 응답에 포함됨")
            else:
                logger.warning(f"revised_sentence_rationale 최종 응답에 없음 (Claude API {'사용' if self.client else '미사용'})")
            
            if DEBUG_LLM:
                logger.debug(f"최종 응답 모델: {result_dict['model']}")
                included = revised_sentence_rationale_final is not None
                logger.debug(
                    f"최종 응답에 rationale 포함 여부: revised_sentence_rationale={included}"
                )
            
            return result_dict
        except Exception as e:
            # 최종 안전망: 모든 것이 실패해도 기본 응답 반환
            self.logger.error(f"suggest() 전체 실패: {e}", exc_info=True)
            return {
                "items": [{
                    "category": "general",
                    "law_summary": "민감 정보 최소 수집·최소 공개 원칙을 준수하세요.",
                    "risk_scenarios": ["사칭/피싱 위험", "개인정보 유출에 따른 법적 분쟁"],
                    "revised_sentence": masked_text,
                    "tips": ["목적 적합성 재검토", "필요 최소한만 공유"]
                }],
                "revised_sentence": masked_text,
                "cached": False,
                "model": "fallback",
                "ttl_remaining": 0,
            }

    def _rewrite_pass(self, masked_text: str, style: dict) -> str:
        """1단계: Rewrite 패스"""
        prompt = f"""
[목표]
- 개인정보 표기는 일반화/은유로 교체
- 의미/맥락 유지, 톤:{style['tone']}, 격식:{style['formality']}, 길이:{style['length']}
- 금칙어: {", ".join(style['forbidden_phrases'])}
- 어색패턴 금지(정규식 허용): {", ".join(style['awkward_patterns'])}

{_fewshot_block()}

[입력]
{masked_text}

[출력(JSON only)]
{{ "draft": "<수정 초안 한 문장>" }}
""".strip()
        
        try:
            self.logger.debug(f"Rewrite pass 시작: {masked_text[:50]}...")
            data = self._call_claude_json_raw(prompt, max_tokens=400, use_high=True)
            if not isinstance(data, dict):
                self.logger.warning(f"Rewrite pass에서 dict가 아닌 응답: {type(data)}")
                return masked_text
            draft = data.get("draft", "").strip()
            if not draft:
                self.logger.warning("Rewrite pass에서 빈 draft 반환")
                return masked_text
            self.logger.debug(f"Rewrite pass 완료: {draft[:50]}...")
            return draft
        except Exception as e:
            self.logger.error(f"Rewrite pass failed: {e}", exc_info=True)
            return masked_text

    def _critique_pass(self, original: str, draft: str, style: dict) -> dict:
        """2단계: Critique 패스"""
        checklist = [
            "의미 보존(핵심 정보/요청/행동 유도 유지)",
            "자연스러움(구어/문어 혼용 금지, 군더더기 제거)",
            f"톤/길이 준수({style['tone']} / {style['length']})",
            f"금칙어 미포함({', '.join(style['forbidden_phrases'])})",
            f"어색패턴 미포함({', '.join(style['awkward_patterns'])})"
        ]
        
        prompt = f"""
[역할] 한국어 에디터. 아래 체크리스트로 초안을 비평하고 '수정본'만 제시.

[체크리스트]
- {"; ".join(checklist)}

[원문]
{original}

[초안]
{draft}

[출력(JSON only)]
{{
  "final": "<수정문장 하나>",
  "violations": [ "<위배사항 요약 또는 빈 배열>" ]
}}
""".strip()
        
        try:
            self.logger.debug(f"Critique pass 시작: draft={draft[:50]}...")
            data = self._call_claude_json_raw(prompt, max_tokens=500, use_high=True)
            if not isinstance(data, dict):
                self.logger.warning(f"Critique pass에서 dict가 아닌 응답: {type(data)}")
                return {"final": draft, "violations": []}
            final = data.get("final", "").strip()
            violations = data.get("violations", [])
            if not isinstance(violations, list):
                violations = []
            if not final:
                self.logger.warning("Critique pass에서 빈 final 반환, draft 사용")
                final = draft
            self.logger.debug(f"Critique pass 완료: final={final[:50]}..., violations={len(violations)}")
            return {"final": final, "violations": violations}
        except Exception as e:
            self.logger.error(f"Critique pass failed: {e}", exc_info=True)
            return {"final": draft, "violations": []}

    def _rewrite_then_critique(self, masked_text: str, style: dict) -> str:
        """2단계 파이프라인: Rewrite → Critique"""
        self.logger.debug(f"2-pass pipeline 시작: {masked_text[:50]}...")
        
        draft = self._rewrite_pass(masked_text, style)
        # draft가 비면 초안으로 원문을 그대로 넣고 시도
        if not draft or draft == masked_text:
            self.logger.warning("Rewrite pass가 원문과 동일하거나 비어있음")
            draft = masked_text
        
        res = self._critique_pass(masked_text, draft, style)
        final = res.get("final", draft)
        
        # 위배사항이 있으면 한 번 더 수정 루프(최대 1회)
        if res.get("violations"):
            self.logger.debug(f"위배사항 발견, 재수정 시도: {res.get('violations')}")
            res2 = self._critique_pass(masked_text, final, style)
            if res2.get("final"):
                final = res2["final"]
        
        result = final if final else masked_text
        self.logger.debug(f"2-pass pipeline 완료: {result[:50]}...")
        return result

    def _generate_revised_sentence(self, masked_text: str) -> str:
        """간단한 수정 문장 생성 (폴백용)"""
        import re
        revised = masked_text
        
        # 1단계: 마스킹 태그가 있는 경우 처리
        # [전화번호], [주소] 등 마스킹 태그를 일반화된 표현으로 대체
        revised = re.sub(r'\[전화번호\]', '연락처는 나중에 알려줄게', revised)
        revised = re.sub(r'\[주소\]', '주소는 따로 전달할게', revised)
        revised = re.sub(r'\[이름\]', '지인', revised)
        revised = re.sub(r'\[학교명\]|\[학교\]', '소속 학교', revised)
        revised = re.sub(r'\[주민등록번호\]', '', revised)
        revised = re.sub(r'\[이메일\]', '이메일은 나중에 알려줄게', revised)
        revised = re.sub(r'\[직장명\]|\[직장\]', '근무처', revised)
        revised = re.sub(r'\[여권번호\]', '', revised)
        revised = re.sub(r'\[계좌번호\]', '계좌 정보는 따로 전달할게', revised)
        revised = re.sub(r'\[학생번호\]', '', revised)
        
        # 2단계: 마스킹 태그가 없는 경우 실제 개인정보 패턴을 찾아서 마스킹
        # 주민등록번호 패턴 (예: 880612-2345678, 8806122345678) - 괄호 안에 있을 수 있음
        revised = re.sub(r'\(?\d{6}[-\s]?\d{7}\)?', '', revised)
        
        # 여권번호 패턴 (예: M12345678, K12345678 등) - "여권번호는 M12345678" 같은 패턴
        revised = re.sub(r'여권번호는\s+[A-Z]\d{8,9}', '여권번호는 개인적으로 확인', revised)
        revised = re.sub(r'[A-Z]\d{8,9}(?=\s*이고|\s*이며|\s*,|\s*\.)', '', revised)
        
        # 학생번호 패턴 (예: 20150345) - "학생번호 20150345" 같은 패턴
        revised = re.sub(r'학생번호\s*\d{8}', '학생번호는 개인적으로 확인', revised)
        revised = re.sub(r'\(학생번호\s*\d{8}\)', '', revised)
        
        # 학교명 패턴 (예: 강남초등학교, 서울고등학교 등)
        revised = re.sub(r'\b\S+초등학교\b', '소속 초등학교', revised)
        revised = re.sub(r'\b\S+중학교\b', '소속 중학교', revised)
        revised = re.sub(r'\b\S+고등학교\b', '소속 고등학교', revised)
        revised = re.sub(r'\b\S+대학교\b', '소속 대학교', revised)
        
        # 이름 패턴 처리 - 괄호 안의 주민등록번호와 함께 제거
        # 예: "박지은(880612-2345678)" -> "지인"
        revised = re.sub(r'\b[가-힣]{2,4}\s*\(\d{6}[-\s]?\d{7}\)', '지인', revised)
        # 예: "김도윤(2015년생," -> "지인"
        revised = re.sub(r'\b[가-힣]{2,4}\s*\(\d{4}년생[^)]*\)', '지인', revised)
        # 나머지 괄호 안의 내용 제거 (이름 포함)
        revised = re.sub(r'\b[가-힣]{2,4}\s*\([^)]*\)', '지인', revised)
        
        # 나머지 마스킹 태그 제거
        revised = re.sub(r'\[.*?\]', '', revised)
        
        # 불완전한 문장 패턴 수정
        revised = re.sub(r'이고\s*,', '입니다.', revised)  # "이고," -> "입니다."
        revised = re.sub(r'이고\s*\.', '입니다.', revised)  # "이고." -> "입니다."
        revised = re.sub(r'이고\s+', '입니다. ', revised)  # "이고 " -> "입니다. "
        revised = re.sub(r'이며\s*,', '입니다.', revised)  # "이며," -> "입니다."
        revised = re.sub(r'이며\s*\.', '입니다.', revised)  # "이며." -> "입니다."
        
        # 불완전한 괄호 제거
        revised = re.sub(r'\([^)]*$', '', revised)  # 닫히지 않은 괄호 제거
        revised = re.sub(r'^[^(]*\)', '', revised)  # 열리지 않은 괄호 제거
        revised = re.sub(r'\)이\s+있습니다', '에 대한 정보가 있습니다', revised)  # ")이 있습니다" -> "에 대한 정보가 있습니다"
        revised = re.sub(r'\)\s*이\s+있습니다', '에 대한 정보가 있습니다', revised)
        
        # 연속된 공백 제거 및 정리
        revised = re.sub(r'\s+', ' ', revised).strip()
        revised = re.sub(r'\s*,\s*', ', ', revised)  # 쉼표 정리
        revised = re.sub(r'\s*\.\s*', '. ', revised)  # 마침표 정리
        revised = re.sub(r'\s*,\s*\.', '.', revised)  # ", ." -> "."
        
        # 빈 문장이나 불필요한 표현 제거
        revised = re.sub(r',\s*,+', ',', revised)  # 연속된 쉼표 제거
        revised = re.sub(r'\.\s*\.+', '.', revised)  # 연속된 마침표 제거
        revised = re.sub(r'\s+입니다\s+', '입니다. ', revised)  # "입니다 " -> "입니다. "
        
        # 이름이 그대로 남아있는 경우 제거
        revised = re.sub(r'\b[가-힣]{2,4}(?=\s+과|\s+와|\s+의)', '지인', revised)
        
        return revised if revised and len(revised.strip()) > 0 else "개인정보가 포함된 내용은 개인적으로 전달하겠습니다."

    def _fallback_items(self, categories: dict, revised_sentence: str = None) -> List[dict]:
        items: List[dict] = []
        
        # 카테고리 영어->한국어 매핑
        category_map = {
            "email": "이메일",
            "phone": "전화번호",
            "rrn": "주민등록번호",
            "account": "계좌번호",
            "passport": "여권번호",
            "ip_address": "IP주소",
            "school": "학교명",
            "name": "이름",
            "address": "주소",
            "workplace": "직장명",
            "general": "일반"
        }

        def add_item(category: str, law: str, risks: List[str], tips: List[str]):
            # 카테고리를 한국어로 변환
            category_kr = category_map.get(category, category)
            items.append({
                "category": category_kr,
                "law_summary": law,
                "risk_scenarios": risks,
                "tips": tips,
            })

        if categories.get("email"):
            email_law = (
                "개인정보보호법 제71조 제1항에 따라 개인정보처리자가 개인정보를 "
                "목적 외 이용·제공하거나 제3자에게 제공할 경우 최대 3억원의 과태료가 부과됩니다. "
                "개인정보보호법 제75조 제1항에 따라 고의로 개인정보를 유출하거나 타인에게 제공할 경우 "
                "5년 이하의 징역 또는 5천만원 이하의 벌금에 처해집니다. "
                "정보통신망 이용촉진 및 정보보호 등에 관한 법률 제48조의2 제1항에 따라 "
                "이메일 주소 등 개인정보를 무단으로 수집·이용할 경우 "
                "5년 이하의 징역 또는 5천만원 이하의 벌금에 처해질 수 있습니다."
            )
            add_item(
                "email",
                email_law,
                [
                    (
                        "이메일 주소 노출 시 피싱/사칭 공격으로 계정 탈취 위험: "
                        "공격자가 노출된 이메일 주소를 이용하여 피싱 이메일을 발송하고, "
                        "이를 통해 피해자를 피싱 사이트로 유도하여 금융정보(계좌번호, 비밀번호 등)를 "
                        "탈취한 후 불법 인출 및 재산 피해를 발생시킬 수 있습니다. "
                        "또한 이메일 주소를 이용하여 주요 온라인 서비스(은행, 쇼핑몰, SNS 등) "
                        "계정을 탈취하여 개인정보 유출, 명예 훼손, 재산 피해를 유발할 수 있습니다."
                    ),
                    (
                        "이메일 주소 노출 시 스팸·사기 메일 증가 위험: "
                        "공격자가 노출된 이메일 주소를 수집하여 스팸 메일, 피싱 메일, "
                        "악성 메일을 대량으로 발송하고, 이를 통해 추가 개인정보 탈취나 "
                        "악성코드 감염을 시도할 수 있습니다."
                    )
                ],
                [
                    (
                        "피싱 공격 방지를 위한 이메일 주소 최소수집 원칙 준수: "
                        "불필요한 이메일 주소 수집을 최소화하고, 수집 목적에 필요한 최소한의 정보만 "
                        "보관하여 노출 범위를 줄임으로써 피싱 공격의 표적이 될 가능성을 최소화합니다. "
                        "또한 이메일 주소 수집 시 반드시 개인정보보호법에 따른 동의 절차를 거쳐야 합니다."
                    ),
                    (
                        "스팸 메일 방지를 위한 외부 전송 시 최소 공개 원칙: "
                        "이메일 주소를 외부로 전송할 경우 반드시 필요한 최소한의 정보만 제공하고, "
                        "수신자 신원 확인 및 전송 목적을 명확히 합니다. "
                        "또한 TLS/SSL 등 암호화된 채널을 통해 안전하게 전송하고, "
                        "전송 로그를 남겨 이상 징후를 조기에 발견할 수 있도록 합니다."
                    )
                ],
            )
        if categories.get("phone"):
            add_item(
                "phone",
                "개인정보보호법 제71조 제1항에 따라 개인정보처리자가 개인정보를 목적 외 이용·제공하거나 제3자에게 제공할 경우 최대 3억원의 과태료가 부과됩니다. 개인정보보호법 제75조 제1항에 따라 고의로 개인정보를 유출하거나 타인에게 제공할 경우 5년 이하의 징역 또는 5천만원 이하의 벌금에 처해집니다. 정보통신망 이용촉진 및 정보보호 등에 관한 법률 제48조의2 제1항에 따라 전화번호 등 개인정보를 무단으로 수집·이용할 경우 5년 이하의 징역 또는 5천만원 이하의 벌금에 처해질 수 있습니다.",
                ["전화번호 노출 시 스미싱(SMS 피싱) 공격 위험: 공격자가 노출된 전화번호로 사기 메시지를 전송하여 피해자를 피싱 사이트로 유도하고, 이를 통해 금융정보(계좌번호, 비밀번호 등)를 탈취한 후 불법 인출 및 재산 피해를 발생시킬 수 있습니다.",
                 "전화번호 노출 시 사칭 전화 및 메신저 피싱 공격: 공격자가 노출된 전화번호를 이용하여 가짜 기관(은행, 경찰서 등)이나 지인을 사칭하는 전화 또는 메시지를 발송하고, 이를 통해 개인정보(주민등록번호, 계좌정보 등)를 탈취하여 신원 도용 및 재산 피해를 유발할 수 있습니다."],
                ["스미싱 공격 방지를 위한 전화번호 최소수집 원칙 준수: 불필요한 전화번호 수집을 최소화하고, 수집 목적에 필요한 최소한의 정보만 보관하여 노출 범위를 줄임으로써 스미싱 공격의 표적이 될 가능성을 최소화합니다. 또한 전화번호 수집 시 반드시 개인정보보호법에 따른 동의 절차를 거쳐야 합니다.",
                 "사칭 공격 방지를 위한 암호화 통신 채널 사용 및 임시번호 활용: 전화번호 등 개인정보를 외부로 전송할 경우 TLS/SSL 등 암호화된 채널을 통해 안전하게 전송하여 전송 중 전화번호가 탈취되어 사칭 공격에 악용되는 것을 방지합니다. 또한 필요 시 임시번호나 가상번호를 사용하여 실제 전화번호 노출을 방지할 수 있습니다."],
            )
        if categories.get("rrn"):
            add_item(
                "rrn",
                "개인정보보호법 제23조 제1항에 따라 주민등록번호는 원칙적으로 수집·이용할 수 없으며, 예외적으로 법령에서 구체적으로 허용하는 경우에만 처리할 수 있습니다. 개인정보보호법 제71조 제1항에 따라 주민등록번호를 목적 외로 이용하거나 제3자에게 제공할 경우 최대 3억원의 과태료가 부과됩니다. 개인정보보호법 제75조 제1항에 따라 고의로 주민등록번호를 유출하거나 타인에게 제공할 경우 5년 이하의 징역 또는 5천만원 이하의 벌금에 처해집니다.",
                ["주민등록번호 노출 시 신원 도용 위험: 공격자가 노출된 주민등록번호를 이용하여 피해자의 신원을 사칭하고, 이를 통해 대출 신청, 계좌 개설, 신용카드 발급 등 금융 서비스를 악용하여 재산 피해를 발생시킬 수 있습니다. 또한 주민등록번호를 이용하여 온라인 서비스 계정을 탈취하거나 각종 본인 인증을 우회하여 추가 개인정보를 탈취할 수 있습니다.",
                 "주민등록번호 노출 시 다단계 공격 위험: 공격자가 주민등록번호를 기반으로 다른 개인정보(이름, 주소, 전화번호 등)를 연계 추적하여 종합적인 신원 정보를 확보하고, 이를 통해 더 심각한 범죄(대규모 사기, 신용카드 사기 등)를 수행할 수 있습니다."],
                ["신원 도용 방지를 위한 주민등록번호 대체 식별자 사용: 주민등록번호 대신 법적으로 허용되는 대체 식별자(CI, DI 등)를 사용하여 개인 식별을 수행하고, 주민등록번호 수집을 원칙적으로 금지합니다. 개인정보보호법 제23조 제1항에 따라 주민등록번호는 법령에서 구체적으로 허용하는 경우에만 수집할 수 있으며, 수집 시 반드시 법적 근거와 보관기간을 명시해야 합니다.",
                 "다단계 공격 방지를 위한 정보 분리 보관 및 접근 권한 관리: 주민등록번호와 다른 개인정보를 분리하여 보관하고, 주민등록번호에 접근할 수 있는 직원 권한을 최소화합니다. 또한 정기적인 접근 로그 검토를 통해 이상 징후를 조기에 발견하고, 암호화 저장 및 전송을 적용하여 주민등록번호 유출을 방지합니다."],
            )
        if categories.get("account"):
            add_item(
                "account",
                "금융실명거래 및 비밀보장에 관한 법률 제4조 제1항에 따라 금융기관은 예금자 등의 거래에 관한 정보를 타인에게 제공하거나 누설하여서는 안 됩니다. 개인정보보호법 제71조 제1항에 따라 개인정보처리자가 개인정보를 목적 외 이용·제공하거나 제3자에게 제공할 경우 최대 3억원의 과태료가 부과됩니다. 개인정보보호법 제75조 제1항에 따라 고의로 계좌번호 등 금융정보를 유출하거나 타인에게 제공할 경우 5년 이하의 징역 또는 5천만원 이하의 벌금에 처해집니다.",
                ["계좌번호 노출 시 보이스피싱 연계 위험: 공격자가 노출된 계좌번호를 이용하여 가짜 기관(은행, 경찰서 등)을 사칭하는 보이스피싱 전화를 발송하고, 이를 통해 추가 개인정보(비밀번호, OTP 등)를 탈취하여 불법 인출 및 재산 피해를 발생시킬 수 있습니다.",
                 "계좌번호 노출 시 불법 이체 시도 위험: 공격자가 노출된 계좌번호를 이용하여 피해자의 계좌로 직접적인 불법 이체를 시도하거나, 계좌번호와 다른 개인정보를 연계하여 계좌 탈취를 시도할 수 있습니다."],
                ["보이스피싱 방지를 위한 계좌번호 최소수집 원칙: 불필요한 계좌번호 수집을 최소화하고, 수집 목적에 필요한 최소한의 정보만 보관하여 노출 범위를 줄임으로써 보이스피싱 공격의 표적이 될 가능성을 최소화합니다. 또한 금융실명거래 및 비밀보장에 관한 법률 제4조 제1항에 따라 계좌번호 등 금융정보는 타인에게 제공하거나 누설하여서는 안 됩니다.",
                 "불법 이체 방지를 위한 안전한 송금 채널 사용 및 계좌 정보 보호: 계좌번호를 외부로 전송할 경우 반드시 TLS/SSL 등 암호화된 채널을 통해 안전하게 전송하고, 가능한 경우 계좌 별칭이나 토큰화된 계좌 정보를 사용하여 실제 계좌번호 노출을 방지합니다. 또한 계좌번호에 대한 접근 권한을 최소화하고 정기적인 접근 로그를 검토합니다."],
            )
        if categories.get("passport"):
            add_item(
                "passport",
                "개인정보보호법 제24조 제1항에 따라 여권번호는 고유식별정보로 분류되며, 원칙적으로 수집·이용할 수 없고 예외적으로 법령에서 구체적으로 허용하는 경우에만 처리할 수 있습니다. 개인정보보호법 제71조 제1항에 따라 여권번호를 목적 외로 이용하거나 제3자에게 제공할 경우 최대 3억원의 과태료가 부과됩니다. 개인정보보호법 제75조 제1항에 따라 고의로 여권번호를 유출하거나 타인에게 제공할 경우 5년 이하의 징역 또는 5천만원 이하의 벌금에 처해집니다.",
                ["여권번호 노출 시 국제 사기 및 티켓 발권 악용 위험: 공격자가 노출된 여권번호를 이용하여 피해자의 신원을 사칭하고, 이를 통해 국제 항공권 발권, 호텔 예약, 국제 금융 서비스 이용 등 다양한 국제 사기를 수행하여 재산 피해를 발생시킬 수 있습니다. 또한 여권번호를 이용하여 국경을 넘나드는 범죄 활동에 악용될 수 있습니다.",
                 "여권번호 노출 시 신원 도용 및 국제 추적 위험: 공격자가 여권번호를 기반으로 피해자의 신원을 완전히 사칭하고, 다른 국가에서 범죄 활동을 수행하거나 불법 입출국을 시도하여 피해자에게 심각한 법적 문제를 야기할 수 있습니다."],
                ["국제 사기 방지를 위한 여권번호 최소수집 원칙: 개인정보보호법 제24조 제1항에 따라 여권번호는 원칙적으로 수집·이용할 수 없으며, 예외적으로 법령에서 구체적으로 허용하는 경우에만 수집할 수 있습니다. 여권번호 수집 시 반드시 법적 근거와 보관기간을 명시하고, 수집 목적 달성 후 즉시 폐기해야 합니다.",
                 "신원 도용 방지를 위한 문서 보안 관리: 여권번호가 포함된 문서를 공유할 경우 반드시 필요한 최소 인원에게만 공유하고, 문서 공유 전 메타데이터 및 이미지 EXIF 정보를 제거하여 추가 개인정보 노출을 방지합니다. 또한 TLS/SSL 등 암호화된 채널을 통해 안전하게 전송하고, 전송 로그를 남겨 추적 가능하도록 합니다."],
            )
        if categories.get("ip_address"):
            add_item(
                "ip_address",
                "IP 주소는 개인 위치/행태 추정에 악용될 수 있어 보호 필요합니다.",
                ["지리적 위치 추정", "서비스 공격 표적화"],
                ["로그 공유 시 기간·범위 최소화", "내부 접근 통제"],
            )
        if categories.get("school"):
            add_item(
                "school",
                "개인정보보호법 제71조 제1항에 따라 개인정보처리자가 개인정보를 목적 외 이용·제공할 경우 최대 3억원의 과태료가 부과됩니다. 개인정보보호법 제75조 제1항에 따라 고의로 개인정보를 유출하거나 타인에게 제공할 경우 5년 이하의 징역 또는 5천만원 이하의 벌금에 처해집니다. 초·중등교육법 제30조의2에 따라 학생의 인적사항 등 개인정보를 보호할 의무가 있으며, 이를 위반할 경우 초·중등교육법 시행령에 따라 교육부 장관의 시정 조치를 받을 수 있습니다.",
                ["학교명 노출 시 학생 신원 추적 및 표적화 위험: 학교명이 노출되면 공격자가 해당 학교의 학생 명단을 확보하거나 SNS 등에서 학교명을 검색하여 특정 학생의 신원을 식별하고, 이를 다른 개인정보(이름, 주소, 연락처 등)와 연계하여 추적 및 표적화를 수행할 수 있습니다. 이는 스토킹, 괴롭힘, 신원 도용 등으로 이어질 수 있습니다.",
                 "학교명 노출 시 피싱/사칭 공격 위험: 공격자가 노출된 학교명을 이용하여 가짜 학교 공지나 행사(학부모회, 체험 학습 등)를 사칭하는 이메일이나 메시지를 발송하고, 이를 통해 학생 및 학부모의 개인정보(주민등록번호, 계좌정보 등)를 탈취하여 신원 도용 및 재산 피해를 발생시킬 수 있습니다."],
                ["학생 신원 추적 방지를 위한 일반화된 표현 사용: 구체적인 학교명 대신 '지역 내 교육기관', '소속 학교' 등 일반화된 표현으로 대체하여 개인 식별 가능성을 최소화합니다. 이를 통해 학교명을 통한 학생 신원 추적 및 표적화를 방지할 수 있습니다. 또한 학교명과 다른 개인정보(이름, 주소 등)의 연계를 방지하기 위해 정보 분리 보관 정책을 수립해야 합니다.",
                 "피싱 공격 방지를 위한 외부 공유 시 최소 정보 원칙: 교육기관 정보를 외부에 공유할 경우 반드시 필요한 최소한의 정보만 제공하고, 학생 개인정보와의 연계를 방지합니다. 또한 학교명을 공유할 경우 반드시 수신자 신원 확인 및 공유 목적을 명확히 하고, 공유 로그를 남겨 추적 가능하도록 합니다. 이를 통해 학교명을 이용한 가짜 공지 사칭 공격을 방지할 수 있습니다."],
            )
        if categories.get("name"):
            add_item(
                "name",
                "개인정보보호법 제71조 제1항에 따라 개인정보처리자가 개인정보를 목적 외 이용·제공하거나 제3자에게 제공할 경우 최대 3억원의 과태료가 부과됩니다. 개인정보보호법 제75조 제1항에 따라 고의로 개인정보를 유출하거나 타인에게 제공할 경우 5년 이하의 징역 또는 5천만원 이하의 벌금에 처해집니다. 정보통신망 이용촉진 및 정보보호 등에 관한 법률 제48조의2 제1항에 따라 이름 등 개인정보를 무단으로 수집·이용할 경우 5년 이하의 징역 또는 5천만원 이하의 벌금에 처해질 수 있습니다.",
                ["이름 노출 시 신원 도용 위험: 공격자가 노출된 이름을 이용하여 피해자의 신원을 사칭하고, 이를 통해 온라인 서비스 계정 탈취, 금융 서비스 악용, 각종 사기 범죄를 수행하여 재산 피해 및 명예 훼손을 유발할 수 있습니다.",
                 "이름 노출 시 피싱/사칭 공격 위험: 공격자가 노출된 이름을 이용하여 지인이나 기관을 사칭하는 피싱 이메일, 메시지, 전화를 발송하고, 이를 통해 추가 개인정보(주민등록번호, 계좌정보 등)를 탈취하여 신원 도용 및 재산 피해를 발생시킬 수 있습니다."],
                ["신원 도용 방지를 위한 이름 최소수집 원칙: 불필요한 이름 수집을 최소화하고, 수집 목적에 필요한 최소한의 정보만 보관하여 노출 범위를 줄임으로써 신원 도용 공격의 표적이 될 가능성을 최소화합니다. 또한 이름 수집 시 반드시 개인정보보호법에 따른 동의 절차를 거쳐야 합니다.",
                 "피싱 공격 방지를 위한 일반화된 표현 사용 및 최소 정보 원칙: 이름 대신 '지인', '동료' 등 일반화된 표현을 사용하거나, 필요한 경우 성만 사용하여 개인 식별 가능성을 최소화합니다. 외부 공유 시 반드시 필요한 최소한의 정보만 제공하고, 수신자 신원 확인 및 공유 목적을 명확히 합니다."],
            )
        if categories.get("address"):
            add_item(
                "address",
                "개인정보보호법 제71조 제1항에 따라 개인정보처리자가 개인정보를 목적 외 이용·제공하거나 제3자에게 제공할 경우 최대 3억원의 과태료가 부과됩니다. 개인정보보호법 제75조 제1항에 따라 고의로 개인정보를 유출하거나 타인에게 제공할 경우 5년 이하의 징역 또는 5천만원 이하의 벌금에 처해집니다. 정보통신망 이용촉진 및 정보보호 등에 관한 법률 제48조의2 제1항에 따라 주소 등 개인정보를 무단으로 수집·이용할 경우 5년 이하의 징역 또는 5천만원 이하의 벌금에 처해질 수 있습니다.",
                ["주소 노출 시 신원 도용 및 추적 위험: 공격자가 노출된 주소를 이용하여 피해자의 신원을 식별하고, 이를 다른 개인정보(이름, 전화번호 등)와 연계하여 종합적인 신원 정보를 확보하여 신원 도용 범죄를 수행할 수 있습니다. 또한 주소를 이용하여 피해자의 실제 위치를 추적할 수 있습니다.",
                 "주소 노출 시 스토킹/괴롭힘 및 불법 접근 시도 위험: 공격자가 노출된 주소를 이용하여 피해자의 거주지로 직접 찾아가 스토킹, 괴롭힘, 불법 침입 등의 범죄를 수행할 수 있으며, 이는 심각한 신체적·정신적 피해로 이어질 수 있습니다."],
                ["신원 도용 방지를 위한 주소 최소수집 원칙: 불필요한 주소 수집을 최소화하고, 수집 목적에 필요한 최소한의 정보만 보관하여 노출 범위를 줄임으로써 신원 도용 공격의 표적이 될 가능성을 최소화합니다. 또한 주소 수집 시 반드시 개인정보보호법에 따른 동의 절차를 거쳐야 합니다.",
                 "스토킹 방지를 위한 일반화된 지역명 사용 및 정보 분리 보관: 상세 주소 대신 일반적인 지역명(예: '서울시 강남구')만 사용하거나, 필요 시 상세 주소는 개인적으로 전달하여 노출 범위를 최소화합니다. 또한 주소와 다른 개인정보(이름, 전화번호 등)를 분리하여 보관하여 연계 추적을 방지합니다."],
            )
        if categories.get("workplace"):
            add_item(
                "workplace",
                "개인정보보호법 제71조 제1항에 따라 개인정보처리자가 개인정보를 목적 외 이용·제공하거나 제3자에게 제공할 경우 최대 3억원의 과태료가 부과됩니다. 개인정보보호법 제75조 제1항에 따라 고의로 개인정보를 유출하거나 타인에게 제공할 경우 5년 이하의 징역 또는 5천만원 이하의 벌금에 처해집니다. 정보통신망 이용촉진 및 정보보호 등에 관한 법률 제48조의2 제1항에 따라 직장명 등 개인정보를 무단으로 수집·이용할 경우 5년 이하의 징역 또는 5천만원 이하의 벌금에 처해질 수 있습니다.",
                ["직장명 노출 시 직장 추적 및 개인 식별 위험: 직장명이 노출되면 공격자가 해당 직장의 직원 명단을 확보하거나 SNS 등에서 직장명을 검색하여 특정 직원의 신원을 식별하고, 이를 다른 개인정보(이름, 주소, 연락처 등)와 연계하여 추적 및 표적화를 수행할 수 있습니다.",
                 "직장명 노출 시 피싱/사칭 공격 위험: 공격자가 노출된 직장명을 이용하여 가짜 회사 공지나 업무 관련 사칭 이메일이나 메시지를 발송하고, 이를 통해 직원의 개인정보(주민등록번호, 계좌정보 등)를 탈취하여 신원 도용 및 재산 피해를 발생시킬 수 있습니다."],
                ["직장 추적 방지를 위한 일반화된 표현 사용: 구체적인 직장명 대신 '소속 회사', '근무처' 등 일반화된 표현으로 대체하여 개인 식별 가능성을 최소화합니다. 이를 통해 직장명을 통한 개인 추적 및 표적화를 방지할 수 있습니다. 또한 직장명과 다른 개인정보(이름, 주소 등)의 연계를 방지하기 위해 정보 분리 보관 정책을 수립해야 합니다.",
                 "피싱 공격 방지를 위한 외부 공유 시 최소 정보 원칙: 직장 정보를 외부에 공유할 경우 반드시 필요한 최소한의 정보만 제공하고, 직원 개인정보와의 연계를 방지합니다. 또한 직장명을 공유할 경우 반드시 수신자 신원 확인 및 공유 목적을 명확히 하고, 공유 로그를 남겨 추적 가능하도록 합니다. 이를 통해 직장명을 이용한 가짜 공지 사칭 공격을 방지할 수 있습니다."],
            )
        return items or [{
            "category": "general",
            "law_summary": "민감 정보 최소 수집·최소 공개 원칙을 준수하세요.",
            "risk_scenarios": ["사칭/피싱 위험", "개인정보 유출에 따른 법적 분쟁"],
            "tips": ["목적 적합성 재검토", "필요 최소한만 공유"]
        }]
    
    def _load_policies(self) -> dict:
        """data/policies.yml에서 고정 레퍼런스 로드"""
        try:
            import yaml
        except ImportError:
            logger.warning("PyYAML not installed. Install with: pip install pyyaml")
            return {}
        
        # 여러 경로 시도
        base_paths = [
            os.path.join(os.path.dirname(__file__), "..", "data", "policies.yml"),
            os.path.join(os.getcwd(), "app", "data", "policies.yml"),
            os.path.join(os.getcwd(), "data", "policies.yml"),
        ]
        
        for base in base_paths:
            if os.path.exists(base):
                try:
                    with open(base, "r", encoding="utf-8") as f:
                        return yaml.safe_load(f) or {}
                except Exception as e:
                    logger.warning(f"Failed to load policies from {base}: {e}")
                    continue
        
        logger.warning("policies.yml not found, using fallback")
        return {}
    
    def _educ_reference(self, categories: Dict[str, Any]) -> List[dict]:
        """교육파트 고정 레퍼런스에서 로드 (LLM 비사용)"""
        ref = self._load_policies()
        if DEBUG_LLM:
            logger.debug(f"로드된 레퍼런스 키: {list(ref.keys())}")
        
        # categories 처리: dict 값이 True인 경우 또는 dict인 경우 모두 처리
        norm = []
        for k, v in categories.items():
            if isinstance(v, dict):
                # dict인 경우 (예: {"count": 1, "items": [...]})
                if v.get("count", 0) > 0 or v.get("items"):
                    norm.append(k)
            elif bool(v):
                # True나 다른 truthy 값인 경우
                norm.append(k)
        
                if DEBUG_LLM:
                    logger.debug(f"정규화된 카테고리: {norm}")
        items: List[dict] = []
        
        for k in norm:
            node = ref.get(k, {})
            if not node:
                # 레퍼런스에 없으면 폴백 사용
                logger.warning(f"레퍼런스에 '{k}' 카테고리 없음")
                continue
            
            items.append({
                "category": k,
                "law_summary": node.get("law_summary_short", "민감정보는 최소 수집·최소 공개 원칙을 준수해야 함."),
                "risk_scenarios": node.get("risk_scenarios", ["사칭/피싱", "유출에 따른 법적 분쟁", "표적화"]),
                "revised_sentence": "",  # 이후 2패스 결과로 채움
                "tips": node.get("tips", ["외부 전송 최소화", "권한 점검", "전송 로그 보관"])
            })
        
        return items

    def _build_prompt(self, masked_text: str, categories: dict, language: str, tone: str) -> str:
        """프롬프트 생성"""
        category_list = list(categories.keys())
        category_list_str = ', '.join(category_list)
        
        # f-string 대신 format() 사용하여 포맷 지정자 문제 방지
        prompt_template = """
당신은 개인정보보호 전문가이자 문장을 자연스럽게 다듬는 보조자입니다. 다음 마스킹된 텍스트를 분석하여 안전하고 자연스러운 문장으로 수정하고, 관련 교육 내용을 제공해주세요.

**마스킹된 텍스트 (반드시 이 텍스트를 수정해야 합니다):**
{masked_text}

**위의 마스킹된 텍스트를 반드시 읽고, revised_sentence 필드에 실제로 수정한 결과를 작성해야 합니다.**

**발견된 민감 정보 유형:** {category_list_str}

## 수정 문장 가이드라인
다음과 같은 방식으로 자연스럽게 수정해주세요:

**예시:**
- 원문: "오늘 [이름] 씨와 점심을 먹었다." → 수정: "오늘 지인과 점심을 함께했다."
- 원문: "내 연락처는 [전화번호]야, 나중에 연락해." → 수정: "내 연락처는 나중에 알려줄게, 필요할 때 연락해."
- 원문: "내 주민등록번호는 [주민등록번호]이야." → 수정: 혹은 관련 문장을 아예 삭제.

- 원문: "[계좌번호]로 돈 보내주면 돼." → 수정: "내 계좌로 송금해주면 돼. 계좌 정보는 따로 전달할게."

**수정 원칙:**
1. 마스킹된 개인정보는 그대로 노출하지 말고, 자연스럽게 일반화된 표현으로 수정
2. 문장의 의미가 크게 달라지지 않도록 유지
3. 일상 대화체라면 일상스럽게, 기사체라면 기사 어투를 유지
4. 개인정보는 "나중에 알려줄게", "따로 전달할게", "개인적으로 알려줄게" 등으로 대체
5. 예시를 참고만하되. 너무 비슷하게 수정하지 마세요.
6. 너무 길지 마세요.
7. 너무 복잡하지 마세요.
8. 일상적인 구어체, 한국인들이 자주 쓰는 언어를 유지하세요.
9. 입력값으로 들어온 문장들과 비슷한 느낌을 주도록 수정하세요.

다음 형식의 JSON 응답을 생성해주세요 (발견된 모든 민감 정보 유형에 대해 각각 하나씩 생성):

**중요**: "revised_sentence" 필드는 위에서 제공한 **마스킹된 텍스트**를 실제로 수정한 결과여야 합니다. 예시 문장을 그대로 사용하지 마세요. 반드시 입력된 마스킹된 텍스트를 기반으로 새로운 수정 문장을 생성해야 합니다.

{{
  "revised_sentence": "[위의 마스킹된 텍스트를 실제로 수정한 완전한 문장을 여기에 작성하세요. 예시 문장을 복사하지 마세요. 마스킹된 부분([이름], [전화번호] 등)을 자연스러운 표현으로 대체한 실제 수정 문장이어야 합니다.]",
  "revised_sentence_rationale": "[수정 문장을 생성한 근거를 설명하세요. 예: '원문의 [전화번호]를 일반화된 표현으로 대체하여 개인정보 노출을 방지하면서도 문장의 의미를 유지했습니다. 전화번호는 스미싱 공격의 표적이 될 수 있어 구체적인 번호 대신 일반적인 표현을 사용했습니다.']",
  "items": [
    {{
      "category": "전화번호",
      "law_summary": "개인정보보호법 제71조 제1항에 따라 개인정보처리자가 개인정보를 목적 외 이용·제공하거나 제3자에게 제공할 경우 최대 3억원의 과태료가 부과됩니다. 개인정보보호법 제75조 제1항에 따라 고의로 개인정보를 유출하거나 타인에게 제공할 경우 5년 이하의 징역 또는 5천만원 이하의 벌금에 처해집니다. 정보통신망 이용촉진 및 정보보호 등에 관한 법률 제48조의2 제1항에 따라 전화번호 등 개인정보를 무단으로 수집·이용할 경우 5년 이하의 징역 또는 5천만원 이하의 벌금에 처해질 수 있습니다.",
      "law_summary_rationale": "[법령 요약을 생성한 근거를 설명하세요. 예: '전화번호는 개인정보보호법 제2조에서 정의하는 개인정보에 해당하며, 목적 외 이용 시 제71조에 따라 최대 3억원의 과태료가 부과됩니다. 또한 정보통신망법 제48조의2에서 무단 수집·이용 시 형사 처벌을 규정하고 있어, 전화번호 보호를 위한 법적 근거가 명확합니다.']",
      "risk_scenarios": [
        "전화번호 노출 시 스미싱(SMS 피싱) 공격 위험: 공격자가 노출된 전화번호로 사기 메시지를 전송하여 피해자를 피싱 사이트로 유도하고, 이를 통해 금융정보(계좌번호, 비밀번호 등)를 탈취한 후 불법 인출 및 재산 피해를 발생시킬 수 있습니다.",
        "전화번호 노출 시 사칭 전화 및 메신저 피싱 공격: 공격자가 노출된 전화번호를 이용하여 가짜 기관(은행, 경찰서 등)이나 지인을 사칭하는 전화 또는 메시지를 발송하고, 이를 통해 개인정보(주민등록번호, 계좌정보 등)를 탈취하여 신원 도용 및 재산 피해를 유발할 수 있습니다.",
        "전화번호 노출 시 본인 인증 우회 및 계정 탈취: 공격자가 노출된 전화번호를 통해 SMS 기반 본인 인증을 시도하고, 이를 통해 주요 온라인 서비스(이메일, SNS, 금융 서비스 등) 계정을 탈취하여 개인정보 유출, 명예 훼손, 재산 피해를 발생시킬 수 있습니다."
      ],
      "risk_scenarios_rationale": "[위험 시나리오를 생성한 근거를 설명하세요. 예: '전화번호는 SMS 기반 본인 인증에 광범위하게 사용되며, 공격자가 전화번호를 확보하면 SIM 스와핑, SMS 피싱 등 다양한 공격 경로가 열립니다. 실제 사례에서 전화번호 노출 후 계정 탈취가 빈번하게 발생하고 있어 이 위험 시나리오를 제시했습니다.']",
      "tips": [
        "스미싱 공격 방지를 위한 전화번호 최소수집 원칙 준수: 불필요한 전화번호 수집을 최소화하고, 수집 목적에 필요한 최소한의 정보만 보관하여 노출 범위를 줄임으로써 스미싱 공격의 표적이 될 가능성을 최소화합니다. 또한 전화번호 수집 시 반드시 개인정보보호법에 따른 동의 절차를 거쳐야 합니다.",
        "사칭 공격 방지를 위한 암호화 통신 채널 사용: 전화번호 등 개인정보를 외부로 전송할 경우 TLS/SSL 등 암호화된 채널을 통해 안전하게 전송하여 전송 중 전화번호가 탈취되어 사칭 공격에 악용되는 것을 방지합니다. 또한 전송 로그를 남겨 이상 징후를 조기에 발견할 수 있도록 합니다.",
        "계정 탈취 방지를 위한 접근 권한 관리 및 정기 점검: 전화번호 정보에 접근할 수 있는 직원 권한을 최소화하고(최소 권한 원칙), 정기적으로 접근 로그를 검토하여 이상 징후를 조기에 발견합니다. 또한 다단계 인증(MFA)을 적용하여 전화번호만으로는 계정 접근이 불가능하도록 보안을 강화합니다."
      ],
      "tips_rationale": "[보안 팁을 생성한 근거를 설명하세요. 예: '위에서 제시한 위험 시나리오(스미싱, 사칭, 계정 탈취)를 직접적으로 방지하기 위해 최소 수집 원칙, 암호화 통신, 접근 권한 관리 등 실무에서 즉시 적용 가능한 기술적 조치를 제시했습니다. ISO 27001, OWASP 가이드라인 등 국제 보안 표준을 참고하여 검증된 보안 조치만 포함했습니다.']"
    }},
    {{
      "category": "학교명",
      "law_summary": "개인정보보호법 제71조 제1항에 따라 개인정보처리자가 개인정보를 목적 외 이용·제공할 경우 최대 3억원의 과태료가 부과됩니다. 개인정보보호법 제75조 제1항에 따라 고의로 개인정보를 유출하거나 타인에게 제공할 경우 5년 이하의 징역 또는 5천만원 이하의 벌금에 처해집니다. 초·중등교육법 제30조의2에 따라 학생의 인적사항 등 개인정보를 보호할 의무가 있으며, 이를 위반할 경우 초·중등교육법 시행령에 따라 교육부 장관의 시정 조치를 받을 수 있습니다.",
      "risk_scenarios": [
        "학교명 노출 시 학생 신원 추적 및 표적화 위험: 학교명이 노출되면 공격자가 해당 학교의 학생 명단을 확보하거나 SNS 등에서 학교명을 검색하여 특정 학생의 신원을 식별하고, 이를 다른 개인정보(이름, 주소, 연락처 등)와 연계하여 추적 및 표적화를 수행할 수 있습니다. 이는 스토킹, 괴롭힘, 신원 도용 등으로 이어질 수 있습니다.",
        "학교명 노출 시 피싱/사칭 공격 위험: 공격자가 노출된 학교명을 이용하여 가짜 학교 공지나 행사(학부모회, 체험 학습 등)를 사칭하는 이메일이나 메시지를 발송하고, 이를 통해 학생 및 학부모의 개인정보(주민등록번호, 계좌정보 등)를 탈취하여 신원 도용 및 재산 피해를 발생시킬 수 있습니다.",
        "학교명 노출 시 집단 개인정보 침해 사고 위험: 학교명과 연계된 학생 정보가 유출되면 해당 학교의 다수 학생들의 개인정보가 한꺼번에 노출되어 집단 개인정보 침해 사고로 이어질 수 있으며, 이는 집단 소송 및 학교의 명예 훼손으로 이어질 수 있습니다."
      ],
      "tips": [
        "학생 신원 추적 방지를 위한 일반화된 표현 사용: 구체적인 학교명 대신 '지역 내 교육기관', '소속 학교' 등 일반화된 표현으로 대체하여 개인 식별 가능성을 최소화합니다. 이를 통해 학교명을 통한 학생 신원 추적 및 표적화를 방지할 수 있습니다. 또한 학교명과 다른 개인정보(이름, 주소 등)의 연계를 방지하기 위해 정보 분리 보관 정책을 수립해야 합니다.",
        "피싱 공격 방지를 위한 외부 공유 시 최소 정보 원칙: 교육기관 정보를 외부에 공유할 경우 반드시 필요한 최소한의 정보만 제공하고, 학생 개인정보와의 연계를 방지합니다. 또한 학교명을 공유할 경우 반드시 수신자 신원 확인 및 공유 목적을 명확히 하고, 공유 로그를 남겨 추적 가능하도록 합니다. 이를 통해 학교명을 이용한 가짜 공지 사칭 공격을 방지할 수 있습니다.",
        "집단 침해 사고 방지를 위한 교육기관 정보보호 정책 수립: 학교명 등 교육기관 정보의 수집·이용·제공 기준을 명확히 하고, 정기적인 보안 감사를 실시하여 정보보호 체계를 강화합니다. 또한 학생 정보에 대한 접근 권한을 최소화하고, 암호화 저장 및 전송을 적용하여 학교명과 연계된 학생 정보 유출을 방지합니다. 집단 침해 사고 발생 시 신속한 대응을 위한 사고 대응 매뉴얼을 수립해야 합니다."
      ]
    }}
  ]
}}

**요구사항:**
1. **revised_sentence (필수, 가장 중요)**: 
   - 반드시 JSON 응답의 최상위에 "revised_sentence" 필드를 포함해야 합니다.
   - 이 필드는 위에서 제공한 **마스킹된 텍스트**를 실제로 읽고 수정한 결과여야 합니다.
   - 예시 문장이나 설명 문장을 그대로 사용하지 마세요. 반드시 입력된 마스킹된 텍스트를 기반으로 새로운 수정 문장을 생성해야 합니다.
   - 모든 마스킹 태그([이름], [전화번호], [주소] 등)를 자연스러운 표현으로 대체한 완전한 문장이어야 합니다.
   - 문장의 의미와 맥락을 유지하면서 개인정보만 안전하게 일반화된 표현으로 변경해야 합니다.
   - 이 필드는 절대 생략하면 안 되며, 반드시 실제 수정된 문장이어야 합니다.
   
2. **revised_sentence_rationale (필수)**: 
   - 수정 문장을 생성한 근거를 **간결하게** (2-3문장, 100-150자 이내) 설명해야 합니다.
   - 어떤 부분을 어떻게 수정했는지, 왜 그렇게 수정했는지를 구체적으로 설명하세요.
   - 예시: "원문의 '[전화번호]'를 일반화된 표현으로 대체하여 개인정보 노출을 방지했습니다. 전화번호는 스미싱 공격의 표적이 될 수 있어 구체적인 번호 대신 일반적인 표현을 사용했습니다."
3. **발견된 모든 민감 정보 유형에 대해 각각 하나의 item을 생성해야 합니다.** 예를 들어 "전화번호", "학교명", "이름", "주소"가 발견되었다면, items 배열에 4개의 객체가 있어야 합니다.
4. **category**: 각 발견된 민감 정보 유형을 반드시 한국어로 명시하세요 (예: "전화번호", "학교명", "이름", "주소", "이메일", "주민등록번호", "계좌번호", "직장명" 등)
5. **law_summary**: 다음 형식을 **무조건** 준수하세요 (반드시 법령명과 조항/항 번호 포함)
   - **필수**: 모든 법령 인용은 반드시 "법령명 제XX조 제X항" 형식으로 시작해야 합니다
     ✅ 올바른 형식: "개인정보보호법 제71조 제1항에 따라...", "정보통신망 이용촉진 및 정보보호 등에 관한 법률 제48조의2 제1항에 따라...", "초·중등교육법 제30조의2에 따라..."
     ❌ 절대 금지: "법률에 따라", "규정에 따라", "법령에 따르면", "관련 법률에 의하면" 같은 모호한 표현
   - **필수**: 법령명은 전체 정식 명칭을 정확히 사용하세요 (약칭 절대 금지)
     ✅ 올바른 예: "개인정보보호법", "정보통신망 이용촉진 및 정보보호 등에 관한 법률", "초·중등교육법", "금융실명거래 및 비밀보장에 관한 법률"
     ❌ 잘못된 예: "개정법", "정보통신법", "교육법", "금융법" (약칭 사용 절대 금지)
   - **필수**: 조항/항 번호를 정확히 명시하세요
     ✅ 올바른 형식: "제71조 제1항", "제48조의2 제1항", "제30조의2", "제75조 제1항"
     ❌ 절대 금지: "제XX조에 따라", "관련 조항에 따라", "법령 조항에 의하면" 같은 불명확한 표현
   - **필수**: 각 법령 조항마다 구체적인 내용과 벌칙 금액을 상세히 기술하세요
     ✅ 올바른 예: "개인정보보호법 제71조 제1항에 따라 개인정보처리자가 개인정보를 목적 외 이용·제공하거나 제3자에게 제공할 경우 최대 3억원의 과태료가 부과됩니다."
     ✅ 올바른 예: "개인정보보호법 제75조 제1항에 따라 고의로 개인정보를 유출하거나 타인에게 제공할 경우 5년 이하의 징역 또는 5천만원 이하의 벌금에 처해집니다."
   - **필수**: 관련 법령이 여러 개인 경우 모두 개별적으로 인용하세요
     예시: 개인정보보호법, 정보통신망 이용촉진 및 정보보호 등에 관한 법률, 각 특별법(교육법, 금융법 등)을 모두 포함
   - **필수**: 각 법령 조항의 의미와 적용 범위, 구체적인 벌칙 내용을 명확히 구분하여 설명하세요
   - **금지**: 법령명 없이 "법률에 따라", "규정에 따라", "관련 법률에 의하면" 같은 모호한 표현 절대 금지
   - **금지**: 조항 번호 없이 "법령에 따르면", "관련 조항에 따라" 같은 일반적인 표현 절대 금지
   - **금지**: "법령에 의해", "법률 규정에 따라" 같은 불명확한 표현 절대 금지
6. **law_summary_rationale (필수)**: 
   - 법령 요약을 생성한 근거를 명확히 설명해야 합니다.
   - 어떤 법령을 왜 인용했는지, 해당 법령이 왜 이 카테고리에 적용되는지를 설명하세요.
   - 예시: "전화번호는 개인정보보호법 제2조에서 정의하는 개인정보에 해당하며, 목적 외 이용 시 제71조에 따라 과태료가 부과됩니다. 또한 정보통신망법 제48조의2에서 무단 수집 시 형사 처벌을 규정하고 있어, 전화번호 보호를 위한 법적 근거가 명확합니다."
   
7. **risk_scenarios**: 해당 카테고리의 개인정보가 노출될 시 발생할 수 있는 구체적이고 전문적인 위험 시나리오를 상세히 작성하세요
   - **필수**: 각 위험 시나리오는 반드시 해당 카테고리 정보 노출과 직접적으로 연관된 위험사항이어야 합니다
   - **필수**: 구체적인 사이버 공격 기법과 공격자의 악용 방식을 전문 용어로 상세히 기술
     예시: "스미싱(SMS 피싱)", "피싱(Phishing)", "사칭(Spoofing)", "사회공학적 공격", "본인 인증 우회", "계정 탈취", "신원 도용"
   - **필수**: 공격 단계를 명확히 구분하여 기술 (예: 정보 수집 → 표적화 → 공격 실행 → 정보 탈취 → 피해 발생)
   - **필수**: 실제 발생 가능한 구체적인 피해 내용을 전문적으로 설명
     - 재산 피해: 금액, 피해 유형(불법 인출, 계정 탈취, 피싱 사기 등)
     - 신원 도용: 대출 사기, 계정 개설, 신용카드 발급 등
     - 명예 훼손: SNS 계정 탈취를 통한 허위 게시, 개인정보 유포 등
     - 개인 추적: 스토킹, 괴롭힘, 위치 추적 등
   - **필수**: 피해 발생 시나리오를 단계별로 상세히 기술
     ✅ 올바른 형식: "[카테고리] 노출 → [구체적 공격 기법] → [공격 실행 과정] → [탈취 정보] → [구체적 피해 유형] → [실제 피해 내용]"
     예시: "전화번호 노출 → 스미싱(SMS 피싱) 공격 → 공격자가 노출된 전화번호로 사기 메시지 전송 → 피해자를 피싱 사이트로 유도 → 금융정보(계좌번호, 비밀번호 등) 탈취 → 불법 인출 및 재산 피해 발생"
   - **필수**: 각 시나리오는 최소 3-4문장으로 작성하여 공격 기법, 공격 과정, 피해 내용을 전문적으로 상세히 설명
   - **필수**: 사이버 보안 전문 용어를 적절히 사용하여 전문성을 높이세요
     예시: "APT(지속적 위협)", "사회공학적 공격", "다단계 공격", "정보 연계 추적", "표적화 공격", "집단 개인정보 침해 사고"
   - **예시 형식**: "[카테고리] 노출 시 [구체적 공격 기법] 위험: [공격 실행 과정 상세 설명]. [탈취 정보 및 악용 방식]. [구체적 피해 유형 및 실제 피해 내용]."
   
8. **risk_scenarios_rationale (필수)**: 
   - 위험 시나리오를 생성한 근거를 명확히 설명해야 합니다.
   - 왜 이 시나리오가 해당 카테고리에 적용되는지, 실제 발생 가능성이 있는지, 어떤 근거로 이 위험을 판단했는지를 설명하세요.
   - 예시: "전화번호는 SMS 기반 본인 인증에 광범위하게 사용되며, 공격자가 전화번호를 확보하면 SIM 스와핑, SMS 피싱 등 다양한 공격 경로가 열립니다. 실제 사례에서 전화번호 노출 후 계정 탈취가 빈번하게 발생하고 있어 이 위험 시나리오를 제시했습니다."
   
9. **tips**: 위의 위험 시나리오로부터 보호하기 위한 전문적이고 구체적인 보안 대응 방법을 상세히 제시하세요
   - **필수**: 각 보안 팁은 위에서 제시한 위험 시나리오를 직접적으로 방지하거나 완화하는 방법이어야 합니다
   - **필수**: 각 팁마다 구체적인 기술적 구현 방법과 보안 표준을 포함하여 실무에서 즉시 적용 가능하도록 전문적으로 작성
   - **필수**: 보안 전문 용어와 국제 보안 표준을 적절히 사용
     예시: "TLS/SSL 암호화", "접근 권한 최소화(Least Privilege Principle)", "정기 보안 감사", "다단계 인증(MFA)", "암호화 저장(AES-256)", "정보 분리 보관", "접근 로그 모니터링", "침해 사고 대응 매뉴얼", "사고 대응 플랜(Incident Response Plan)"
   - **필수**: 각 팁은 위험 시나리오와의 대응 관계를 명확히 하여 최소 3-4문장으로 전문적으로 상세히 작성
   - **필수**: 보안 팁은 실무에서 즉시 적용 가능한 구체적인 기술적 조치 방안을 제시해야 합니다
   - **필수**: 각 보안 조치의 구체적 적용 방법, 기술적 세부사항, 기대 효과를 단계별로 설명
   - **필수**: 보안 표준 및 모범 사례를 참고하여 전문적인 수준의 보안 조치를 제안하세요
     예시: "개인정보보호법 시행령에 따른 기술적·관리적 보호조치", "ISO 27001 정보보안 관리체계", "OWASP 보안 가이드라인"
   - **예시 형식**: "[구체적 보안 조치명] (보안 표준/기법): [구체적 적용 방법 및 기술적 세부사항]. [실행 절차 및 구현 방법]. [기대 효과 및 위험 완화 정도]."
   
10. **tips_rationale (필수)**: 
   - 보안 팁을 생성한 근거를 명확히 설명해야 합니다.
   - 왜 이 보안 팁이 위험 시나리오를 방지하는지, 어떤 보안 표준이나 모범 사례를 참고했는지를 설명하세요.
   - 예시: "위에서 제시한 위험 시나리오(스미싱, 사칭, 계정 탈취)를 직접적으로 방지하기 위해 최소 수집 원칙, 암호화 통신, 접근 권한 관리 등 실무에서 즉시 적용 가능한 기술적 조치를 제시했습니다. ISO 27001, OWASP 가이드라인 등 국제 보안 표준을 참고하여 검증된 보안 조치만 포함했습니다."

**중요 (반드시 준수):** 
- **가장 중요**: 반드시 JSON 응답의 최상위에 "revised_sentence" 필드를 포함해야 합니다. 이 필드가 없으면 응답이 실패합니다.
- **근거 필드 필수 (절대 생략 금지)**: 모든 AI 결과에 대해 근거(rationale) 필드를 반드시 포함해야 합니다. 이 필드들이 없으면 응답이 실패합니다. 근거는 사용자가 "왜 이런 결과가 나왔는지" 이해할 수 있도록 명확하고 구체적으로 작성해야 합니다.
  - "revised_sentence_rationale" (최상위 필수, 절대 생략 금지): 수정 문장을 생성한 근거를 반드시 포함해야 합니다. 어떤 부분을 어떻게 수정했는지, 왜 그렇게 수정했는지를 설명하세요.
  - 각 item의 "law_summary_rationale" (필수, 절대 생략 금지): 법령 요약을 생성한 근거를 반드시 포함해야 합니다. 어떤 법령을 왜 인용했는지, 해당 법령이 왜 이 카테고리에 적용되는지를 설명하세요.
  - 각 item의 "risk_scenarios_rationale" (필수, 절대 생략 금지): 위험 시나리오를 생성한 근거를 반드시 포함해야 합니다. 왜 이 시나리오가 해당 카테고리에 적용되는지, 실제 발생 가능성이 있는지, 어떤 근거로 이 위험을 판단했는지를 설명하세요.
  - 각 item의 "tips_rationale" (필수, 절대 생략 금지): 보안 팁을 생성한 근거를 반드시 포함해야 합니다. 왜 이 보안 팁이 위험 시나리오를 방지하는지, 어떤 보안 표준이나 모범 사례를 참고했는지를 설명하세요.
  
**JSON 구조 예시 (반드시 이 형식을 따라야 함):**
{{
  "revised_sentence": "수정된 문장...",
  "revised_sentence_rationale": "수정 근거 설명...",
  "items": [
    {{
      "category": "전화번호",
      "law_summary": "법령 내용...",
      "law_summary_rationale": "법령 인용 근거 설명...",
      "risk_scenarios": ["시나리오 1", "시나리오 2"],
      "risk_scenarios_rationale": "위험 시나리오 근거 설명...",
      "tips": ["팁 1", "팁 2"],
      "tips_rationale": "보안 팁 근거 설명..."
    }}
  ]
}}
- **revised_sentence는 반드시 위에서 제공한 마스킹된 텍스트를 실제로 수정한 결과여야 합니다.** 예시 문장을 복사하지 마세요. 입력된 텍스트의 마스킹된 부분을 자연스러운 표현으로 대체한 실제 수정 문장을 생성해야 합니다.
- **반드시 발견된 모든 민감 정보 유형에 대해 각각 하나의 item을 생성해야 합니다.**
- 개인정보는 절대 노출하지 마세요
- 문맥에 맞고 자연스러운 문장으로 수정하세요
- **법령 요약(law_summary) 작성 시 무조건 준수 사항:**
  * 모든 법령 인용은 반드시 "법령명 제XX조 제X항" 형식으로 시작해야 합니다
  * 법령명은 전체 정식 명칭을 정확히 사용해야 합니다 (약칭 절대 금지)
  * 조항/항 번호를 정확히 명시해야 합니다 (예: "제71조 제1항", "제48조의2 제1항")
  * 각 법령 조항마다 구체적인 내용과 벌칙 금액을 상세히 설명해야 합니다
  * 법령명 없이 "법률에 따라", "규정에 따라", "관련 법률에 의하면" 같은 모호한 표현 절대 금지
  * 조항 번호 없이 "법령에 따르면", "관련 조항에 따라" 같은 일반적인 표현 절대 금지
  * "법령에 의해", "법률 규정에 따라" 같은 불명확한 표현 절대 금지
  * ✅ 올바른 예: "개인정보보호법 제71조 제1항에 따라 개인정보처리자가 개인정보를 목적 외 이용·제공하거나 제3자에게 제공할 경우 최대 3억원의 과태료가 부과됩니다."
  * ✅ 올바른 예: "정보통신망 이용촉진 및 정보보호 등에 관한 법률 제48조의2 제1항에 따라 전화번호 등 개인정보를 무단으로 수집·이용할 경우 5년 이하의 징역 또는 5천만원 이하의 벌금에 처해질 수 있습니다."
- **위험 시나리오(risk_scenarios) 작성 시 무조건 준수:**
  * 해당 카테고리의 개인정보가 노출될 시 발생할 수 있는 구체적이고 전문적인 위험 시나리오를 상세히 작성
  * 각 위험 시나리오는 반드시 해당 카테고리 정보 노출과 직접적으로 연관된 위험사항이어야 함
  * 구체적인 사이버 공격 기법과 공격자의 악용 방식을 전문 용어로 상세히 기술 (예: 스미싱, 피싱, 사칭, 사회공학적 공격, 본인 인증 우회, 계정 탈취, 신원 도용)
  * 공격 단계를 명확히 구분하여 기술 (정보 수집 → 표적화 → 공격 실행 → 정보 탈취 → 피해 발생)
  * 실제 발생 가능한 구체적인 피해 내용을 전문적으로 설명 (재산 피해 금액 및 유형, 신원 도용 방식, 명예 훼손, 개인 추적 등)
  * 피해 발생 시나리오를 단계별로 상세히 기술 (예: "[카테고리] 노출 → [구체적 공격 기법] → [공격 실행 과정] → [탈취 정보] → [구체적 피해 유형] → [실제 피해 내용]")
  * 각 시나리오는 최소 3-4문장으로 작성하여 공격 기법, 공격 과정, 피해 내용을 전문적으로 상세히 설명
  * 사이버 보안 전문 용어를 적절히 사용하여 전문성을 높이세요 (APT, 사회공학적 공격, 다단계 공격, 정보 연계 추적, 표적화 공격 등)
  다음과 가이 위험 시나리오를 작성한 근거를 반드시 제시하시오오
- **보안 팁(tips) 작성 시 무조건 준수:**
  * 위의 위험 시나리오로부터 보호하기 위한 전문적이고 구체적인 보안 대응 방법을 상세히 제시
  * 각 보안 팁은 위에서 제시한 위험 시나리오를 직접적으로 방지하거나 완화하는 방법이어야 함
  * 각 팁마다 구체적인 기술적 구현 방법과 보안 표준을 포함하여 실무에서 즉시 적용 가능하도록 전문적으로 작성
  * 보안 전문 용어와 국제 보안 표준을 적절히 사용 (예: "TLS/SSL 암호화", "접근 권한 최소화(Least Privilege Principle)", "정기 보안 감사", "다단계 인증(MFA)", "암호화 저장(AES-256)", "정보 분리 보관", "접근 로그 모니터링", "침해 사고 대응 매뉴얼")
  * 각 팁은 위험 시나리오와의 대응 관계를 명확히 하여 최소 3-4문장으로 전문적으로 상세히 작성
  * 보안 팁은 실무에서 즉시 적용 가능한 구체적인 기술적 조치 방안을 제시해야 함
  * 각 보안 조치의 구체적 적용 방법, 기술적 세부사항, 기대 효과를 단계별로 설명
  * 보안 표준 및 모범 사례를 참고하여 전문적인 수준의 보안 조치를 제안하세요 (개인정보보호법 시행령, ISO 27001, OWASP 가이드라인 등)
  다음과 같이 보안팁을 작성한 근거를 반드시 제시하시오오
- **category는 반드시 한국어로 작성하세요**
- 한국어로 응답하세요
- JSON 형식으로만 응답하세요 (마크다운 코드 블록 없이)
"""
        
        # format()을 사용하여 변수 치환 (f-string 대신)
        prompt = prompt_template.format(
            masked_text=masked_text,
            category_list_str=category_list_str
        )
        
        return prompt

    def _call_claude_json_raw(self, prompt: str, *, max_tokens: int = 1200, use_high: bool = False) -> dict:
        """Claude API 호출하고 JSON 파싱 (2단계 파이프라인용)"""
        if not self.client:
            raise RuntimeError("Claude client not initialized")
        
        model = self.model
        
        try:
            # Claude는 system 메시지를 별도로 처리
            system_message = "반드시 JSON 형식으로만 응답하세요. 설명이나 마크다운 코드 블록 없이 순수 JSON만 반환하세요."
            
            response = self.client.messages.create(
                model=model,
                max_tokens=max_tokens,
                system=system_message,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2 if use_high else 0.3,
            )
            
            # Claude 응답은 content가 리스트 형태
            if response.content and len(response.content) > 0:
                content = response.content[0].text
            else:
                content = ""
            
            if DEBUG_LLM:
                logger.debug(f"Raw response ({model}): {content[:200]}...")
            
            # ```json 마커 제거
            content = re.sub(r'^```json\s*', '', content, flags=re.MULTILINE)
            content = re.sub(r'^```\s*$', '', content, flags=re.MULTILINE)
            content = content.strip()
            
            # JSON 추출 시도
            try:
                return json.loads(content)
            except json.JSONDecodeError as e1:
                logger.warning(f"첫 번째 JSON 파싱 시도 실패: {e1}")
                # JSON 블록 찾기 (더 관대한 패턴)
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    try:
                        json_str = json_match.group()
                        # 중괄호 밸런스 체크
                        if json_str.count('{') == json_str.count('}'):
                            return json.loads(json_str)
                        else:
                            # 불완전한 JSON이면 마지막 }까지 찾기
                            last_brace = json_str.rfind('}')
                            if last_brace > 0:
                                return json.loads(json_str[:last_brace+1])
                    except json.JSONDecodeError as e2:
                        logger.error(f"JSON 파싱 실패: {e2}")
                        if DEBUG_LLM:
                            logger.debug(f"추출된 내용: {json_match.group()[:300]}")
                        # 빈 dict 반환 (폴백)
                        return {}
                
                logger.error(f"JSON을 찾을 수 없음. 전체 응답: {content[:500]}")
                # 빈 dict 반환 (폴백)
                return {}
                
        except Exception as e:
            logger.error(f"Claude API 호출 실패 ({model}): {e}", exc_info=True)
            # 예외를 다시 발생시키지 않고 빈 dict 반환 (폴백 메커니즘)
            return {}

    def _call_claude(self, prompt: str) -> Dict[str, Any]:
        """Claude API 호출 (기존 방식, 하위 호환성 유지)"""
        if not self.client:
            raise Exception("Claude client not initialized")
            
        try:
            system_message = (
                "당신은 개인정보보호 전문가이자 사이버 보안 전문가입니다.\n\n"
                "**절대 준수 사항 (반드시 포함해야 함):**\n\n"
                "1. **JSON 형식 준수 (가장 중요)**: "
                "반드시 유효한 JSON 형식으로 응답해야 합니다. "
                "문자열 내의 따옴표는 \"로 이스케이프하고, "
                "모든 중괄호와 대괄호를 올바르게 닫아야 합니다. "
                "JSON이 잘리거나 잘못된 형식이면 응답이 실패합니다.\n\n"
                "2. **revised_sentence (필수)**: "
                "JSON 응답의 최상위에 반드시 포함. "
                "사용자가 제공한 마스킹된 텍스트를 실제로 읽고 수정한 결과여야 합니다. "
                "예시 문장을 복사하지 마세요.\n\n"
                "3. **revised_sentence_rationale (필수, 절대 생략 금지)**: "
                "JSON 응답의 최상위에 반드시 포함. "
                "수정 문장을 생성한 근거를 **간결하게** "
                "(2-3문장, 100-150자 이내) 설명하세요. "
                "이 필드가 없으면 응답이 실패합니다.\n\n"
                "4. **각 item의 rationale 필드 (필수, 절대 생략 금지)**: "
                "모든 item에 다음 필드를 반드시 포함해야 합니다:\n"
                "   - law_summary_rationale: 법령 요약 생성 근거 "
                "(2-3문장, 100-150자 이내, 간결하게)\n"
                "   - risk_scenarios_rationale: 위험 시나리오 생성 근거 "
                "(2-3문장, 100-150자 이내, 간결하게)\n"
                "   - tips_rationale: 보안 팁 생성 근거 "
                "(2-3문장, 100-150자 이내, 간결하게)\n\n"
                "**중요**: rationale 필드는 명확하고 구체적이어야 하지만, "
                "**반드시 간결하게** 작성하세요. "
                "각 rationale은 2-3문장, 100-150자 이내로 작성하여 "
                "JSON 응답이 너무 길어지지 않도록 하세요. "
                "너무 길면 JSON이 잘려서 파싱이 실패합니다. "
                "이 필드들이 없으면 응답이 실패합니다.\n\n"
                "**중요**:\n"
                "- JSON 문자열 내의 모든 따옴표는 반드시 백슬래시로 "
                "이스케이프(\\\")해야 합니다.\n"
                "- 모든 중괄호 { }와 대괄호 [ ]를 올바르게 닫아야 합니다.\n"
                "- 모든 필드 사이에 콤마(,)를 반드시 포함해야 합니다.\n"
                "- JSON 응답이 완전히 끝나야 합니다. "
                "응답이 중간에 잘리면 파싱이 실패합니다.\n"
                "- 긴 텍스트를 작성할 때도 JSON 형식 규칙을 반드시 준수하세요."
            )
            
            # Rate limit 방지를 위해 재시도 로직 추가
            max_retries = 3
            retry_delay = 2  # 초
            
            for attempt in range(max_retries):
                try:
                    response = self.client.messages.create(
                        model=self.model,
                        max_tokens=16000,  # rationale 필드 포함으로 매우 긴 응답 필요
                        system=system_message,
                        messages=[
                            {"role": "user", "content": prompt}
                        ],
                        temperature=0.2
                    )
                    break  # 성공 시 루프 탈출
                except Exception as api_error:
                    error_str = str(api_error)
                    if "429" in error_str or "Too Many Requests" in error_str:
                        if attempt < max_retries - 1:
                            wait_time = retry_delay * (attempt + 1)
                            logger.warning(f"Rate limit (429) 발생. {wait_time}초 후 재시도... ({attempt + 1}/{max_retries})")
                            import time
                            time.sleep(wait_time)
                            continue
                        else:
                            logger.error("Rate limit (429) - 최대 재시도 횟수 초과")
                            raise
                    else:
                        raise
            
            # Claude 응답은 content가 리스트 형태
            if response.content and len(response.content) > 0:
                content = response.content[0].text
            else:
                content = ""
            
            if DEBUG_LLM:
                logger.debug(f"Claude 원본 응답 (처음 1000자): {content[:1000]}...")
                logger.debug(f"Claude 원본 응답 전체 길이: {len(content)}자")
            
            # ```json 마커 제거
            content = re.sub(r'^```json\s*', '', content, flags=re.MULTILINE)
            content = re.sub(r'^```\s*$', '', content, flags=re.MULTILINE)
            content = content.strip()
            
            try:
                parsed = json.loads(content)
                if DEBUG_LLM:
                    logger.debug(f"JSON 파싱 성공. 파싱된 최상위 키: {list(parsed.keys()) if isinstance(parsed, dict) else 'None'}")
                    if isinstance(parsed, dict):
                        logger.debug("========== Claude 응답 분석 ==========")
                        logger.debug(f"파싱된 모든 키: {list(parsed.keys())}")
                        if "revised_sentence" in parsed:
                            logger.debug(f"revised_sentence 발견: {parsed['revised_sentence'][:100] if parsed['revised_sentence'] else 'None'}...")
                        else:
                            logger.warning("revised_sentence가 응답에 없습니다!")
                        if "revised_sentence_rationale" in parsed:
                            logger.debug(f"revised_sentence_rationale 발견: {parsed['revised_sentence_rationale'][:200] if parsed['revised_sentence_rationale'] else 'None'}...")
                        else:
                            logger.warning("revised_sentence_rationale가 응답에 없습니다!")
                            logger.debug(f"Claude가 생성한 모든 최상위 필드: {list(parsed.keys())}")
                        if "items" in parsed and isinstance(parsed["items"], list) and len(parsed["items"]) > 0:
                            first_item = parsed["items"][0]
                            if isinstance(first_item, dict):
                                logger.debug(f"첫 번째 item의 모든 키: {list(first_item.keys())}")
                                if "law_summary_rationale" in first_item:
                                    logger.debug("law_summary_rationale 발견")
                                else:
                                    logger.warning("law_summary_rationale 없음")
                                if "risk_scenarios_rationale" in first_item:
                                    logger.debug("risk_scenarios_rationale 발견")
                                else:
                                    logger.warning("risk_scenarios_rationale 없음")
                                if "tips_rationale" in first_item:
                                    logger.debug("tips_rationale 발견")
                                else:
                                    logger.warning("tips_rationale 없음")
                        logger.debug("========================================")
                return parsed
            except json.JSONDecodeError as e:
                logger.error(f"JSON 파싱 오류: {e}")
                error_msg = str(e)
                error_pos = getattr(e, 'pos', len(content))
                if DEBUG_LLM:
                    logger.debug(f"오류 위치: char {error_pos}")
                    logger.debug(f"파싱 시도한 내용 (오류 위치 주변 200자): ...{content[max(0, error_pos-100):error_pos+100]}...")
                
                # JSON 복구 시도
                try:
                    content_fixed = content
                    
                    # "Expecting ',' delimiter" 오류 처리
                    if "Expecting ',' delimiter" in error_msg or "Expecting delimiter" in error_msg:
                        # 오류 위치 근처에서 문제 찾기
                        # 오류 위치 앞에서 마지막 완전한 필드 끝 찾기
                        search_start = max(0, error_pos - 500)
                        search_end = min(len(content_fixed), error_pos + 100)
                        
                        # 오류 위치 앞에서 마지막 완전한 중괄호나 콤마 찾기
                        last_valid_pos = search_start
                        for i in range(error_pos, search_start, -1):
                            if content_fixed[i] in ['}', ']', ',']:
                                # 이 위치가 유효한 JSON 구조인지 확인
                                # 중괄호/대괄호 밸런스 체크
                                test_str = content_fixed[:i+1]
                                test_braces = test_str.count('{') - test_str.count('}')
                                test_brackets = test_str.count('[') - test_str.count(']')
                                
                                if test_braces == 0 and test_brackets == 0:
                                    last_valid_pos = i + 1
                                    break
                                elif content_fixed[i] == ',':
                                    last_valid_pos = i + 1
                                    break
                        
                        if last_valid_pos > search_start:
                            # 마지막 완전한 위치까지 자르고 닫기
                            content_fixed = content_fixed[:last_valid_pos]
                            
                            # 중괄호/대괄호 밸런스 맞추기
                            open_braces = content_fixed.count('{')
                            close_braces = content_fixed.count('}')
                            if open_braces > close_braces:
                                content_fixed += '}' * (open_braces - close_braces)
                            
                            open_brackets = content_fixed.count('[')
                            close_brackets = content_fixed.count(']')
                            if open_brackets > close_brackets:
                                content_fixed += ']' * (open_brackets - close_brackets)
                            
                            parsed = json.loads(content_fixed)
                            if DEBUG_LLM:
                                logger.debug("JSON 복구 후 파싱 성공! (콤마 오류 위치에서 잘림)")
                            return parsed
                    
                    # "Unterminated string" 오류 처리
                    if "Unterminated string" in error_msg:
                        # 오류 위치에서 문자열이 시작된 위치 찾기
                        # 오류 위치 앞에서 마지막 따옴표 찾기
                        string_start = content_fixed.rfind('"', 0, error_pos)
                        
                        if string_start > 0:
                            # 문자열 시작 위치에서 오류 위치까지의 텍스트 확인
                            # 이스케이프된 따옴표가 아닌 실제 문자열 끝 찾기
                            # 오류 위치 앞에서 마지막 완전한 중괄호나 콤마 찾기
                            last_valid_pos = string_start
                            
                            # 오류 위치 앞에서 역방향으로 검색
                            for i in range(error_pos - 1, string_start, -1):
                                if content_fixed[i] == '"':
                                    # 이스케이프된 따옴표인지 확인
                                    if i > 0 and content_fixed[i-1] != '\\':
                                        last_valid_pos = i
                                        break
                            
                            # 문자열이 제대로 닫히지 않았다면, 해당 필드 전체 제거
                            if last_valid_pos == string_start:
                                # 필드 시작 위치 찾기 (콜론 이전)
                                field_start = content_fixed.rfind('"', 0, string_start - 10)
                                if field_start > 0:
                                    # 콜론 찾기
                                    colon_pos = content_fixed.find(':', field_start, string_start)
                                    if colon_pos > 0:
                                        # 이 필드 전체를 제거 (이전 콤마까지)
                                        prev_comma = content_fixed.rfind(',', 0, field_start)
                                        if prev_comma > 0:
                                            content_fixed = content_fixed[:prev_comma] + content_fixed[string_start-1:]
                                        else:
                                            # 첫 번째 필드인 경우
                                            next_comma = content_fixed.find(',', string_start)
                                            if next_comma > 0:
                                                content_fixed = content_fixed[:field_start-1] + content_fixed[next_comma+1:]
                                            else:
                                                # 마지막 필드인 경우
                                                content_fixed = content_fixed[:field_start-1] + '\n}'
                            
                            # 중괄호/대괄호 밸런스 맞추기
                            open_braces = content_fixed.count('{')
                            close_braces = content_fixed.count('}')
                            if open_braces > close_braces:
                                content_fixed += '}' * (open_braces - close_braces)
                            
                            open_brackets = content_fixed.count('[')
                            close_brackets = content_fixed.count(']')
                            if open_brackets > close_brackets:
                                content_fixed += ']' * (open_brackets - close_brackets)
                            
                            parsed = json.loads(content_fixed)
                            if DEBUG_LLM:
                                logger.debug("JSON 복구 후 파싱 성공! (잘린 문자열 필드 제거)")
                            return parsed
                        else:
                            # 마지막 완전한 중괄호 찾기
                            last_valid_close = content_fixed.rfind('}', 0, error_pos)
                            if last_valid_close > 0:
                                content_fixed = content_fixed[:last_valid_close+1]
                                
                                open_braces = content_fixed.count('{')
                                close_braces = content_fixed.count('}')
                                if open_braces > close_braces:
                                    content_fixed += '}' * (open_braces - close_braces)
                                
                                open_brackets = content_fixed.count('[')
                                close_brackets = content_fixed.count(']')
                                if open_brackets > close_brackets:
                                    content_fixed += ']' * (open_brackets - close_brackets)
                                
                                parsed = json.loads(content_fixed)
                                if DEBUG_LLM:
                                    logger.debug("JSON 복구 후 파싱 성공! (잘린 문자열 제거)")
                                return parsed
                    
                    # 기본 복구: 마지막 완전한 중괄호까지 자르기
                    last_valid_close = content_fixed.rfind('}', 0, error_pos)
                    if last_valid_close > 0:
                        content_fixed = content_fixed[:last_valid_close+1]
                        
                        open_braces = content_fixed.count('{')
                        close_braces = content_fixed.count('}')
                        if open_braces > close_braces:
                            content_fixed += '}' * (open_braces - close_braces)
                        
                        open_brackets = content_fixed.count('[')
                        close_brackets = content_fixed.count(']')
                        if open_brackets > close_brackets:
                            content_fixed += ']' * (open_brackets - close_brackets)
                        
                        parsed = json.loads(content_fixed)
                        if DEBUG_LLM:
                            logger.debug("JSON 복구 후 파싱 성공! (기본 복구)")
                        return parsed
                        
                except Exception as fix_error:
                    logger.warning(f"JSON 복구 시도 실패: {fix_error}")
                
                # JSON이 아닌 경우 텍스트에서 JSON 부분만 추출 시도
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    try:
                        json_str = json_match.group()
                        # 중괄호 밸런스 체크
                        if json_str.count('{') == json_str.count('}'):
                            parsed = json.loads(json_str)
                            if DEBUG_LLM:
                                logger.debug(f"정규식으로 JSON 추출 성공. 파싱된 키: {list(parsed.keys()) if isinstance(parsed, dict) else 'None'}")
                                if isinstance(parsed, dict) and "revised_sentence" in parsed:
                                    logger.debug(f"revised_sentence 발견: {parsed['revised_sentence'][:100] if parsed['revised_sentence'] else 'None'}...")
                            return parsed
                        else:
                            # 중괄호 불균형 시 마지막 닫는 중괄호까지 잘라서 파싱
                            last_close = json_str.rfind('}')
                            if last_close > 0:
                                json_str = json_str[:last_close+1]
                                parsed = json.loads(json_str)
                                if DEBUG_LLM:
                                    logger.debug("중괄호 밸런스 수정 후 파싱 성공!")
                                return parsed
                    except json.JSONDecodeError as e2:
                        logger.error(f"정규식으로 추출한 JSON도 파싱 실패: {e2}")
                        pass
                
                # 최종 실패: 빈 dict 반환 (폴백 사용)
                logger.warning("모든 JSON 파싱 시도 실패. 빈 dict 반환하여 폴백 사용")
                return {}
            
        except Exception as e:
            logger.error(f"Claude API error: {e}", exc_info=True)
            raise Exception(f"Claude API 호출 실패: {str(e)}")


