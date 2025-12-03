# 🔔 PrivAlert

**개인정보 보호 분석 시스템**

> **"SNS에 올리기 전, 한 번 더 확인하세요!"**  
> 텍스트, 이미지, 동영상에서 개인정보를 자동 탐지하고 안전하게 수정하는 웹 서비스

---

## 🌟 PrivAlert

SNS나 블로그에 올릴 글, 사진, 동영상에서 **개인정보를 자동 탐지**하는 보안 도구

### 주요 기능

- 📄 **텍스트 분석**: 전화번호, 이메일, 주소, 이름 등 자동 탐지
- 🖼️ **이미지 분석**: 
  - 얼굴/손가락 검출
  - OCR 텍스트 추출
  - 메타데이터 제거
- 🎬 **동영상 분석**: 프레임 추출 및 음성 인식
- ✏️ **수정 제안**: 개인정보를 안전하게 바꿀 수 있는 문장 제안
- 👤 **맞춤 설정**: 사용자별 필터링 규칙 설정

---

## 🚀 빠른 시작

### Docker로 실행하기 (권장)

#### 1️⃣ Docker 설치

- **Windows/Mac**: [Docker Desktop 다운로드](https://www.docker.com/products/docker-desktop)
- **Linux**: `sudo apt-get install docker.io docker-compose`

#### 2️⃣ 환경 변수 설정

프로젝트 루트에 `.env` 파일 생성:

```bash
# 필수 설정
FLASK_SECRET_KEY=32자-이상의-랜덤한-문자열
MYSQL_ROOT_PASSWORD=16자-이상의-강력한-비밀번호
MYSQL_PASSWORD=16자-이상의-강력한-비밀번호
JWT_SECRET_KEY=랜덤한-문자열
ENCRYPTION_KEY=암호화-키

# 선택 설정 (이메일 인증)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_EMAIL=your-email@gmail.com
SMTP_PASSWORD=your-app-password

# 선택 설정 (AI 기능)
ANTHROPIC_API_KEY=sk-ant-...
CLAUDE_MODEL=claude-sonnet-4-5-20250929
```

**비밀번호 생성:**
```bash
# Windows PowerShell
[Convert]::ToBase64String((1..32 | ForEach-Object { Get-Random -Minimum 0 -Maximum 256 }))

# Linux/Mac
openssl rand -base64 32

# 암호화 키
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

#### 3️⃣ 실행

```bash
docker-compose up -d --build
```

#### 4️⃣ 접속

- 🌐 **웹사이트**: http://localhost:3000
- 🔧 **API 문서**: http://localhost:5000/api-docs/

---

### 로컬에서 실행하기

```bash
# 저장소 클론
git clone https://github.com/yelin1197/PrivAlert.git
cd PrivAlert

# 백엔드 설정
cd backend
python3 -m venv venv
source venv/bin/activate  # Windows: .\venv\Scripts\activate
pip install -r requirements.txt

# 프론트엔드 설정
cd ../frontend
npm install

# 환경 변수 설정 (.env 파일 생성)

# 실행
# 터미널 1: 백엔드
cd backend && python wsgi.py

# 터미널 2: 프론트엔드
cd frontend && npm run dev
```

---

## 📌 기술 스택

- **Frontend**: React + TypeScript + Vite
- **Backend**: Flask (Python)
- **Database**: MySQL
- **AI/ML**: 
  - MediaPipe (얼굴/손가락 검출)
  - EasyOCR (텍스트 추출)
  - KoBERT (한국어 NER)
  - Claude API (수정 제안)
- **Infrastructure**: Docker, Docker Compose

---

## 📡 주요 API

- `POST /api/v1/analyze` - 통합 분석 (이미지 + 텍스트)
- `POST /api/v1/face/detect` - 얼굴 검출
- `POST /api/v1/hand/detect` - 손가락 검출
- `POST /api/v1/ocr/text` - OCR 텍스트 추출
- `POST /api/v1/filter/filter` - 텍스트 필터링
- `POST /api/v1/images/sanitize` - 이미지 메타데이터 제거
- `POST /api/v1/video/analyze` - 비디오 분석

자세한 API 문서: http://localhost:5000/api-docs/

---

## 🔒 보안

- Argon2id 비밀번호 해싱
- JWT 기반 인증
- MFA (Multi-Factor Authentication) 지원
- CSRF 보호
- Rate Limiting
- HTTPS 권장 (프로덕션 환경)

---

## 📝 참고사항

- `.env` 파일은 Git에 커밋하지 않기
- `data/` 디렉토리는 Git 제외
- 프로덕션 환경에서는 HTTPS 사용

---

## 📄 라이선스

19기 도전학기제 설계형(팀) **도전!보안벨** 프로젝트

---

## 🤝 기여

이슈나 풀 리퀘스트 환영
