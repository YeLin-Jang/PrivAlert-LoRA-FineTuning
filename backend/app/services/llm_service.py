import os
import json
import hashlib
import time
from typing import Any, Dict, List

# 간단 메모리 캐시 (재시도/요금 절약)
_CACHE: Dict[str, tuple[float, Any]] = {}


class LLMService:
    """LLM 기반 교육/수정 제안 서비스 (OpenAI 키 없으면 폴백)"""

    def __init__(self) -> None:
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        
        # OpenAI 클라이언트 초기화 (키가 있을 때만)
        if self.api_key:
            try:
                from openai import OpenAI
                self.client = OpenAI(api_key=self.api_key)
            except ImportError:
                print("Warning: openai package not installed. Install with: pip install openai")
                self.client = None
        else:
            self.client = None

    def _cache_key(self, masked_text: str, categories: dict, language: str, tone: str) -> str:
        raw = json.dumps({
            "masked_text": masked_text,
            "categories": categories,
            "language": language,
            "tone": tone,
        }, ensure_ascii=False, sort_keys=True)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def suggest(self, masked_text: str, categories: dict, language: str = "ko", tone: str = "educational") -> dict:
        key = self._cache_key(masked_text, categories, language, tone)
        now = time.time()
        if key in _CACHE and now - _CACHE[key][0] < 86400:
            return {"items": _CACHE[key][1], "cached": True, "model": self.model}

        # OpenAI API 사용 가능하면 실제 호출, 아니면 폴백
        if self.client:
            try:
                prompt = self._build_prompt(masked_text, categories, language, tone)
                result = self._call_openai(prompt)
                items = result.get("items", self._fallback_items(categories))
            except Exception as e:
                print(f"OpenAI API failed, using fallback: {e}")
                items = self._fallback_items(categories)
        else:
            items = self._fallback_items(categories)
            
        _CACHE[key] = (now, items)
        return {"items": items, "cached": False, "model": self.model}

    def _fallback_items(self, categories: dict) -> List[dict]:
        items: List[dict] = []

        def add_item(category: str, law: str, risks: List[str], revised: str, tips: List[str]):
            items.append({
                "category": category,
                "law_summary": law,
                "risk_scenarios": risks,
                "revised_sentence": revised,
                "tips": tips,
            })

        if categories.get("email"):
            add_item(
                "email",
                "개인정보보호법상 개인 식별 정보로 분류됩니다. 무단 공개 시 과태료 등 행정처분 대상이 될 수 있습니다.",
                ["피싱/사칭으로 계정 탈취", "스팸·사기 메일 증가"],
                "이메일은 일부 마스킹하여 공유하세요: user****@domain.com",
                ["외부 전송 시 최소 공개", "수신자/열람 권한 점검", "로그 남기기"],
            )
        if categories.get("phone"):
            add_item(
                "phone",
                "전화번호는 개인 정보에 해당합니다. 무단 공개·처리는 법적 분쟁 소지가 있습니다.",
                ["스미싱 유도", "사칭 전화/메신저 피싱"],
                "전화번호는 뒤 4자리를 가린 형태로 공유하세요: 010-1234-****",
                ["필요 시 임시번호/가상번호 사용", "대외 공유 금지"],
            )
        if categories.get("rrn"):
            add_item(
                "rrn",
                "주민등록번호는 원칙적 처리 금지(예외적 허용). 위반 시 과태료/과징금 부과 대상입니다.",
                ["신원 도용", "대출/계정 개설 악용"],
                "주민등록번호는 수집/공유하지 마세요. 불가피하다면 전면 마스킹 처리",
                ["대체키 사용", "법적 근거·보관기간 명시"],
            )
        if categories.get("account"):
            add_item(
                "account",
                "계좌번호는 금융정보로서 보호 대상입니다. 부주의 공개는 법적 책임을 유발할 수 있습니다.",
                ["보이스피싱 연계", "불법 이체 시도"],
                "계좌번호는 일부만 노출하세요: 110-****-****",
                ["송금 시 별도 안전 채널 사용", "계좌 별칭/토큰화 활용"],
            )
        if categories.get("passport"):
            add_item(
                "passport",
                "여권번호는 고유식별정보입니다. 공개 시 신원 도용 위험이 큽니다.",
                ["국제 사기/티켓 발권 악용"],
                "여권번호는 절대 공개하지 마세요(필요 시 전면 마스킹)",
                ["문서 공유 전 메타데이터/이미지 EXIF 제거", "필요 최소 인원에게만 공유"],
            )
        if categories.get("ip_address"):
            add_item(
                "ip_address",
                "IP 주소는 개인 위치/행태 추정에 악용될 수 있어 보호 필요합니다.",
                ["지리적 위치 추정", "서비스 공격 표적화"],
                "IP는 일부 마스킹 또는 해시화해 공유하세요: 192.168.***.***",
                ["로그 공유 시 기간·범위 최소화", "내부 접근 통제"],
            )
        return items or [{
            "category": "general",
            "law_summary": "민감 정보 최소 수집·최소 공개 원칙을 준수하세요.",
            "risk_scenarios": ["사칭/피싱 위험", "개인정보 유출에 따른 법적 분쟁"],
            "revised_sentence": "민감 내용을 전부 마스킹하고, 필요한 요지만 전달하세요.",
            "tips": ["목적 적합성 재검토", "필요 최소한만 공유"]
        }]

    def _build_prompt(self, masked_text: str, categories: dict, language: str, tone: str) -> str:
        """프롬프트 생성"""
        category_list = list(categories.keys())
        
        prompt = f"""
당신은 개인정보보호 전문가이자 문장을 자연스럽게 다듬는 보조자입니다. 다음 마스킹된 텍스트를 분석하여 안전하고 자연스러운 문장으로 수정하고, 관련 교육 내용을 제공해주세요.

**마스킹된 텍스트:**
{masked_text}

**발견된 민감 정보 유형:** {', '.join(category_list)}

## 수정 문장 가이드라인
다음과 같은 방식으로 자연스럽게 수정해주세요:

**예시:**
- 원문: "오늘 [이름] 씨와 점심을 먹었다." → 수정: "오늘 지인과 점심을 함께했다."
- 원문: "내 연락처는 [전화번호]야, 나중에 연락해." → 수정: "내 연락처는 나중에 알려줄게, 필요할 때 연락해."
- 원문: "내 주민등록번호는 [주민등록번호]이야." → 수정: "내 신원은 공식 문서로 확인 가능해."
- 원문: "[주소]에 택배 보내줄래?" → 수정: "내 집으로 택배를 보내줄래? 주소는 개인적으로 알려줄게."
- 원문: "[계좌번호]로 돈 보내주면 돼." → 수정: "내 계좌로 송금해주면 돼. 계좌 정보는 따로 전달할게."

**수정 원칙:**
1. 마스킹된 개인정보는 그대로 노출하지 말고, 자연스럽게 일반화된 표현으로 수정
2. 문장의 의미가 크게 달라지지 않도록 유지
3. 일상 대화체라면 일상스럽게, 기사체라면 기사 어투를 유지
4. 개인정보는 "나중에 알려줄게", "따로 전달할게", "개인적으로 알려줄게" 등으로 대체

다음 형식의 JSON 응답을 생성해주세요:

{{
  "items": [
    {{
      "category": "이메일",
      "law_summary": "개인정보보호법 제71조에 따라 개인정보를 무단으로 처리하거나 제3자에게 제공할 경우 최대 3억원의 과태료가 부과될 수 있습니다. 또한 개인정보보호법 제75조에 따라 5년 이하의 징역 또는 5천만원 이하의 벌금에 처해질 수 있습니다.",
      "risk_scenarios": [
        "피싱 메일을 통한 계정 탈취 시도",
        "스팸 메일 및 사기 메일 증가",
        "개인정보 유출로 인한 신원 도용 위험"
      ],
      "revised_sentence": "연락처: [개인정보는 보호되어 마스킹 처리됨]",
      "tips": [
        "개인정보 공유 시 최소한의 정보만 제공",
        "외부 전송 시 암호화된 채널 사용",
        "수신자 권한을 정기적으로 점검"
      ]
    }}
  ]
}}

**요구사항:**
1. **revised_sentence**: 위 예시처럼 자연스럽고 안전한 표현으로 수정 (개인정보 노출 없이)
2. **law_summary**: 구체적인 법령 조항과 벌칙 금액 포함
3. **risk_scenarios**: 실제 발생 가능한 구체적인 위험 상황 3가지
4. **tips**: 실무에서 바로 적용 가능한 보안 가이드라인 3가지

**중요:** 
- 개인정보는 절대 노출하지 마세요
- 문맥에 맞고 자연스러운 문장으로 수정하세요
- 법적 근거는 정확한 조항과 벌칙 금액을 포함하세요
- 한국어로 응답하세요
"""
        return prompt

    def _call_openai(self, prompt: str) -> Dict[str, Any]:
        """OpenAI API 호출 (실제 구현)"""
        if not self.client:
            raise Exception("OpenAI client not initialized")
            
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system", 
                        "content": """당신은 개인정보보호 전문가입니다. 
                        - 마스킹된 텍스트를 자연스럽고 안전한 문장으로 수정하세요
                        - 개인정보는 절대 노출하지 마세요
                        - 정확한 JSON 형식을 유지하세요
                        - 한국어로 응답하세요"""
                    },
                    {"role": "user", "content": prompt}
                ],
                max_tokens=3000,
                temperature=0.3  # 더 일관된 응답을 위해 낮춤
            )
            
            content = response.choices[0].message.content
            print(f"GPT 응답: {content[:200]}...")  # 디버깅용
            
            # JSON 파싱 시도
            try:
                return json.loads(content)
            except json.JSONDecodeError as e:
                print(f"JSON 파싱 오류: {e}")
                # JSON이 아닌 경우 텍스트에서 JSON 부분만 추출 시도
                import re
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group())
                else:
                    raise Exception("유효한 JSON 응답을 받지 못했습니다.")
            
        except Exception as e:
            print(f"OpenAI API error: {e}")
            raise Exception(f"OpenAI API 호출 실패: {str(e)}")


