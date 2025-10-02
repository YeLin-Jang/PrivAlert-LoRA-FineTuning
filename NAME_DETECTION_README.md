# 이름 탐지 및 마스킹 처리 기능

이 문서는 PrivAlert 프로젝트에 추가된 이름 탐지 및 마스킹 처리 기능에 대한 설명입니다.

## 기능 개요

- **이름 탐지**: LoRA 파인튜닝된 KLUE BERT 모델을 사용하여 한국어 텍스트에서 개인 이름을 탐지
- **이름 마스킹**: 탐지된 이름을 지정된 문자로 마스킹 처리 (조사 보존)
- **텍스트 리라이팅**: 마스킹된 텍스트를 자연스럽게 리라이팅
- **통합 처리**: 탐지, 마스킹, 리라이팅을 한 번에 처리

## 백엔드 구조

### 새로 추가된 파일들

```
backend/
├── app/
│   ├── services/
│   │   ├── name_detection_service.py      # 이름 탐지 및 마스킹 서비스
│   │   └── model_initializer.py           # 모델 초기화 서비스
│   └── routes/
│       └── name_detection_routes.py       # 이름 처리 API 라우트
```

### API 엔드포인트

- `POST /api/v1/name/detect` - 이름 탐지
- `POST /api/v1/name/mask` - 이름 마스킹
- `POST /api/v1/name/rewrite` - 텍스트 리라이팅
- `POST /api/v1/name/process` - 통합 처리
- `GET /api/v1/name/status` - 서비스 상태 확인

## 프론트엔드 구조

### 새로 추가된 파일들

```
frontend/src/
├── components/
│   ├── NameProcessingForm.tsx             # 이름 처리 컴포넌트
│   └── NameProcessingForm.css             # 스타일 파일
├── api.ts                                 # API 함수 추가
└── types.ts                               # 타입 정의 추가
```

## 설치 및 설정

### 1. 백엔드 의존성 설치

```bash
cd backend
pip install -r requirements.txt
```

### 2. 환경 변수 설정

`.env` 파일을 생성하고 다음 변수들을 설정하세요:

```env
# 이름 탐지 모델 설정
NAME_MODEL_PATH=klue/bert-base
NAME_LORA_PATH=../LoRA_DateSet/lora_model

# OpenAI API 설정 (선택사항)
OPENAI_API_KEY=your-openai-api-key-here
```

### 3. 모델 파일 준비

1. `LoRA_DateSet` 폴더에 훈련된 LoRA 모델을 저장
2. 모델 파일이 다음 경로 중 하나에 있는지 확인:
   - `LoRA_DateSet/lora_model/`
   - `LoRA_DateSet/model/`
   - `LoRA_DateSet/output/`

### 4. 서버 실행

```bash
# 백엔드 실행
cd backend
python -m flask run

# 프론트엔드 실행
cd frontend
npm run dev
```

## 사용법

### 1. 웹 인터페이스 사용

1. 브라우저에서 `http://localhost:3000` 접속
2. "이름 탐지 및 마스킹 처리" 섹션으로 이동
3. 텍스트 입력 후 원하는 기능 선택:
   - **이름 탐지**: 텍스트에서 이름만 탐지
   - **이름 마스킹**: 이름을 마스킹 처리
   - **텍스트 리라이팅**: 마스킹된 텍스트 리라이팅
   - **통합 처리**: 모든 과정을 한 번에 처리

### 2. API 직접 사용

#### 이름 탐지
```bash
curl -X POST http://localhost:5000/api/v1/name/detect \
  -H "Content-Type: application/json" \
  -d '{"text": "김철수님이 회의에 참석했습니다."}'
```

#### 이름 마스킹
```bash
curl -X POST http://localhost:5000/api/v1/name/mask \
  -H "Content-Type: application/json" \
  -d '{"text": "김철수님이 회의에 참석했습니다.", "mask_char": "*"}'
```

#### 통합 처리
```bash
curl -X POST http://localhost:5000/api/v1/name/process \
  -H "Content-Type: application/json" \
  -d '{"text": "김철수님이 회의에 참석했습니다.", "mask_char": "*", "use_openai": false}'
```

## 주요 특징

### 1. 조사 보존 마스킹
- "김철수님" → "김*님"
- "이영희씨" → "이*씨"
- "박민수군" → "박*군"

### 2. 신뢰도 기반 탐지
- 각 탐지된 이름에 대해 신뢰도 점수 제공
- 위치 정보 (시작/끝 인덱스) 제공

### 3. 유연한 마스킹 문자
- 기본값: `*`
- 사용자가 원하는 문자로 변경 가능

### 4. OpenAI 통합 (선택사항)
- OpenAI API 키가 설정된 경우 고품질 리라이팅 제공
- 설정되지 않은 경우 기본 리라이팅 사용

## 문제 해결

### 1. 모델 로딩 실패
- LoRA 모델 파일 경로 확인
- 환경 변수 `NAME_LORA_PATH` 설정 확인
- 로그에서 구체적인 오류 메시지 확인

### 2. 메모리 부족
- GPU 메모리 부족 시 CPU 모드로 자동 전환
- 배치 크기 조정 고려

### 3. API 오류
- 서비스 상태 확인: `GET /api/v1/name/status`
- 로그 파일 확인

## 성능 최적화

### 1. 모델 캐싱
- 모델은 애플리케이션 시작 시 한 번만 로드
- 요청마다 모델을 다시 로드하지 않음

### 2. GPU 가속
- CUDA가 사용 가능한 경우 자동으로 GPU 사용
- CPU 모드로도 정상 작동

### 3. 배치 처리
- 여러 텍스트를 한 번에 처리하는 기능은 향후 추가 예정

## 라이선스 및 의존성

이 기능은 다음 오픈소스 라이브러리를 사용합니다:
- Transformers (Hugging Face)
- PyTorch
- PEFT (Parameter Efficient Fine-Tuning)
- KLUE BERT

모든 라이브러리는 MIT 또는 Apache 2.0 라이선스 하에 있습니다.
