# PrivAlert (Flask 기반 위험정보 탐지)

아직 코드는 없습니다. 초기 환경/설정만 포함합니다.

## 목표
- 업로드 텍스트/이미지 내 위험정보 탐지
- 위험도 산정 및 수정 문구 제안
- Flask 백엔드 + (추후) React 프런트

## 로컬 환경 (선택 사항)
- Miniconda/Anaconda
- Python 3.10

## 설치 (Conda)
```bash
conda env create -f environment.yml
conda activate privalert
# (선택) pip 사용 시: pip install -r requirements.txt
```

## 환경 변수
`.env` 파일 생성(커밋 금지). 예시는 `.env.example` 참고.

필수:
- `OPENAI_API_KEY=`

선택:
- `FLASK_ENV=development`
- `FLASK_RUN_PORT=5000`

## 라이선스
MIT (LICENSE 참조)
