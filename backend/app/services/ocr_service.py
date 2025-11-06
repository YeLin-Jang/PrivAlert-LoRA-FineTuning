import os
import logging
import tempfile
from typing import Optional
import easyocr

logger = logging.getLogger(__name__)

class OCRService:
    """EasyOCR을 사용한 OCR 서비스"""
    
    def __init__(self):
        self._reader = None
    
    @property
    def reader(self):
        """EasyOCR 리더 (lazy loading)"""
        if self._reader is None:
            self._reader = self._create_reader()
        return self._reader
    
    def _create_reader(self):
        """EasyOCR 리더 생성 (한국어, 영어 지원)"""
        try:
            # 한국어(ko)와 영어(en) 지원
            # GPU 사용 가능 시 자동으로 GPU 사용, 없으면 CPU 사용
            reader = easyocr.Reader(['ko', 'en'], gpu=False)
            # 초기화 완료 (로그 제거)
            return reader
        except Exception as e:
            logger.error(f"EasyOCR 초기화 오류: {str(e)}")
            raise ValueError(f"EasyOCR 초기화 실패: {str(e)}")
    
    def detect_text(self, file_path: str) -> Optional[str]:
        """
        이미지에서 텍스트 추출
        
        Args:
            file_path: 이미지 파일 경로
            
        Returns:
            추출된 텍스트 또는 None (텍스트가 없는 경우)
            
        Raises:
            FileNotFoundError: 파일이 존재하지 않는 경우
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"파일을 찾을 수 없습니다: {file_path}")
        
        try:
            # EasyOCR로 텍스트 추출
            results = self.reader.readtext(file_path)
            
            if not results:
                logger.info(f"텍스트가 감지되지 않음: {file_path}")
                return None
            
            # 결과를 텍스트로 결합
            # EasyOCR 결과 형식: [(bbox, text, confidence), ...]
            extracted_lines = []
            for (bbox, text, confidence) in results:
                if text.strip():  # 빈 텍스트 제외
                    extracted_lines.append(text.strip())
            
            if not extracted_lines:
                logger.info(f"텍스트가 감지되지 않음: {file_path}")
                return None
            
            extracted_text = '\n'.join(extracted_lines)
            logger.info(f"텍스트 추출 완료: {len(extracted_text)}자")
            
            return extracted_text if extracted_text else None
            
        except Exception as e:
            logger.error(f"OCR 처리 중 오류 발생: {str(e)}")
            raise
    
    def detect_text_from_bytes(self, image_data: bytes) -> Optional[str]:
        """
        바이트 데이터에서 직접 텍스트 추출 (파일 접근 충돌 방지)
        
        Args:
            image_data: 이미지 바이트 데이터
            
        Returns:
            추출된 텍스트 또는 None (텍스트가 없는 경우)
        """
        if not image_data:
            logger.warning("빈 이미지 데이터입니다")
            return None
        
        temp_file_path = None
        try:
            # 임시 파일로 저장
            with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as temp_file:
                temp_file.write(image_data)
                temp_file_path = temp_file.name
            
            # 파일 경로를 사용하여 텍스트 추출
            return self.detect_text(temp_file_path)
            
        except Exception as e:
            logger.error(f"OCR 처리 중 오류 발생: {str(e)}")
            raise
        finally:
            # 임시 파일 삭제
            if temp_file_path and os.path.exists(temp_file_path):
                try:
                    os.remove(temp_file_path)
                except Exception as e:
                    logger.warning(f"임시 파일 삭제 실패: {e}")