# 🔔 PrivAlert

19기 도전학기제 설계형(팀) **도전!보안벨**  
사용자 맞춤 민감정보 탐지를 위한 **AI 기반 텍스트 및 이미지 점검 시스템 개발**  
Flask 기반 **위험정보(개인정보 등) 탐지 웹서비스** 프로젝트입니다.  

이 문서에는 이미지 EXIF/메타데이터 제거 백엔드 엔드포인트 사용법과 Windows 설치/실행 가이드가 포함됩니다.

---

## 📌 프로젝트 개요
- 업로드된 텍스트/이미지/비디오에서 개인정보 가능성이 있는 패턴 탐지  
- 위험도 산정 및 수정 문구 제안  
- **아키텍처**: React + TypeScript (Frontend) + Flask (Backend) + AI 분석 파이프라인
- **주요 기능**: 
  - 이미지에서 얼굴/손가락 검출 (MediaPipe)
  - 텍스트에서 정형/비정형 데이터 탐지 (정규식 + AI 모델)
  - 이미지 메타데이터(EXIF) 제거
  - 비디오 분석 (프레임 추출, 오디오 추출)
  - GPT 기반 교육 콘텐츠 생성  

---

## ⚙️ 초기 세팅 방법

### 1. 저장소 클론
```bash
git clone https://github.com/yelin1197/PrivAlert.git
cd PrivAlert
```

### 2. Backend 설정 및 실행

#### Windows(CMD/PowerShell)
```cmd
cd backend
py -3.10 -m venv venv || py -3.13 -m venv venv
.\venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

# 환경변수 설정 (.env 파일 생성)
# 노션 참고하여 필요한 API 키 설정

# 서버 실행
python wsgi.py
```

#### Linux/Mac
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# 환경변수 설정
# .env 파일 생성 및 필요한 API 키 설정

# 서버 실행
python wsgi.py
```

**주의사항:**
- `python-magic`가 Windows에서 동작하지 않을 경우 `python-magic-bin` 사용을 고려하세요.
- 환경변수 설정이 필요합니다 (Google Cloud Vision API, OpenAI API 키 등)

### 3. Frontend 설정 및 실행

```bash
cd frontend
npm install
npm run dev
```

### 4. 접속 URL
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:5000
- **API 문서 (Swagger)**: http://localhost:5000/api-docs/

---

## 🖥️ 데이터 수집 & 분석

### 🔹 정형 데이터
- 정규표현식 기반 탐지 (전화번호, 이메일 등)

### 🔹 비정형 데이터
- 이름 → 웹 크롤링 데이터  
- 주소 → AI Hub 데이터셋  
- 닉네임/SNS 아이디 → 정규표현식  
- 문맥 기반 → KoBERT 등 한국어 사전학습 모델 파인튜닝  
- 개체명 인식 → spaCy / Stanza 활용  

---

## 🌀 웹사이트 개발 파이프라인
1. **전처리 레이어**  
   - 언어 식별, 토큰화, 정규식 패턴 탐지, NER 모델 실행  
2. **컨텍스트 판단 레이어**  
   - 마스킹된 텍스트를 LLM(GPT) API로 전달 → 위험 판단 및 수정 문구 생성  
3. **후처리/머지**  
   - 중복 스팬 병합, 신뢰도 가중치, 위험도 산정 및 라벨링  
4. **저장/로그**  
   - 원문은 저장하지 않고, 익명화된 분석 로그만 S3/Firebase에 저장  

---

## 📡 API 엔드포인트

### 주요 엔드포인트

#### 통합 분석
- `POST /api/v1/analyze` - 이미지와 텍스트를 통합 분석하여 민감 정보 탐지

#### 이미지 분석
- `POST /api/v1/face/detect` - 얼굴 검출
- `POST /api/v1/hand/detect` - 손가락 검출
- `POST /api/v1/ocr/text` - OCR 텍스트 추출

#### 이미지 정제
- `POST /api/v1/images/sanitize` - EXIF/메타데이터 제거 (다운로드)
- `POST /api/v1/images/sanitize:report` - 정제 리포트 (JSON)

#### 텍스트 분석
- `POST /api/v1/filter/filter` - 정형 데이터 필터링
- `POST /api/v1/name/detect` - 이름 탐지
- `POST /api/v1/name/mask` - 이름 마스킹
- `POST /api/v1/workplace/detect` - 직장명 탐지 (AI 모델)
- `POST /api/v1/workplace/mask` - 직장명 마스킹

#### 비디오 분석
- `POST /api/v1/video/analyze` - 비디오 분석 (프레임 추출, 오디오 추출)

#### 교육 콘텐츠
- `POST /api/v1/education/suggest` - GPT 기반 수정 문장 및 교육 자료 생성

#### 유틸리티
- `GET /api/v1/filter/filters` - 사용 가능한 필터 목록
- `GET /health` - 헬스체크

### 이미지 메타데이터 정제 API 상세

#### 엔드포인트
- `POST /api/v1/images/sanitize`: multipart/form-data로 `file` 업로드 → 정제된 이미지를 즉시 다운로드 응답(as_attachment)
- `POST /api/v1/images/sanitize:report`: 동일 입력 → JSON 리포트 반환

### 폼 필드
- `file`(필수): 이미지 파일
- `target_format`(선택): `jpeg|png|webp|heic`
- `keep_icc`(선택): `true|false` (기본 true)

### 제약/보안
- 허용 포맷: JPEG/JPG, PNG, WEBP, HEIF/HEIC
- 바이트 상한: 20MB, 픽셀 상한: 50,000,000
- EXIF Orientation 반영, EXIF/GPS 및 PNG 텍스트 청크 제거
- 서버 디스크 저장 없이 메모리로 처리, 최소 로깅

### cURL 예시
```bash
curl -X POST http://localhost:5000/api/v1/images/sanitize \
  -F "file=@/path/to/photo.jpg" \
  -F "target_format=jpeg" \
  -F "keep_icc=true" \
  -o sanitized.jpg
```

### React(TypeScript) 예시
```ts
async function sanitizeAndDownload(file: File, format?: "jpeg"|"png"|"webp"|"heic") {
  const fd = new FormData();
  fd.append("file", file);
  if (format) fd.append("target_format", format);
  fd.append("keep_icc", "true");
  const res = await fetch("/api/v1/images/sanitize", { method: "POST", body: fd });
  if (!res.ok) throw new Error("sanitize failed");
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `sanitized.${(format||file.type.split('/')[1]||'jpg')}`;
  a.click();
  URL.revokeObjectURL(url);
}
```

### 응답 예시
- 다운로드형: 파일 스트림
- 리포트형(JSON):
```json
{"source_format":"JPEG","target_format":"JPEG","exif_removed":true,"gps_removed":true,"size":12345}
```

### 트러블슈팅(Windows)
- `python-magic` 오류: `python-magic-bin` 대체 설치 고려
- `pillow-heif` 동작 불가: HEIC 저장이 불가할 수 있으니 `target_format=jpeg|png|webp` 사용
- 대용량 이미지 에러: 20MB/5천만 픽셀 상한에 걸릴 수 있음

## 📑 커밋 스타일
- **[CREATE]** : API 첫 생성, 기능 추가  
- **[UPDATE]** : 버그 및 API 수정, 추가 구현 중  
- **[REFAC]** : 오타 수정, 디렉토리 변경 등 소규모 수정  
- **[CHORE]** : 코드 변경 없는 환경설정 등 수정 (예: setup)  
- **[DOCS]** : 문서 작업  
- **[DEPLOY]** : 배포 관련 작업  
