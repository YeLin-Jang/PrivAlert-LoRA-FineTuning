# 🔔 PrivAlert

**당신의 개인정보 보호 분석 시스템**

> **"SNS에 올리기 전, 한 번 더 확인하세요!"**  
> PrivAlert는 AI 기술을 활용하여 텍스트, 이미지, 동영상에서 개인정보를 자동으로 찾아주고, 안전하게 수정할 수 있도록 도와주는 웹 서비스입니다.

---

## 🌟 PrivAlert가 뭔가요?

**PrivAlert**는 여러분이 SNS나 블로그에 올리려는 글, 사진, 동영상에 **개인정보가 숨어있는지** 자동으로 찾아주는 똑똑한 보안 도우미입니다! 

### 왜 필요한가요? 🤔

- 📸 **사진 속 개인정보**: 사진에 담긴 전화번호, 주소, 이름 등을 자동으로 찾아드립니다
- 📝 **글 속 민감 정보**: 이메일, 전화번호, 주소, 직장명 등이 포함되어 있는지 확인합니다
- 🎥 **동영상 분석**: 동영상 속 대화나 자막에서 개인정보를 추출합니다
- 🔒 **안전한 공유**: 개인정보가 노출되기 전에 미리 알려드려 안전하게 공유할 수 있습니다

### 주요 기능 ✨

1. **📄 텍스트 분석**: 입력한 텍스트에서 전화번호, 이메일, 주소, 이름 등을 자동 탐지
2. **🖼️ 이미지 분석**: 
   - 사진 속 얼굴과 손가락 검출
   - 이미지 속 텍스트 추출 (OCR)
   - 위치 정보 등 메타데이터 제거
3. **🎬 동영상 분석**: 동영상에서 프레임 추출 및 음성 인식
4. **✏️ 수정 제안**: AI가 개인정보를 안전하게 바꿀 수 있는 문장을 제안해드립니다
5. **👤 사용자 맞춤 설정**: 본인만의 필터링 규칙을 설정하여 더 정확한 탐지 가능

---

## 🚀 3분 안에 시작하기

### 방법 1: Docker로 실행하기 (가장 쉬운 방법! ⭐)

**Docker가 뭔가요?**  
Docker는 프로그램을 실행하는 데 필요한 모든 것을 하나로 묶어서, 복잡한 설정 없이 바로 실행할 수 있게 해주는 도구입니다. 마치 "포장된 상자"를 열기만 하면 되는 것처럼요!

#### 1️⃣ Docker 설치하기

- **Windows/Mac**: [Docker Desktop 다운로드](https://www.docker.com/products/docker-desktop) 후 설치
- **Linux**: 
  ```bash
  sudo apt-get update
  sudo apt-get install docker.io docker-compose
  ```

설치 확인:
```bash
docker --version
docker-compose --version
```

#### 2️⃣ 환경 설정 파일 만들기

프로젝트 폴더(`PrivAlert`) 안에 `.env` 파일을 만들고 아래 내용을 복사하세요:

```bash
# 필수 설정 (반드시 변경하세요!)
FLASK_SECRET_KEY=여기에-32자-이상의-랜덤한-문자열을-입력하세요
MYSQL_ROOT_PASSWORD=데이터베이스-루트-비밀번호-16자-이상
MYSQL_PASSWORD=데이터베이스-사용자-비밀번호-16자-이상
JWT_SECRET_KEY=JWT-비밀키-다른-랜덤-문자열
ENCRYPTION_KEY=암호화-키-생성-필요

# 선택 설정 (이메일 인증을 사용하려면)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_EMAIL=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM=noreply@privalert.com

# 선택 설정 (AI 수정 제안 기능을 사용하려면)
ANTHROPIC_API_KEY=sk-ant-...
CLAUDE_MODEL=claude-sonnet-4-5-20250929
```

**💡 비밀번호 생성 팁:**
- Windows PowerShell에서:
  ```powershell
  [Convert]::ToBase64String((1..32 | ForEach-Object { Get-Random -Minimum 0 -Maximum 256 }))
  ```
- Linux/Mac에서:
  ```bash
  openssl rand -base64 32
  ```

**💡 암호화 키 생성:**
```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

#### 3️⃣ 실행하기

프로젝트 폴더에서 아래 명령어를 실행하세요:

```bash
docker-compose up -d --build
```

**이 명령어가 하는 일:**
- `docker-compose up`: 모든 서비스를 시작합니다
- `-d`: 백그라운드에서 실행합니다 (터미널을 닫아도 계속 실행됨)
- `--build`: 필요한 이미지를 자동으로 빌드합니다

#### 4️⃣ 접속하기

잠시 기다린 후 (약 1-2분), 브라우저에서 접속하세요:

- 🌐 **웹사이트**: http://localhost:3000
- 🔧 **API 문서**: http://localhost:5000/api-docs/
- ❤️ **서버 상태 확인**: http://localhost:5000/health

**🎉 완료!** 이제 PrivAlert를 사용할 수 있습니다!

---

### 방법 2: 로컬에서 직접 실행하기 (개발자용)

Docker 없이 직접 실행하고 싶다면 아래 방법을 따라하세요.

#### 1️⃣ 저장소 다운로드

```bash
git clone https://github.com/yelin1197/PrivAlert.git
cd PrivAlert
```

#### 2️⃣ 백엔드 설정

**Windows:**
```cmd
cd backend
py -3.10 -m venv venv
.\venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

**Linux/Mac:**
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

#### 3️⃣ 프론트엔드 설정

```bash
cd frontend
npm install
```

#### 4️⃣ 환경 변수 설정

프로젝트 루트에 `.env` 파일을 만들고 위의 "방법 1"에서 설명한 내용을 입력하세요.

#### 5️⃣ 실행하기

**백엔드 실행:**
```bash
cd backend
python wsgi.py
```

**프론트엔드 실행 (새 터미널):**
```bash
cd frontend
npm run dev
```

#### 6️⃣ 접속하기

- 🌐 **웹사이트**: http://localhost:3000 (또는 http://localhost:5173)
- 🔧 **API**: http://localhost:5000

---

## 📌 프로젝트 개요 (상세)

- 업로드된 텍스트/이미지/비디오에서 개인정보 가능성이 있는 패턴 탐지  
- 위험도 산정 및 수정 문구 제안  
- **아키텍처**: React + TypeScript (Frontend) + Flask (Backend) + AI 분석 파이프라인
- **주요 기능**: 
  - 이미지에서 얼굴/손가락 검출 (MediaPipe)
  - 텍스트에서 정형/비정형 데이터 탐지 (정규식 + AI 모델)
  - 이미지 메타데이터(EXIF) 제거
  - 비디오 분석 (프레임 추출, 오디오 추출)
  - Claude API 기반 교육 콘텐츠 생성
  - SMTP 이메일 인증 시스템
  - 사용자 맞춤 필터링 설정 (DB 저장 및 자동 적용)
  - 관리자 페이지 (사용자 관리, 로그 조회)

---

## 🚀 빠른 시작 (Docker - 상세 가이드)

> 💡 **위의 "3분 안에 시작하기" 섹션을 먼저 확인하세요!**  
> 아래는 더 자세한 설명과 문제 해결 방법입니다.

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

# 암호화 키 (토큰 메타데이터 암호화용)
# Fernet 키 생성: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
ENCRYPTION_KEY=your-fernet-key-here
```

**선택 환경 변수 (이메일 인증 및 프롬프팅):**
```bash
# SMTP 설정 (이메일 인증)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_EMAIL=your-email@gmail.com
SMTP_PASSWORD=your-app-password  # Gmail: 앱 비밀번호
SMTP_FROM=noreply@privalert.com

# Claude API (프롬프팅 - 선택사항)
ANTHROPIC_API_KEY=sk-ant-...
CLAUDE_MODEL=claude-sonnet-4-5-20250929
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

**코드 변경 시:**
- **Backend 코드 변경**: 볼륨 마운트로 자동 반영 (재시작만 필요)
  ```bash
  docker-compose restart backend
  ```
- **Frontend 코드 변경**: 재빌드 필요
  ```bash
  docker-compose down
  docker-compose build frontend
  docker-compose up -d
  ```
- **Dockerfile 변경**: 해당 서비스 재빌드 필요
  ```bash
  docker-compose build --no-cache <service-name>
  docker-compose up -d
  ```

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

**관리자 페이지 접속**: `http://localhost:3000/admin/login`

- **사용자명**: `.env` 파일의 `DEFAULT_ADMIN_USERNAME` (기본값: `admin`)
- **비밀번호**: `.env` 파일의 `DEFAULT_ADMIN_PASSWORD`

**⚠️ 프로덕션 환경에서는 반드시 비밀번호를 변경하세요!**

**참고**: 일반 사용자는 관리자 페이지에 접근할 수 없습니다. 관리자 페이지는 별도 인증 시스템(JWT)을 사용합니다.

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

### 보안: MySQL 포트 외부 노출 없음

이 프로젝트는 **보안을 위해 MySQL 포트를 외부에 노출하지 않습니다**. Docker 내부 네트워크에서만 MySQL에 접근할 수 있습니다.

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

### 접속 확인

#### 브라우저에서 확인
- **프론트엔드**: http://localhost:3000 (또는 `FRONTEND_PORT`에 설정된 포트)
- **백엔드 API**: http://localhost:5000 (또는 `BACKEND_PORT`에 설정된 포트)
- **API 문서 (Swagger)**: http://localhost:5000/api-docs/

#### Docker 로그로 확인
```bash
# 모든 서비스 로그
docker-compose logs -f

# 백엔드 로그만 (실시간)
docker-compose logs -f backend

# MySQL 로그만
docker-compose logs -f mysql

# 최근 100줄 로그
docker-compose logs --tail=100 backend
```

#### 컨테이너 상태 확인
```bash
# 모든 컨테이너 상태
docker-compose ps

# 특정 컨테이너 상태
docker-compose ps backend
docker-compose ps mysql
```

#### 헬스체크 확인
```bash
# 백엔드 헬스체크
curl http://localhost:5000/health

# 또는 Docker 컨테이너 내부에서
docker-compose exec backend curl http://localhost:5000/health
```

### 개발 환경 (외부 도구 접근 필요 시)

**⚠️ 개발 환경에서만 사용하세요!**

```bash
# MySQL Workbench, DBeaver 등 외부 도구로 접근이 필요한 경우
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build
```

### 로컬 개발 환경 설정 (백엔드/프론트엔드 로컬 실행)

Docker 빌드가 오래 걸리는 경우, 백엔드와 프론트엔드는 로컬에서 실행하고 MySQL만 Docker로 실행할 수 있습니다.

#### 1. MySQL만 Docker로 실행

**방법 1: 배치 스크립트 사용 (Windows, 권장)**
```bash
# 프로젝트 루트에서 실행
start-mysql-docker.bat
```

**방법 2: 수동 실행**
```bash
# 로컬 MySQL이 3306을 사용 중이면 먼저 중지 필요
# (관리자 권한으로 실행)
net stop MySQL80

# 로컬 개발용 MySQL만 실행 (포트 3306 노출)
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d mysql

# MySQL 상태 확인
docker-compose -f docker-compose.yml -f docker-compose.dev.yml ps
docker-compose -f docker-compose.yml -f docker-compose.dev.yml logs mysql
```

#### 2. 환경 변수 설정 (.env 파일)

프로젝트 루트의 `.env` 파일에 다음 환경 변수를 설정합니다:

```bash
# MySQL 설정 (로컬 접근용)
MYSQL_HOST=localhost          # Docker MySQL에 접근하려면 localhost 사용
MYSQL_PORT=3306              # docker-compose.dev.yml에서 노출한 포트
# 주의: 로컬 MySQL이 3306을 사용 중이면 중지하거나 다른 포트로 변경해야 합니다
MYSQL_DATABASE=privalert
MYSQL_USER=privalert_user
MYSQL_PASSWORD=your-password-here
MYSQL_ROOT_PASSWORD=your-root-password-here

# Flask 설정
FLASK_ENV=development
FLASK_SECRET_KEY=your-super-secret-key-minimum-32-characters-long
JWT_SECRET_KEY=your-jwt-secret-key-different-from-flask-secret-key

# CORS 설정 (프론트엔드 로컬 실행용)
CORS_ORIGINS=http://localhost:3000,http://localhost:5173

# API 키 (필요한 경우)
OPENAI_API_KEY=your-openai-api-key
# GOOGLE_CLOUD_CREDENTIALS_JSON은 더 이상 필요하지 않음 (EasyOCR 사용)
```

#### 3. 백엔드 로컬 실행
```bash
# backend 디렉토리로 이동
cd backend

# 가상환경 활성화 (Windows)
venv\Scripts\activate

# 가상환경 활성화 (Linux/Mac)
source venv/bin/activate

# 의존성 설치
pip install -r requirements.txt

# Flask 앱 실행
python wsgi.py
# 또는
flask run --host=0.0.0.0 --port=5000
```

#### 4. 프론트엔드 로컬 실행
```bash
# frontend 디렉토리로 이동
cd frontend

# 의존성 설치
npm install

# 개발 서버 실행
npm run dev
```

#### 5. 접속 확인
- **프론트엔드**: http://localhost:5173 (Vite 기본 포트) 또는 http://localhost:3000
- **백엔드 API**: http://localhost:5000
- **API 문서**: http://localhost:5000/api-docs/

#### 6. MySQL 중지

**방법 1: 배치 스크립트 사용 (Windows)**
```bash
stop-mysql-docker.bat
```

**방법 2: 수동 실행**
```bash
# MySQL 컨테이너 중지
docker-compose -f docker-compose.yml -f docker-compose.dev.yml down

# 데이터까지 삭제하려면
docker-compose -f docker-compose.yml -f docker-compose.dev.yml down -v
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

# 코드 변경 후 재빌드 및 재시작
# Backend 코드 변경 시 (볼륨 마운트로 자동 반영)
docker-compose restart backend

# Frontend 코드 변경 시 (재빌드 필요)
docker-compose down
docker-compose build frontend
docker-compose up -d

# Dockerfile 변경 시 (캐시 없이 재빌드)
docker-compose build --no-cache <service-name>
docker-compose up -d

# MySQL 접속
docker-compose exec mysql mysql -u privalert_user -p privalert

# 백엔드 컨테이너 접속
docker-compose exec backend bash

# 데이터베이스 백업
docker-compose exec mysql mysqldump -u root -p privalert > backup_$(date +%Y%m%d).sql

# 데이터베이스 복원
docker-compose exec -T mysql mysql -u root -p privalert < backup_20241104.sql
```

### Docker 이미지 빌드 및 푸시

#### 방법 1: 스크립트 사용 (권장)

**Windows:**
```powershell
cd C:\도전보안벨\PrivAlert
.\docker-push.bat
```

**Linux/Mac:**
```bash
cd PrivAlert
chmod +x docker-push.sh
./docker-push.sh
```

#### 방법 2: 수동 실행

**1단계: Docker Hub 로그인**
```bash
docker login
```

**2단계: 이미지 빌드**
```bash
cd PrivAlert
docker-compose build --no-cache
```

**3단계: 이미지 태그 지정**
```bash
# Docker Hub 사용자명으로 변경하세요
export DOCKER_USERNAME=your-username

# 이미지 태그 지정
docker tag ${DOCKER_USERNAME}/privalert-backend:1.0 ${DOCKER_USERNAME}/privalert-backend:latest
docker tag ${DOCKER_USERNAME}/privalert-frontend:1.0 ${DOCKER_USERNAME}/privalert-frontend:latest
```

**4단계: Docker Hub에 푸시**
```bash
docker push ${DOCKER_USERNAME}/privalert-backend:latest
docker push ${DOCKER_USERNAME}/privalert-frontend:latest
```

#### 방법 3: Docker Compose로 직접 푸시

`docker-compose.yml`에 이미지 이름을 추가하면 자동으로 푸시됩니다:

```yaml
backend:
  build:
    context: ./backend
    dockerfile: Dockerfile
  image: your-username/privalert-backend:latest  # 추가

frontend:
  build:
    context: ./frontend
    dockerfile: Dockerfile
  image: your-username/privalert-frontend:latest  # 추가
```

그 후:
```bash
docker-compose build
docker-compose push
```

#### 빌드 캐시 없이 재빌드
```bash
docker-compose build --no-cache backend
docker-compose build --no-cache frontend
```

### 보안 설정

#### MySQL 포트 노출 없음
- ✅ **보안**: MySQL은 Docker 내부 네트워크(`privalert-network`)에서만 접근 가능
- ✅ **보안**: 외부에서 MySQL 포트(3306)에 직접 접근 불가능
- ✅ **보안**: 백엔드는 `mysql` 호스트명으로 MySQL에 접근 (Docker DNS)

#### 네트워크 격리
- Docker 네트워크 `privalert-network` 사용
- MySQL은 내부 네트워크에서만 접근 가능
- 프로덕션 환경에서는 `internal: true`로 설정 권장

### 주의사항

⚠️ **보안**: 
- MySQL 포트는 외부에 노출되지 않습니다 (docker-compose.yml만 사용 시)
- 로컬 개발 환경(docker-compose.dev.yml 사용 시)에서는 MySQL 포트가 노출됩니다
- 외부 도구(MySQL Workbench, DBeaver 등)로 접근하려면 `docker-compose.dev.yml`을 함께 사용 (개발 환경에서만)
- 프로덕션 환경에서는 절대 포트를 노출하지 마세요

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
- `POST /api/v1/education/suggest` - Claude API 기반 수정 문장 및 교육 자료 생성

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

## 🔒 보안

### ⚠️ 중요 경고

**이 시스템은 HTTP 전용 환경에서 동작합니다. HTTPS가 적용되지 않았으므로 보안에 취약할 수 있습니다.**

- 운영 환경에서는 **반드시 HTTPS로 전환**해야 합니다
- HTTP 환경에서의 위험 사항을 이해하고 적절한 보완 조치를 취하세요

### 보안 체크리스트

**실행 전 확인사항:**
- [ ] `.env` 파일이 생성되었고 모든 필수 값이 설정되었는가?
- [ ] `FLASK_SECRET_KEY`가 최소 32자 이상인가?
- [ ] `MYSQL_ROOT_PASSWORD`가 강력한 비밀번호인가?
- [ ] `MYSQL_PASSWORD`가 강력한 비밀번호인가?
- [ ] `.env` 파일이 Git에 커밋되지 않았는가?
- [ ] 프로덕션 환경에서는 `docker-compose.dev.yml`을 사용하지 않는가?

### HTTP 전용 환경의 위험

#### 1. 패킷 스니핑 (Man-in-the-Middle 공격)

**위험**: HTTP 통신은 암호화되지 않으므로 네트워크 상에서 패킷을 가로채면 모든 데이터를 볼 수 있습니다.

**영향**:
- 비밀번호 평문 노출
- 세션 쿠키 탈취
- 개인정보 노출
- CSRF 토큰 노출

**완화 조치 (현재 구현)**:
- `HttpOnly` 쿠키 플래그 (JavaScript 접근 방지)
- `SameSite=Strict` 쿠키 플래그 (CSRF 공격 방지)
- 세션 토큰 회전
- Double Submit Cookie 패턴 (CSRF 보호)
- Rate Limiting (무차별 대입 공격 방지)

**권장 해결책**: HTTPS 전환

#### 2. 쿠키 탈취

**위험**: HTTP 환경에서는 네트워크 스니핑으로 쿠키를 탈취할 수 있습니다.

**완화 조치 (현재 구현)**:
- `HttpOnly` 플래그로 JavaScript 접근 차단
- `SameSite=Strict` 플래그로 크로스 사이트 요청 차단
- 세션 만료 시간 짧게 설정 (24시간)
- 세션 회전 지원

**권장 해결책**: HTTPS 전환 + `Secure` 플래그 활성화

#### 3. HSTS 미적용

**위험**: HSTS (HTTP Strict Transport Security)를 적용하지 않았으므로, HTTPS로 전환 시에도 일시적으로 HTTP로 접근할 수 있습니다.

**완화 조치**: HSTS는 HTTP 환경에서 설정하지 않음 (현재 구현)

**권장 해결책**: HTTPS 전환 후 HSTS 활성화

### 구현된 보안 조치

#### 1. 비밀번호 보안
- **Argon2id 해싱** (권장 파라미터)
  - `memory_cost=65536` (64MB)
  - `time_cost=3` (3 iterations)
  - `parallelism=4` (4 threads)
  - `hash_len=32` (32 bytes)
  - `salt_len=16` (16 bytes salt)
- **비밀번호 강도 검증**
  - 최소 12자
  - 대소문자, 숫자, 특수문자 포함
  - 약한 패턴 차단
- **비밀번호 재사용 방지**: 새 비밀번호는 현재 비밀번호와 달라야 함

#### 2. 토큰 보안
- **토큰 해시 저장**: 원문 토큰은 DB에 저장하지 않고 SHA256 해시만 저장
- **단발성 토큰**: 사용 후 즉시 무효화
- **만료 시간**: 이메일 검증 24시간, 비밀번호 재설정 1시간
- **예측 불가능한 토큰**: `secrets.token_urlsafe()` 사용

#### 3. 세션 보안
- **예측 불가능한 세션 ID**: `secrets.token_urlsafe(32)` 사용
- **Double Submit Cookie**: 세션 ID + 세션 토큰으로 검증
- **세션 회전**: 주기적 세션 갱신 지원
- **세션 만료**: 24시간 후 자동 만료
- **세션 관리**: 사용자가 세션 목록 조회 및 무효화 가능

#### 4. CSRF 보호
- **Double Submit Cookie 패턴**: 쿠키와 요청 헤더의 토큰 비교
- **서버 세션 기반 CSRF 토큰**: 사용자별 토큰 생성 및 검증
- **일회용 토큰**: 사용 후 즉시 무효화
- **SameSite=Strict**: 크로스 사이트 요청 차단

#### 5. Rate Limiting
- **IP 기반 제한**: Flask-Limiter 사용
- **계정 기반 제한**: 로그인 실패 5회 시 30분 잠금
- **엔드포인트별 제한**:
  - 회원가입: 5회/시간
  - 로그인: 10회/시간
  - 비밀번호 재설정 요청: 5회/시간

#### 6. 입력 검증
- **서버 측 검증**: 모든 입력값 서버에서 검증
- **이메일 형식 검증**: 정규식 사용
- **XSS 방어**: HTML 이스케이프
- **SQL Injection 방지**: SQLAlchemy ORM 사용
- **Path Traversal 방지**: 파일 경로 검증

#### 7. MFA (Multi-Factor Authentication)
- **TOTP (RFC 6238)**: Google Authenticator, Authy 등 호환
- **복구 코드**: 10개의 일회용 복구 코드 제공
- **시크릿 암호화**: Fernet (symmetric encryption) 사용
- **QR 코드**: Base64 인코딩된 이미지 제공

#### 8. 감사 로그
- **모든 중요한 이벤트 기록**:
  - 로그인/로그아웃
  - 비밀번호 변경
  - 계정 삭제 요청
  - MFA 활성화/비활성화
  - 세션 무효화
- **민감 정보 제외**: 비밀번호, 토큰 등은 로그에 기록하지 않음
- **보관 기간**: 90일 (설정 가능)

#### 9. 세션 쿠키 설정 (HTTP 환경)

**현재 설정**:
```
Set-Cookie: session_id=...; HttpOnly; SameSite=Strict; Path=/; Max-Age=86400
```

**설정 이유**:
- `HttpOnly`: JavaScript 접근 차단 (XSS 공격 완화)
- `SameSite=Strict`: 크로스 사이트 요청 차단 (CSRF 공격 완화)
- `Secure=False`: HTTP 환경이므로 Secure 플래그 미설정
- `Path=/`: 루트 경로에서만 쿠키 전송

**HTTPS 전환 시 변경 필요**:
```
Set-Cookie: session_id=...; HttpOnly; Secure; SameSite=Strict; Path=/; Max-Age=86400
```

### HTTPS 전환 체크리스트

운영 환경에서 HTTPS로 전환할 때 다음 항목을 확인하세요:

#### 1. SSL/TLS 인증서 설정
- [ ] SSL/TLS 인증서 발급 (Let's Encrypt, 상용 인증서 등)
- [ ] 인증서 파일 경로 설정
- [ ] 인증서 갱신 자동화 (Let's Encrypt의 경우 certbot 사용)

#### 2. 쿠키 설정 변경
- [ ] `SESSION_COOKIE_SECURE = True` 설정
- [ ] `JWT_COOKIE_SECURE = True` 설정
- [ ] 세션 쿠키 설정에서 `Secure` 플래그 활성화
- [ ] 모든 쿠키에 `Secure` 플래그 추가

**변경 위치**: `backend/app/__init__.py`, `backend/app/routes/auth_routes.py`

#### 3. HSTS 활성화
- [ ] `Strict-Transport-Security` 헤더 추가
- [ ] `max-age` 설정 (권장: 31536000 = 1년)
- [ ] `includeSubDomains` 옵션 고려
- [ ] `preload` 옵션 고려 (HSTS Preload List 등록 시)

**변경 위치**: `backend/app/__init__.py`

#### 4. HTTP → HTTPS 리다이렉트
- [ ] 모든 HTTP 요청을 HTTPS로 리다이렉트
- [ ] Nginx/Apache 설정에서 리다이렉트 규칙 추가
- [ ] 프론트엔드에서 HTTPS URL 사용

#### 5. CORS 설정 업데이트
- [ ] CORS 허용 오리진을 HTTPS URL로 변경
- [ ] `.env` 파일의 `CORS_ORIGINS` 업데이트

#### 6. 프론트엔드 설정
- [ ] API 베이스 URL을 HTTPS로 변경
- [ ] 모든 외부 리소스(이미지, 스크립트 등)를 HTTPS로 로드
- [ ] Mixed Content 경고 확인

#### 7. 데이터베이스 연결
- [ ] 데이터베이스 연결이 내부 네트워크인지 확인
- [ ] 외부 연결이 필요한 경우 SSL/TLS 사용

#### 8. 보안 헤더 재확인
- [ ] `X-Content-Type-Options: nosniff`
- [ ] `X-Frame-Options: DENY`
- [ ] `X-XSS-Protection: 1; mode=block`
- [ ] `Referrer-Policy: strict-origin-when-cross-origin`
- [ ] `Content-Security-Policy` 업데이트 (필요 시)

#### 9. 테스트
- [ ] HTTPS 연결 테스트
- [ ] 쿠키가 `Secure` 플래그로 전송되는지 확인
- [ ] HSTS 헤더가 설정되는지 확인
- [ ] HTTP → HTTPS 리다이렉트 테스트
- [ ] 모든 API 엔드포인트 HTTPS로 작동하는지 확인
- [ ] Mixed Content 경고 없는지 확인

#### 10. 모니터링
- [ ] SSL/TLS 인증서 만료 모니터링 설정
- [ ] HTTPS 연결 실패 모니터링
- [ ] 보안 이벤트 로깅 강화

### 보안 검사 체크리스트

#### 배포 전 검사
- [ ] 의존성 취약점 스캔 (`pip-audit`, `snyk`, `trivy`)
- [ ] 정적 분석 (`bandit`, `pylint`, `mypy`)
- [ ] 코드 리뷰 (보안 관점)
- [ ] 펜테스팅 (선택사항)

#### 정기 검사
- [ ] 의존성 업데이트 및 취약점 확인 (월 1회)
- [ ] 보안 패치 적용
- [ ] 로그 분석 (비정상 활동 확인)
- [ ] 감사 로그 검토

### 보안 명령어

#### 의존성 취약점 스캔
```bash
# pip-audit (Python)
pip install pip-audit
pip-audit

# trivy (Docker 이미지)
trivy image privalert:1.0

# snyk (종합)
snyk test
```

#### 정적 분석
```bash
# bandit (보안 취약점 검사)
pip install bandit
bandit -r backend/app

# pylint (코드 품질)
pylint backend/app

# mypy (타입 체크)
mypy backend/app
```

---

## 📑 커밋 스타일

- **[CREATE]** : API 첫 생성, 기능 추가  
- **[UPDATE]** : 버그 및 API 수정, 추가 구현 중  
- **[REFAC]** : 오타 수정, 디렉토리 변경 등 소규모 수정  
- **[CHORE]** : 코드 변경 없는 환경설정 등 수정 (예: setup)  
- **[DOCS]** : 문서 작업  
- **[DEPLOY]** : 배포 관련 작업

---

## 👤 사용자 인증 시스템

### 개요

이 프로젝트는 HTTP 전용 환경에서 작동하는 안전한 사용자 인증 시스템을 제공합니다.

### 주요 기능

- **회원가입 및 이메일 검증** (SMTP 기반 이메일 인증)
  - 이메일 인증 완료 후 계정 생성
  - 암호화된 토큰 메타데이터 저장
- **로그인/로그아웃** (세션 기반)
- **비밀번호 재설정** (이메일 토큰 발송)
- **마이페이지** (프로필 수정, 필터링 설정, 분석 기록)
- **사용자 맞춤 필터링** (DB 저장 및 자동 적용)
- **MFA (Multi-Factor Authentication)** - TOTP 기반
- **세션 관리** (세션 목록, 개별/전체 로그아웃)
- **계정 삭제** (7일 유예 기간)

### 설치 및 설정

#### 1. 환경 변수 설정

`.env` 파일에 다음 변수를 추가하세요:

```bash
# 암호화 키 (MFA 시크릿 및 토큰 메타데이터 암호화용)
# Fernet 키 생성: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
ENCRYPTION_KEY=your-fernet-key-here

# 이메일 발송 설정 (이메일 인증 필수)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_EMAIL=your-email@gmail.com
SMTP_PASSWORD=your-app-password  # Gmail: 앱 비밀번호 생성 필요
SMTP_FROM=noreply@privalert.com

# Claude API (프롬프팅 - 선택사항, 없으면 폴백 모드)
ANTHROPIC_API_KEY=sk-ant-...
CLAUDE_MODEL=claude-sonnet-4-5-20250929
```

**Gmail 앱 비밀번호 생성 방법:**
1. Google 계정 설정 → 보안
2. 2단계 인증 활성화
3. 앱 비밀번호 생성
4. 생성된 16자리 비밀번호를 `SMTP_PASSWORD`에 설정

#### 2. 의존성 설치

```bash
cd backend
pip install -r requirements.txt
```

필요한 패키지:
- `argon2-cffi` - Argon2id 비밀번호 해싱
- `pyotp` - TOTP (MFA)
- `qrcode[pil]` - QR 코드 생성
- `cryptography` - 암호화

#### 3. 데이터베이스 초기화

```bash
cd backend
python wsgi.py
```

서버 시작 시 자동으로 테이블이 생성됩니다.

### API 엔드포인트

#### 인증 (Authentication)

**회원가입**
```
POST /api/v1/auth/signup
Body: { "email": "...", "password": "..." }
Response: { "success": true, "message": "...", "data": {...} }
```

**이메일 검증**
```
GET /api/v1/auth/verify?token=...
Response: { "success": true, "message": "..." }
```

**로그인**
```
POST /api/v1/auth/login
Body: { "email": "...", "password": "...", "totp": "..." (선택) }
Response: { "success": true, "data": { "user": {...}, "csrf_token": "...", "session_id": "..." } }
Set-Cookie: session_id=..., session_token=...
```

**로그아웃**
```
POST /api/v1/auth/logout
Response: { "success": true, "message": "..." }
```

**비밀번호 재설정 요청**
```
POST /api/v1/auth/request-reset
Body: { "email": "..." }
Response: { "success": true, "message": "..." }
```

**비밀번호 재설정**
```
POST /api/v1/auth/reset
Body: { "token": "...", "newPassword": "..." }
Response: { "success": true, "message": "..." }
```

#### 사용자 프로필 (User Profile)

**프로필 조회**
```
GET /api/v1/user/me
Headers: Cookie: session_id=..., session_token=...
Response: { "success": true, "data": {...} }
```

**프로필 수정**
```
PATCH /api/v1/user/me
Headers: X-CSRF-Token: ...
Body: { "email": "..." (선택), "csrf_token": "..." }
Response: { "success": true, "data": {...} }
```

**비밀번호 변경**
```
POST /api/v1/user/password-change
Headers: X-CSRF-Token: ...
Body: { "currentPassword": "...", "newPassword": "...", "csrf_token": "..." }
Response: { "success": true, "message": "..." }
```

**세션 목록 조회**
```
GET /api/v1/user/sessions
Response: { "success": true, "data": { "sessions": [...], "current_session_id": "..." } }
```

**특정 세션 무효화**
```
DELETE /api/v1/user/sessions/<session_id>
Headers: X-CSRF-Token: ...
Body: { "csrf_token": "..." }
Response: { "success": true, "message": "..." }
```

**모든 세션 무효화**
```
POST /api/v1/user/sessions/revoke-all
Headers: X-CSRF-Token: ...
Body: { "csrf_token": "..." }
Response: { "success": true, "message": "..." }
```

**계정 삭제 요청**
```
POST /api/v1/user/delete-account
Headers: X-CSRF-Token: ...
Body: { "password": "...", "csrf_token": "..." }
Response: { "success": true, "message": "..." }
```

#### MFA (Multi-Factor Authentication)

**MFA 활성화**
```
POST /api/v1/user/mfa/enable
Headers: X-CSRF-Token: ...
Body: { "csrf_token": "..." }
Response: { "success": true, "data": { "secret": "...", "qr_code": "...", "backup_codes": [...] } }
```

**MFA 활성화 확인**
```
POST /api/v1/user/mfa/confirm
Headers: X-CSRF-Token: ...
Body: { "totp": "...", "csrf_token": "..." }
Response: { "success": true, "message": "..." }
```

**MFA 비활성화**
```
POST /api/v1/user/mfa/disable
Headers: X-CSRF-Token: ...
Body: { "password": "...", "csrf_token": "..." }
Response: { "success": true, "message": "..." }
```

### 보안 주의사항

#### HTTP 환경의 제한사항

1. **쿠키 탈취 위험**: HTTP 환경에서는 네트워크 스니핑으로 쿠키를 탈취할 수 있습니다
   - 완화 조치: `HttpOnly`, `SameSite=Strict` 플래그 적용
   - 권장: HTTPS 전환

2. **HSTS 미적용**: HTTP 환경에서는 HSTS를 설정하지 않습니다

3. **Secure 플래그 미설정**: HTTP 환경에서는 `Secure` 쿠키 플래그를 사용하지 않습니다
   - HTTPS 전환 시 `Secure` 플래그를 활성화해야 합니다

### 보안 권장사항

1. **MFA 활성화**: 가능한 모든 계정에 MFA를 활성화하세요
2. **강력한 비밀번호**: 최소 12자, 대소문자, 숫자, 특수문자 포함
3. **세션 관리**: 사용하지 않는 세션은 정기적으로 무효화하세요
4. **HTTPS 전환**: 운영 환경에서는 반드시 HTTPS로 전환하세요

### 문제 해결

#### Argon2id 설치 오류
```bash
# Windows
pip install argon2-cffi-binary

# Linux/Mac
pip install argon2-cffi
```

#### 이메일 발송 오류
- `.env` 파일에 SMTP 설정이 올바르게 되어 있는지 확인하세요
- Gmail 사용 시 앱 비밀번호를 사용해야 합니다
- SMTP 설정이 없거나 실패하면 개발 환경에서는 로그에 토큰이 출력됩니다
- 프로덕션 환경에서는 SMTP 설정이 필수입니다

---

## 🔧 서버 네트워크 오류 진단

### 관리자 로그인 네트워크 오류 해결 방법

#### 1. 서버 상태 확인

**Docker 사용 시:**
```bash
# 컨테이너 상태 확인
docker-compose ps

# 백엔드 로그 확인
docker-compose logs backend

# 실시간 로그 확인
docker-compose logs -f backend
```

**로컬 실행 시:**
```bash
# 프로세스 확인
netstat -ano | findstr :5000

# 또는
tasklist | findstr python
```

#### 2. 서버 재시작

**Docker:**
```bash
cd PrivAlert
docker-compose restart backend
```

**로컬:**
```bash
cd PrivAlert/backend
python wsgi.py
```

#### 3. 포트 확인

- 기본 포트: **5000**
- Docker 포트 매핑: `BACKEND_PORT:5000`
- 프론트엔드에서 접근하는 URL 확인:
  - `http://localhost:5000/api/v1/admin/auth/login`
  - 또는 `http://localhost:${BACKEND_PORT}/api/v1/admin/auth/login`

#### 4. CORS 설정 확인

`.env` 파일에 다음이 설정되어 있는지 확인:
```bash
CORS_ORIGINS=http://localhost:3000
```

프론트엔드가 다른 포트에서 실행 중이라면 추가:
```bash
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
```

#### 5. API 엔드포인트 확인

관리자 로그인 엔드포인트:
```
POST /api/v1/admin/auth/login
```

프론트엔드에서 요청하는 URL이 정확한지 확인:
- ✅ `http://localhost:5000/api/v1/admin/auth/login`
- ❌ `http://localhost:5000/admin/login` (잘못된 경로)

#### 6. 네트워크 오류 종류별 해결

**"Failed to fetch" 또는 "Network Error":**
- 서버가 실행되지 않음
- 포트가 다름
- CORS 문제

**"Connection refused":**
- 서버가 실행되지 않음
- 방화벽 문제

**"CORS error":**
- CORS_ORIGINS 설정 확인
- 프론트엔드 origin이 허용 목록에 있는지 확인

#### 7. 빠른 해결 방법

1. Docker 컨테이너 재시작:
```bash
cd PrivAlert
docker-compose down
docker-compose up -d
```

2. 로그 확인:
```bash
docker-compose logs backend | tail -50
```

3. 브라우저 개발자 도구에서 네트워크 탭 확인:
   - 요청 URL
   - 응답 상태 코드
   - 에러 메시지

#### 8. 테스트 요청

터미널에서 직접 테스트:
```bash
curl -X POST http://localhost:5000/api/v1/admin/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"your-password"}'
```

성공하면 서버는 정상 작동 중입니다.

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
- `.env` 파일은 프로젝트 루트에 생성 (필수)
- `.env` 파일은 Git 제외
- 환경 변수 목록은 루트 `.env.example` 참조 (있는 경우)

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

### 기능 설명

**텍스트 분석:**
- 직접 입력 텍스트: Claude API로 수정문장 생성 (API 키 없으면 폴백 모드)
- OCR 추출 텍스트: 마스킹 결과 출력 ([주소] 형식)
- 사용자 맞춤 필터링: DB에 저장된 사용자 설정 자동 적용

**이미지/영상 분석:**
- 얼굴/손가락: 사용자 선택에 따라 출력 (`show_faces`, `blur_fingers` 옵션)
- OCR 텍스트: 마스킹 결과로 표시

**이메일 인증:**
- 회원가입 시 SMTP를 통해 이메일 인증 토큰 발송
- 토큰 검증 완료 후 계정 생성
- 이메일 인증 완료 전까지 로그인 불가

**프롬프팅:**
- Claude API 기반 고품질 교육 콘텐츠 생성
- API 키 없어도 폴백 모드로 기본 기능 작동
- 법령 인용, 위험 시나리오, 보안 대응 가이드 제공
