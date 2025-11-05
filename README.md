# 🔔 PrivAlert

19기 도전학기제 설계형(팀) **도전!보안벨**  
사용자 맞춤 민감정보 탐지를 위한 **AI 기반 텍스트 및 이미지 점검 시스템 개발**  
Flask 기반 **위험정보(개인정보 등) 탐지 웹서비스** 프로젝트입니다.

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

## 🚀 빠른 시작 (Docker - 권장)

### 1단계: Docker 설치 확인

```bash
docker --version
docker-compose --version
```

설치되어 있지 않다면:
- **Windows/Mac**: [Docker Desktop](https://www.docker.com/products/docker-desktop) 다운로드 및 설치
- **Linux**: 
  ```bash
  sudo apt-get update
  sudo apt-get install docker.io docker-compose
  ```

### 2단계: 환경 변수 설정

```bash
# 프로젝트 루트에서 실행
# .env 파일이 없다면 생성 (필수 환경 변수 설정)
```

**⚠️ 중요**: `.env` 파일은 프로젝트 **루트**에 생성합니다!

**필수 환경 변수:**
```bash
# Flask Secret Key (최소 32자)
FLASK_SECRET_KEY=your-super-secret-key-minimum-32-characters-long-change-this

# MySQL Root 비밀번호 (최소 16자)
MYSQL_ROOT_PASSWORD=your-strong-root-password-here-minimum-16-characters

# MySQL 사용자 비밀번호 (최소 16자)
MYSQL_PASSWORD=your-strong-database-password-here-minimum-16-characters

# JWT Secret Key
JWT_SECRET_KEY=your-jwt-secret-key-different-from-flask-secret-key
```

**비밀번호 생성 (선택사항):**
```bash
# Linux/Mac
openssl rand -base64 32

# Windows PowerShell
[Convert]::ToBase64String((1..32 | ForEach-Object { Get-Random -Minimum 0 -Maximum 256 }))
```

### 3단계: Docker 실행

```bash
# 프로젝트 루트에서 실행
docker-compose up -d --build
```

**설명:**
- `--build`: 이미지가 없거나 변경사항이 있으면 자동으로 빌드
- `-d`: 백그라운드 실행
- Backend, Frontend 이미지가 자동으로 빌드됨

### 4단계: 확인

```bash
# 헬스체크
curl http://localhost:5000/health

# 브라우저에서 접속
# 프론트엔드: http://localhost:3000
# 백엔드 API: http://localhost:5000
# API 문서: http://localhost:5000/api-docs/
```

### 5단계: 기본 관리자 계정 로그인

- **사용자명**: `admin` / **비밀번호**: `admin123!`
- **사용자명**: `super_admin` / **비밀번호**: `super123!`

**⚠️ 프로덕션 환경에서는 반드시 비밀번호를 변경하세요!**

---

## 🖥️ 로컬 개발 환경 설정

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

# 환경변수 설정 (.env 파일 생성 - 프로젝트 루트에)
# .env.example을 참고하여 .env 파일 생성
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

# 환경변수 설정 (.env 파일 생성 - 프로젝트 루트에)
# .env.example을 참고하여 .env 파일 생성

# 서버 실행
python wsgi.py
```

**주의사항:**
- `python-magic`가 Windows에서 동작하지 않을 경우 `python-magic-bin` 사용을 고려하세요.
- 환경변수 설정이 필요합니다 (OpenAI API 키 등)

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

## 🐳 Docker 상세 가이드

### 프로덕션 환경 (권장)

**보안: 데이터베이스 포트 노출 없음 (Docker 내부 네트워크만)**

```bash
# 프로젝트 루트에서 실행
docker-compose up -d --build

# 로그 확인
docker-compose logs -f

# 특정 서비스 로그만 확인
docker-compose logs -f backend
docker-compose logs -f mysql
```

### 개발 환경 (외부 도구 접근 필요 시)

**⚠️ 개발 환경에서만 사용하세요!**

```bash
# MySQL Workbench, DBeaver 등 외부 도구로 접근이 필요한 경우
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build
```

### 유용한 명령어

```bash
# 모든 서비스 중지
docker-compose down

# 서비스 중지 및 볼륨 삭제 (데이터 삭제)
docker-compose down -v

# 특정 서비스 재시작
docker-compose restart backend

# 특정 서비스만 실행
docker-compose up -d mysql backend

# MySQL 접속
docker-compose exec mysql mysql -u privalert_user -p privalert

# 백엔드 컨테이너 접속
docker-compose exec backend bash

# 데이터베이스 백업
docker-compose exec mysql mysqldump -u root -p privalert > backup_$(date +%Y%m%d).sql

# 데이터베이스 복원
docker-compose exec -T mysql mysql -u root -p privalert < backup_20241104.sql
```

### Docker 이미지 빌드

#### 전체 빌드 및 실행 (권장)
```bash
docker-compose up -d --build
```

#### 개별 이미지 빌드
```bash
# Backend 이미지 빌드
cd backend
docker build -t privalert-backend:latest .

# Frontend 이미지 빌드
cd frontend
docker build --build-arg VITE_API_BASE_URL=http://localhost:5000 -t privalert-frontend:latest .
```

#### 빌드 캐시 없이 재빌드
```bash
docker-compose build --no-cache backend
docker-compose build --no-cache frontend
```

---

## 🔧 문제 해결

### MySQL 연결 실패

**증상:**
```
데이터베이스 연결 실패: (2003, "Can't connect to MySQL server")
```

**해결 방법:**
```bash
# 1. MySQL 컨테이너 상태 확인
docker-compose ps mysql

# 2. MySQL 로그 확인
docker-compose logs mysql

# 3. MySQL 재시작
docker-compose restart mysql

# 4. 환경 변수 확인
docker-compose exec mysql env | grep MYSQL
```

### 백엔드 연결 실패

**증상:**
```
헬스체크 실패 또는 데이터베이스 연결 오류
```

**해결 방법:**
```bash
# 1. 백엔드 로그 확인
docker-compose logs backend

# 2. 데이터베이스 연결 정보 확인
docker-compose exec backend env | grep MYSQL

# 3. 백엔드 재시작
docker-compose restart backend

# 4. 헬스체크 재확인
curl http://localhost:5000/health
```

### 포트 충돌

**증상:**
```
Error: bind: address already in use
```

**해결 방법:**
1. `.env` 파일에서 포트 변경:
```bash
MYSQL_PORT=3307      # 다른 포트 사용
BACKEND_PORT=5001    # 다른 포트 사용
FRONTEND_PORT=3001   # 다른 포트 사용
```

2. 또는 사용 중인 프로세스 종료:
```bash
# Windows
netstat -ano | findstr :3306
taskkill /PID <PID> /F

# Linux/Mac
lsof -i :3306
kill -9 <PID>
```

### 볼륨 권한 오류

**증상:**
```
Permission denied: /app/data
```

**해결 방법:**
```bash
# Linux에서 권한 설정
sudo chown -R $USER:$USER backend/data backend/static

# Windows/Mac에서는 일반적으로 문제 없음
```

---

## 📁 프로젝트 구조

```
PrivAlert/
├── backend/                    # 백엔드 (Flask)
│   ├── app/                    # 애플리케이션 코드
│   │   ├── extensions/         # Flask 확장 (데이터베이스 등)
│   │   ├── models/            # 데이터베이스 모델
│   │   ├── routes/            # API 라우트
│   │   ├── services/          # 비즈니스 로직
│   │   ├── utils/             # 유틸리티 함수
│   │   └── data/              # 데이터 파일 (정적)
│   ├── models/                # AI 모델 파일 (KLUE, LoRA)
│   ├── tests/                  # 테스트 파일
│   ├── Dockerfile              # Docker 이미지 빌드
│   ├── requirements.txt        # Python 의존성
│   └── wsgi.py                 # WSGI 진입점
│
├── frontend/                   # 프론트엔드 (React + TypeScript)
│   ├── src/                    # 소스 코드
│   │   ├── components/        # React 컴포넌트
│   │   ├── contexts/          # React Context
│   │   ├── hooks/              # Custom Hooks
│   │   ├── routes/             # 라우팅 설정
│   │   ├── services/           # API 서비스
│   │   ├── types/              # TypeScript 타입
│   │   └── utils/              # 유틸리티 함수
│   ├── Dockerfile              # Docker 이미지 빌드
│   ├── package.json            # Node.js 의존성
│   └── vite.config.ts          # Vite 설정
│
├── docker/                     # Docker 설정
│   ├── mysql/                  # MySQL 설정
│   │   ├── my.cnf
│   │   └── init/
│   └── nginx/                  # Nginx 설정
│       └── nginx.conf
│
├── docker-compose.yml          # Docker Compose 설정 (프로젝트 루트)
├── docker-compose.dev.yml      # 개발 환경 설정
└── README.md                   # 이 파일
```

### 파일 위치 가이드

**백엔드 작업:**
- **API 추가**: `backend/app/routes/`
- **비즈니스 로직**: `backend/app/services/`
- **모델 추가**: `backend/app/models/`
- **유틸리티**: `backend/app/utils/`

**프론트엔드 작업:**
- **컴포넌트 추가**: `frontend/src/components/`
- **API 서비스**: `frontend/src/services/`
- **타입 정의**: `frontend/src/types/`

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

#### 폼 필드
- `file`(필수): 이미지 파일
- `target_format`(선택): `jpeg|png|webp|heic`
- `keep_icc`(선택): `true|false` (기본 true)

#### 제약/보안
- 허용 포맷: JPEG/JPG, PNG, WEBP, HEIF/HEIC
- 바이트 상한: 20MB, 픽셀 상한: 50,000,000
- EXIF Orientation 반영, EXIF/GPS 및 PNG 텍스트 청크 제거
- 서버 디스크 저장 없이 메모리로 처리, 최소 로깅

#### cURL 예시
```bash
curl -X POST http://localhost:5000/api/v1/images/sanitize \
  -F "file=@/path/to/photo.jpg" \
  -F "target_format=jpeg" \
  -F "keep_icc=true" \
  -o sanitized.jpg
```

#### React(TypeScript) 예시
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

---

## 🖥️ 데이터 수집 & 분석

### 정형 데이터
- 정규표현식 기반 탐지 (전화번호, 이메일 등)

### 비정형 데이터
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

## 🔒 보안 체크리스트

실행 전 확인사항:

- [ ] `.env` 파일이 생성되었고 모든 필수 값이 설정되었는가?
- [ ] `FLASK_SECRET_KEY`가 최소 32자 이상인가?
- [ ] `MYSQL_ROOT_PASSWORD`가 강력한 비밀번호인가?
- [ ] `MYSQL_PASSWORD`가 강력한 비밀번호인가?
- [ ] `.env` 파일이 Git에 커밋되지 않았는가?
- [ ] 프로덕션 환경에서는 `docker-compose.dev.yml`을 사용하지 않는가?

---

## 📑 커밋 스타일

- **[CREATE]** : API 첫 생성, 기능 추가  
- **[UPDATE]** : 버그 및 API 수정, 추가 구현 중  
- **[REFAC]** : 오타 수정, 디렉토리 변경 등 소규모 수정  
- **[CHORE]** : 코드 변경 없는 환경설정 등 수정 (예: setup)  
- **[DOCS]** : 문서 작업  
- **[DEPLOY]** : 배포 관련 작업

---

## 📝 참고사항

### 실무 표준 준수 사항

**Docker 구조:**
- Dockerfile은 각 서비스 디렉토리에 위치
- `.dockerignore`는 각 서비스 디렉토리에 위치
- `docker/` 디렉토리는 compose와 설정만 포함

**의존성 관리:**
- Backend: `requirements.txt` 사용
- Frontend: `package.json` 사용
- 루트에 불필요한 의존성 파일 없음

**환경 변수:**
- `.env` 파일은 프로젝트 루트에 생성
- `.env` 파일은 Git 제외

**Git 제외:**
- 빌드 결과물 (`dist/`, `__pycache__/`)
- 의존성 디렉토리 (`node_modules/`, `venv/`)
- 민감 정보 (`data/`, `.env`)
- IDE 설정 (`.vscode/`, `.idea/`)

### 주의사항

1. **`.env` 파일**: 절대 Git에 커밋하지 마세요
2. **`data/` 디렉토리**: 민감한 분석 결과 포함 (Git 제외)
3. **AI 모델 파일**: 크기가 크므로 Git LFS 사용 권장
4. **빌드 결과물**: Git에 포함하지 않음
