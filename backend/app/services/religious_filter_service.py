import json
import re
import logging
from typing import Dict, List, Tuple
from pathlib import Path
import unicodedata

logger = logging.getLogger(__name__)


class ReligiousFilterService:
    """종교별 민감 단어 필터링 서비스"""
    
    def __init__(self, data_file_path: str = None, standards_path: str = None):
        """
        서비스 초기화
        
        Args:
            data_file_path: 민감 단어 데이터 파일 경로
            standards_path: 필터링 기준 파일 경로
        """
        if data_file_path is None:
            # 기본 경로 설정
            current_dir = Path(__file__).parent.parent.parent
            data_file_path = current_dir / "data" / "religious_sensitive_words.json"
        
        if standards_path is None:
            current_dir = Path(__file__).parent.parent.parent
            standards_path = current_dir / "data" / "religious_filtering_standards.json"
        
        self.data_file_path = Path(data_file_path)
        self.standards_path = Path(standards_path)
        self.sensitive_words = self._load_sensitive_words()
        self.standards = self._load_standards()
        self.compiled_patterns = self._compile_patterns()
        
        logger.info(f"로드된 종교: {list(self.sensitive_words.keys())}")
        logger.info(f"적용된 기준: {self.standards.get('standards', {}).get('legal_basis', {})}")
    
    def _load_sensitive_words(self) -> Dict:
        """민감 단어 데이터 로드"""
        try:
            with open(self.data_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            logger.info("민감 단어 데이터 로드 성공")
            return data
        except FileNotFoundError:
            logger.error(f"민감 단어 데이터 파일을 찾을 수 없습니다: {self.data_file_path}")
            return {}
        except json.JSONDecodeError as e:
            logger.error(f"민감 단어 데이터 파일 JSON 파싱 오류: {e}")
            return {}
        except Exception as e:
            logger.error(f"민감 단어 데이터 로드 중 오류 발생: {e}")
            return {}
    
    def _load_standards(self) -> Dict:
        """필터링 기준 데이터 로드"""
        try:
            with open(self.standards_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            logger.info("필터링 기준 데이터 로드 성공")
            return data
        except FileNotFoundError:
            logger.warning(f"필터링 기준 파일을 찾을 수 없습니다: {self.standards_path}")
            return {}
        except json.JSONDecodeError as e:
            logger.error(f"필터링 기준 파일 JSON 파싱 오류: {e}")
            return {}
        except Exception as e:
            logger.error(f"필터링 기준 데이터 로드 중 오류 발생: {e}")
            return {}
    
    def _compile_patterns(self) -> Dict[str, List[re.Pattern]]:
        """정규식 패턴 컴파일"""
        compiled = {}
        
        for religion, data in self.sensitive_words.items():
            if religion == "bypass_patterns":
                continue
                
            patterns = []
            
            # 키워드 패턴 (띄어쓰기, 특수문자, 숫자 등으로 우회하는 경우 감지)
            for keyword in data.get("keywords", []):
                # 기본 키워드
                patterns.append(re.compile(re.escape(keyword), re.IGNORECASE))
                
                # 띄어쓰기로 우회하는 경우
                spaced_pattern = re.escape(keyword[0]) + r'\s*' + re.escape(keyword[1:])
                patterns.append(re.compile(spaced_pattern, re.IGNORECASE))
                
                # 특수문자로 우회하는 경우
                if len(keyword) > 1:
                    special_char_pattern = r'[^\w\s]?'.join(list(keyword))
                    patterns.append(re.compile(special_char_pattern, re.IGNORECASE))
                
                # 숫자로 우회하는 경우
                if len(keyword) > 1:
                    number_pattern = r'[0-9]?'.join(list(keyword))
                    patterns.append(re.compile(number_pattern, re.IGNORECASE))
            
            # 정규식 패턴
            for pattern in data.get("patterns", []):
                try:
                    patterns.append(re.compile(pattern, re.IGNORECASE))
                except re.error as e:
                    logger.warning(f"정규식 패턴 컴파일 실패: {pattern}, 오류: {e}")
            
            compiled[religion] = patterns
        
        return compiled
    
    def _normalize_text(self, text: str) -> str:
        """텍스트 정규화 (유니코드 정규화, 공백 정리)"""
        # 유니코드 정규화
        text = unicodedata.normalize('NFC', text)
        
        # 연속된 공백을 하나로 정리
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip()
    
    def _detect_bypass_patterns(self, text: str, keyword: str) -> List[Tuple[int, int, str]]:
        """우회 패턴 감지"""
        matches = []
        
        # 띄어쓰기로 우회하는 경우
        spaced_pattern = r'\s*'.join(list(keyword))
        for match in re.finditer(spaced_pattern, text, re.IGNORECASE):
            matches.append((match.start(), match.end(), match.group()))
        
        # 특수문자로 우회하는 경우
        special_pattern = r'[^\w\s]*'.join(list(keyword))
        for match in re.finditer(special_pattern, text, re.IGNORECASE):
            matches.append((match.start(), match.end(), match.group()))
        
        # 숫자로 우회하는 경우
        number_pattern = r'[0-9]*'.join(list(keyword))
        for match in re.finditer(number_pattern, text, re.IGNORECASE):
            matches.append((match.start(), match.end(), match.group()))
        
        return matches
    
    def _get_replacement(self, religion: str, word: str) -> str:
        """대체 단어 찾기"""
        try:
            replacements = self.sensitive_words.get(religion, {}).get("replacements", {})
            return replacements.get(word, "")
        except Exception as e:
            logger.warning(f"대체 단어 찾기 실패: {religion}, {word}, 오류: {e}")
            return ""
    
    def filter_text(self, text: str, use_replacements: bool = True) -> Dict:
        """
        텍스트에서 민감 단어 필터링 및 대체 단어 제시
        
        Args:
            text: 필터링할 텍스트
            use_replacements: 대체 단어 사용 여부 (기본값: True)
            
        Returns:
            필터링 결과 딕셔너리
        """
        if not text or not isinstance(text, str):
            return {
                "success": False,
                "error": "유효하지 않은 텍스트입니다",
                "original_text": text,
                "filtered_text": text,
                "detected_words": [],
                "statistics": {}
            }
        
        # 텍스트 정규화
        normalized_text = self._normalize_text(text)
        detected_words = []
        replacement_suggestions = []  # 대체 단어 제안
        statistics = {religion: 0 for religion in self.sensitive_words.keys() if religion != "bypass_patterns"}
        
        # 각 종교별로 민감 단어 검사
        for religion, patterns in self.compiled_patterns.items():
            religion_detected = []
            
            for pattern in patterns:
                # 패턴 매칭
                for match in pattern.finditer(normalized_text):
                    start, end = match.span()
                    matched_text = match.group()
                    
                    # 중복 제거를 위해 이미 감지된 단어와 겹치는지 확인
                    is_duplicate = False
                    for existing in religion_detected:
                        if (start >= existing['start'] and start < existing['end']) or \
                           (end > existing['start'] and end <= existing['end']):
                            is_duplicate = True
                            break
                    
                    if not is_duplicate:
                        # 대체 단어 찾기
                        replacement = self._get_replacement(religion, matched_text)
                        
                        word_info = {
                            'word': matched_text,
                            'start': start,
                            'end': end,
                            'religion': religion,
                            'pattern_type': 'regex'
                        }
                        
                        if replacement and use_replacements:
                            word_info['replacement'] = replacement
                            replacement_suggestions.append({
                                'original': matched_text,
                                'replacement': replacement,
                                'position': f"{start}-{end}"
                            })
                        
                        religion_detected.append(word_info)
            
            # 키워드 직접 검색 (우회 패턴 포함)
            for keyword in self.sensitive_words.get(religion, {}).get("keywords", []):
                # 기본 키워드 검색
                if keyword.lower() in normalized_text.lower():
                    start = normalized_text.lower().find(keyword.lower())
                    end = start + len(keyword)
                    
                    # 문맥 예외 확인
                    if self._is_context_exception(normalized_text, keyword, start, end):
                        continue
                    
                    # 중복 제거
                    is_duplicate = False
                    for existing in religion_detected:
                        if (start >= existing['start'] and start < existing['end']) or \
                           (end > existing['start'] and end <= existing['end']):
                            is_duplicate = True
                            break
                    
                    if not is_duplicate:
                        # 대체 단어 찾기
                        replacement = self._get_replacement(religion, keyword)
                        
                        word_info = {
                            'word': keyword,
                            'start': start,
                            'end': end,
                            'religion': religion,
                            'pattern_type': 'keyword'
                        }
                        
                        if replacement and use_replacements:
                            word_info['replacement'] = replacement
                            replacement_suggestions.append({
                                'original': keyword,
                                'replacement': replacement,
                                'position': f"{start}-{end}"
                            })
                        
                        religion_detected.append(word_info)
                
                # 우회 패턴 검색
                bypass_matches = self._detect_bypass_patterns(normalized_text, keyword)
                for start, end, matched_text in bypass_matches:
                    # 중복 제거
                    is_duplicate = False
                    for existing in religion_detected:
                        if (start >= existing['start'] and start < existing['end']) or \
                           (end > existing['start'] and end <= existing['end']):
                            is_duplicate = True
                            break
                    
                    if not is_duplicate:
                        # 대체 단어 찾기
                        replacement = self._get_replacement(religion, matched_text)
                        
                        word_info = {
                            'word': matched_text,
                            'start': start,
                            'end': end,
                            'religion': religion,
                            'pattern_type': 'bypass'
                        }
                        
                        if replacement and use_replacements:
                            word_info['replacement'] = replacement
                            replacement_suggestions.append({
                                'original': matched_text,
                                'replacement': replacement,
                                'position': f"{start}-{end}"
                            })
                        
                        religion_detected.append(word_info)
            
            # 감지된 단어를 시작 위치 기준으로 정렬
            religion_detected.sort(key=lambda x: x['start'])
            
            # 통계 업데이트
            statistics[religion] = len(religion_detected)
            detected_words.extend(religion_detected)
        
        # 감지된 단어를 시작 위치 기준으로 정렬
        detected_words.sort(key=lambda x: x['start'])
        
        # 마스킹 적용하지 않고 원본 텍스트 유지 (프론트엔드에서 하이라이트만 적용)
        for word_info in detected_words:
            # 로깅
            logger.info(f"민감 단어 감지: '{word_info['word']}' "
                       f"(종교: {word_info['religion']}, 위치: {word_info['start']}-{word_info['end']})")
        
        # 전체 통계
        total_detected = len(detected_words)
        total_words = len(normalized_text.split())
        
        # 공식 기준 정보 추가
        compliance_info = self._get_compliance_info(detected_words)
        
        return {
            "success": True,
            "original_text": text,
            "filtered_text": text,  # 원본 텍스트 그대로 반환
            "detected_words": detected_words,
            "replacement_suggestions": replacement_suggestions,  # 대체 단어 제안
            "statistics": {
                **statistics,
                "total_detected": total_detected,
                "total_words": total_words,
                "detection_rate": round((total_detected / total_words * 100), 2) if total_words > 0 else 0
            },
            "compliance": compliance_info,
            "standards_applied": {
                "legal_basis": self.standards.get('standards', {}).get('legal_basis', {}),
                "filtering_level": self._determine_filtering_level(detected_words),
                "quality_assurance": self.standards.get('standards', {}).get('quality_assurance', {})
            }
        }
    
    def _is_context_exception(self, text: str, word: str, start: int, end: int) -> bool:
        """문맥 예외 확인"""
        # 예외 단어 목록 가져오기
        exceptions = self.sensitive_words.get('context_exceptions', {})
        non_religious_words = exceptions.get('non_religious_words', [])
        context_patterns = exceptions.get('context_patterns', [])
        
        # 1. 완전 일치하는 비종교 단어 확인
        if word in non_religious_words:
            return True
            
        # 2. 문맥 패턴 확인 (단어 주변 10글자)
        context_start = max(0, start - 10)
        context_end = min(len(text), end + 10)
        context = text[context_start:context_end]
        
        for pattern in context_patterns:
            if re.search(pattern, context, re.IGNORECASE):
                return True
                
        # 3. 비종교 관련 단어가 주변에 있는지 확인
        for non_religious in non_religious_words:
            if non_religious in context:
                return True
                
        return False
    
    def get_sensitive_words_by_religion(self, religion: str = None) -> Dict:
        """
        종교별 민감 단어 목록 조회
        
        Args:
            religion: 특정 종교 (None이면 전체)
            
        Returns:
            민감 단어 목록
        """
        if religion:
            return self.sensitive_words.get(religion, {})
        return self.sensitive_words
    
    def add_sensitive_word(self, religion: str, word: str, word_type: str = "keyword") -> bool:
        """
        민감 단어 추가
        
        Args:
            religion: 종교
            word: 추가할 단어
            word_type: 단어 타입 (keyword 또는 pattern)
            
        Returns:
            성공 여부
        """
        try:
            if religion not in self.sensitive_words:
                self.sensitive_words[religion] = {"keywords": [], "patterns": []}
            
            if word_type == "keyword":
                if word not in self.sensitive_words[religion]["keywords"]:
                    self.sensitive_words[religion]["keywords"].append(word)
            elif word_type == "pattern":
                if word not in self.sensitive_words[religion]["patterns"]:
                    self.sensitive_words[religion]["patterns"].append(word)
            
            # 패턴 재컴파일
            self.compiled_patterns = self._compile_patterns()
            
            logger.info(f"민감 단어 추가: {religion} - {word} ({word_type})")
            return True
            
        except Exception as e:
            logger.error(f"민감 단어 추가 실패: {e}")
            return False
    
    def remove_sensitive_word(self, religion: str, word: str, word_type: str = "keyword") -> bool:
        """
        민감 단어 제거
        
        Args:
            religion: 종교
            word: 제거할 단어
            word_type: 단어 타입 (keyword 또는 pattern)
            
        Returns:
            성공 여부
        """
        try:
            if religion not in self.sensitive_words:
                return False
            
            if word_type == "keyword":
                if word in self.sensitive_words[religion]["keywords"]:
                    self.sensitive_words[religion]["keywords"].remove(word)
            elif word_type == "pattern":
                if word in self.sensitive_words[religion]["patterns"]:
                    self.sensitive_words[religion]["patterns"].remove(word)
            
            # 패턴 재컴파일
            self.compiled_patterns = self._compile_patterns()
            
            logger.info(f"민감 단어 제거: {religion} - {word} ({word_type})")
            return True
            
        except Exception as e:
            logger.error(f"민감 단어 제거 실패: {e}")
            return False
    
    def _get_compliance_info(self, detected_words: List[Dict]) -> Dict:
        """준수 정보 생성"""
        if not detected_words:
            return {
                "status": "compliant",
                "message": "종교 관련 민감 내용이 발견되지 않았습니다",
                "legal_basis": "대한민국 헌법 제20조 - 종교의 자유 보장"
            }
        
        # 감지된 단어의 민감도 분석
        high_sensitivity_count = 0
        religions_affected = set()
        
        for word_info in detected_words:
            religion = word_info.get('religion', '')
            religions_affected.add(religion)
            
            # 민감도 레벨 확인
            sensitivity_levels = self.standards.get('standards', {}).get('religious_sensitivity_levels', {})
            if religion in sensitivity_levels:
                high_sensitivity_words = sensitivity_levels[religion].get('high_sensitivity', [])
                if word_info.get('word', '').lower() in [w.lower() for w in high_sensitivity_words]:
                    high_sensitivity_count += 1
        
        if high_sensitivity_count > 0:
            return {
                "status": "non_compliant",
                "message": f"고민감도 종교 관련 내용이 {high_sensitivity_count}개 발견되었습니다",
                "legal_basis": "개인정보보호법, 청소년보호법",
                "recommendation": "해당 내용의 게시를 재검토하시기 바랍니다",
                "affected_religions": list(religions_affected)
            }
        else:
            return {
                "status": "review_required",
                "message": "종교 관련 내용이 발견되었으나 맥락 검토가 필요합니다",
                "legal_basis": "대한민국 헌법 제20조 - 종교의 자유",
                "recommendation": "교육적 목적이나 문화적 맥락인지 확인하시기 바랍니다",
                "affected_religions": list(religions_affected)
            }
    
    def _determine_filtering_level(self, detected_words: List[Dict]) -> str:
        """필터링 레벨 결정"""
        if not detected_words:
            return "none"
        
        # 고민감도 키워드 확인
        high_sensitivity_count = 0
        for word_info in detected_words:
            religion = word_info.get('religion', '')
            sensitivity_levels = self.standards.get('standards', {}).get('religious_sensitivity_levels', {})
            if religion in sensitivity_levels:
                high_sensitivity_words = sensitivity_levels[religion].get('high_sensitivity', [])
                if word_info.get('word', '').lower() in [w.lower() for w in high_sensitivity_words]:
                    high_sensitivity_count += 1
        
        if high_sensitivity_count > 0:
            return "level_1_immediate_block"
        elif len(detected_words) > 0:
            return "level_2_contextual_review"
        else:
            return "level_3_educational_content"
