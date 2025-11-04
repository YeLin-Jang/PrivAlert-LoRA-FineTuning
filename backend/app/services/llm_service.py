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
            cached_data = _CACHE[key][1]
            return {"items": cached_data.get("items", []), "revised_sentence": cached_data.get("revised_sentence"), "cached": True, "model": self.model}

        # OpenAI API 사용 가능하면 실제 호출, 아니면 폴백
        if self.client:
            try:
                prompt = self._build_prompt(masked_text, categories, language, tone)
                result = self._call_openai(prompt)
                revised_sentence = result.get("revised_sentence")
                items = result.get("items", self._fallback_items(categories, revised_sentence))
                if not revised_sentence:
                    revised_sentence = self._generate_revised_sentence(masked_text)
            except Exception as e:
                print(f"OpenAI API failed, using fallback: {e}")
                items = self._fallback_items(categories)
                revised_sentence = self._generate_revised_sentence(masked_text)
        else:
            items = self._fallback_items(categories)
            revised_sentence = self._generate_revised_sentence(masked_text)
            
        _CACHE[key] = (now, {"items": items, "revised_sentence": revised_sentence})
        return {"items": items, "revised_sentence": revised_sentence, "cached": False, "model": self.model}

    def _generate_revised_sentence(self, masked_text: str) -> str:
        """간단한 수정 문장 생성 (폴백용)"""
        # 마스킹된 부분을 일반화된 표현으로 대체
        revised = masked_text
        # [전화번호], [주소] 등 마스킹 태그를 제거하고 자연스럽게 수정
        import re
        revised = re.sub(r'\[전화번호\]', '연락처는 나중에 알려줄게', revised)
        revised = re.sub(r'\[주소\]', '주소는 따로 전달할게', revised)
        revised = re.sub(r'\[이름\]', '지인', revised)
        revised = re.sub(r'\[학교명\]|\[학교\]', '학교', revised)
        revised = re.sub(r'\[주민등록번호\]', '', revised)
        revised = re.sub(r'\[이메일\]', '이메일은 나중에 알려줄게', revised)
        revised = re.sub(r'\[직장명\]|\[직장\]', '직장', revised)
        revised = re.sub(r'\[.*?\]', '', revised)  # 나머지 마스킹 태그 제거
        revised = re.sub(r'\s+', ' ', revised).strip()  # 연속된 공백 제거
        return revised if revised else masked_text

    def _fallback_items(self, categories: dict, revised_sentence: str = None) -> List[dict]:
        items: List[dict] = []

        def add_item(category: str, law: str, risks: List[str], tips: List[str]):
            items.append({
                "category": category,
                "law_summary": law,
                "risk_scenarios": risks,
                "tips": tips,
            })

        if categories.get("email"):
            add_item(
                "email",
                "개인정보보호법상 개인 식별 정보로 분류됩니다. 무단 공개 시 과태료 등 행정처분 대상이 될 수 있습니다.",
                ["피싱/사칭으로 계정 탈취", "스팸·사기 메일 증가"],
                ["외부 전송 시 최소 공개", "수신자/열람 권한 점검", "로그 남기기"],
            )
        if categories.get("phone"):
            add_item(
                "phone",
                "전화번호는 개인 정보에 해당합니다. 무단 공개·처리는 법적 분쟁 소지가 있습니다.",
                ["스미싱 유도", "사칭 전화/메신저 피싱"],
                ["필요 시 임시번호/가상번호 사용", "대외 공유 금지"],
            )
        if categories.get("rrn"):
            add_item(
                "rrn",
                "주민등록번호는 원칙적 처리 금지(예외적 허용). 위반 시 과태료/과징금 부과 대상입니다.",
                ["신원 도용", "대출/계정 개설 악용"],
                ["대체키 사용", "법적 근거·보관기간 명시"],
            )
        if categories.get("account"):
            add_item(
                "account",
                "계좌번호는 금융정보로서 보호 대상입니다. 부주의 공개는 법적 책임을 유발할 수 있습니다.",
                ["보이스피싱 연계", "불법 이체 시도"],
                ["송금 시 별도 안전 채널 사용", "계좌 별칭/토큰화 활용"],
            )
        if categories.get("passport"):
            add_item(
                "passport",
                "여권번호는 고유식별정보입니다. 공개 시 신원 도용 위험이 큽니다.",
                ["국제 사기/티켓 발권 악용"],
                ["문서 공유 전 메타데이터/이미지 EXIF 제거", "필요 최소 인원에게만 공유"],
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
                "학교명은 개인정보보호법상 개인을 식별할 수 있는 정보입니다. 무단 공개 시 과태료가 부과될 수 있습니다.",
                ["학생 신원 추적", "피싱/사칭 공격", "학원 정보 노출"],
                ["학교명 대신 일반적 표현 사용", "외부 공유 시 최소 정보만 제공", "교육기관 정보 보호"],
            )
        if categories.get("name"):
            add_item(
                "name",
                "이름은 개인정보보호법 제71조에 따라 개인 식별 정보로 분류됩니다. 무단 공개 시 최대 3억원의 과태료가 부과될 수 있습니다.",
                ["신원 도용", "피싱/사칭 공격", "개인 추적"],
                ["이름 대신 일반적 표현 사용", "필요 시 성만 사용", "외부 공유 시 최소 정보만 제공"],
            )
        if categories.get("address"):
            add_item(
                "address",
                "주소는 개인정보보호법상 개인 식별 정보로 분류됩니다. 무단 공개 시 과태료가 부과될 수 있습니다.",
                ["신원 도용 및 추적", "스토킹/괴롭힘", "불법 접근 시도"],
                ["주소 대신 일반적 지역명만 사용", "상세 주소는 개인적으로 전달", "외부 공유 시 최소 정보만 제공"],
            )
        if categories.get("workplace"):
            add_item(
                "workplace",
                "직장명은 개인정보보호법상 개인을 식별할 수 있는 정보입니다. 무단 공개 시 과태료가 부과될 수 있습니다.",
                ["직장 추적", "피싱/사칭 공격", "개인정보 유출"],
                ["직장명 대신 일반적 표현 사용", "외부 공유 시 최소 정보만 제공", "회사 정보 보호"],
            )
        return items or [{
            "category": "general",
            "law_summary": "민감 정보 최소 수집·최소 공개 원칙을 준수하세요.",
            "risk_scenarios": ["사칭/피싱 위험", "개인정보 유출에 따른 법적 분쟁"],
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

{{
  "revised_sentence": "전체 마스킹된 텍스트를 자연스럽고 안전한 문장으로 수정한 결과입니다. 모든 개인정보를 일반화된 표현으로 대체했습니다.",
  "items": [
    {{
      "category": "전화번호",
      "law_summary": "개인정보보호법 제71조에 따라 개인정보를 무단으로 처리하거나 제3자에게 제공할 경우 최대 3억원의 과태료가 부과될 수 있습니다. 또한 개인정보보호법 제75조에 따라 5년 이하의 징역 또는 5천만원 이하의 벌금에 처해질 수 있습니다.",
      "risk_scenarios": [
        "스미싱 및 피싱 공격",
        "사칭 전화 및 메신저 피싱",
        "개인정보 유출로 인한 신원 도용 위험"
      ],
      "tips": [
        "개인정보 공유 시 최소한의 정보만 제공",
        "외부 전송 시 암호화된 채널 사용",
        "수신자 권한을 정기적으로 점검"
      ]
    }},
    {{
      "category": "학교명",
      "law_summary": "개인정보보호법 제71조에 따라 개인정보를 무단으로 처리하거나 제3자에게 제공할 경우 최대 3억원의 과태료가 부과될 수 있습니다.",
      "risk_scenarios": [
        "학생 신원 추적",
        "피싱/사칭 공격",
        "학원 정보 노출"
      ],
      "tips": [
        "학교명 대신 일반적 표현 사용",
        "외부 공유 시 최소 정보만 제공",
        "교육기관 정보 보호"
      ]
    }}
  ]
}}

**요구사항:**
1. **revised_sentence**: 최상위에 전체 마스킹된 텍스트를 자연스럽고 안전한 문장으로 수정한 결과를 하나만 제공하세요. 모든 개인정보를 일반화된 표현으로 대체한 완전한 문장이어야 합니다.
2. **발견된 모든 민감 정보 유형에 대해 각각 하나의 item을 생성해야 합니다.** 예를 들어 "전화번호", "학교명", "이름", "주소"가 발견되었다면, items 배열에 4개의 객체가 있어야 합니다.
3. **law_summary**: 구체적인 법령 조항과 벌칙 금액 포함
4. **risk_scenarios**: 실제 발생 가능한 구체적인 위험 상황 3가지
5. **tips**: 실무에서 바로 적용 가능한 보안 가이드라인 3가지
6. **category**: 각 발견된 민감 정보 유형을 한국어로 명시 (예: "전화번호", "학교명", "이름", "주소", "이메일", "주민등록번호" 등)

**중요:** 
- **반드시 발견된 모든 민감 정보 유형에 대해 각각 하나의 item을 생성해야 합니다.**
- 개인정보는 절대 노출하지 마세요
- 문맥에 맞고 자연스러운 문장으로 수정하세요
- 법적 근거는 정확한 조항과 벌칙 금액을 포함하세요
- 한국어로 응답하세요
- JSON 형식으로만 응답하세요 (마크다운 코드 블록 없이)
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
                        - 발견된 모든 민감 정보 유형에 대해 각각 하나의 item을 생성해야 합니다
                        - 정확한 JSON 형식을 유지하세요 (마크다운 코드 블록 없이)
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
            import re
            # ```json 마커 제거
            content = re.sub(r'^```json\s*', '', content, flags=re.MULTILINE)
            content = re.sub(r'^```\s*$', '', content, flags=re.MULTILINE)
            content = content.strip()
            
            try:
                return json.loads(content)
            except json.JSONDecodeError as e:
                print(f"JSON 파싱 오류: {e}")
                # JSON이 아닌 경우 텍스트에서 JSON 부분만 추출 시도
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    try:
                        return json.loads(json_match.group())
                    except json.JSONDecodeError:
                        pass
                raise Exception("유효한 JSON 응답을 받지 못했습니다.")
            
        except Exception as e:
            print(f"OpenAI API error: {e}")
            raise Exception(f"OpenAI API 호출 실패: {str(e)}")


