import os
import json
import logging
from typing import Optional
from google.cloud import vision
from google.oauth2 import service_account

logger = logging.getLogger(__name__)

class OCRService:
    """Google Cloud Vision API를 사용한 OCR 서비스"""
    
    def __init__(self):
        self._client = None
        self._credentials_loaded = False
    
    @property
    def client(self) -> vision.ImageAnnotatorClient:
        """Vision API 클라이언트 (lazy loading)"""
        if self._client is None:
            self._client = self._create_client()
        return self._client
    
    def _create_client(self) -> vision.ImageAnnotatorClient:
        """Vision API 클라이언트 생성"""
        credentials_json = os.getenv('GOOGLE_CLOUD_CREDENTIALS_JSON')
        
        if not credentials_json:
            raise ValueError("GOOGLE_CLOUD_CREDENTIALS_JSON 환경변수가 설정되지 않았습니다")
        
        try:
            credentials_info = json.loads(credentials_json)
            credentials = service_account.Credentials.from_service_account_info(credentials_info)
            return vision.ImageAnnotatorClient(credentials=credentials)
        except json.JSONDecodeError:
            raise ValueError("GOOGLE_CLOUD_CREDENTIALS_JSON이 올바른 JSON 형식이 아닙니다")
        except Exception as e:
            raise ValueError(f"Google Cloud 자격증명 설정 오류: {str(e)}")
    
    def detect_text(self, file_path: str) -> Optional[str]:
        """
        이미지에서 텍스트 추출
        
        Args:
            file_path: 이미지 파일 경로
            
        Returns:
            추출된 텍스트 또는 None (텍스트가 없는 경우)
            
        Raises:
            FileNotFoundError: 파일이 존재하지 않는 경우
            ValueError: 자격증명 오류
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"파일을 찾을 수 없습니다: {file_path}")
        
        try:
            with open(file_path, "rb") as f:
                content = f.read()
            
            if not content:
                logger.warning(f"빈 파일입니다: {file_path}")
                return None
            
            image = vision.Image(content=content)
            response = self.client.text_detection(image=image)
            
            # API 오류 확인
            if response.error.message:
                logger.error(f"Vision API 오류: {response.error.message}")
                return None
            
            # 텍스트 추출
            texts = response.text_annotations
            if not texts:
                logger.info(f"텍스트가 감지되지 않음: {file_path}")
                return None
            
            extracted_text = texts[0].description.strip()
            logger.info(f"텍스트 추출 완료: {len(extracted_text)}자")
            
            return extracted_text if extracted_text else None
            
        except Exception as e:
            logger.error(f"OCR 처리 중 오류 발생: {str(e)}")
            raise