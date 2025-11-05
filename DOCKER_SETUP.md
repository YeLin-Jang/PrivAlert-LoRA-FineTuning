# Docker 환경 설정 가이드

## 보안: MySQL 포트 외부 노출 없음

이 프로젝트는 **보안을 위해 MySQL 포트를 외부에 노출하지 않습니다**.  
Docker 내부 네트워크에서만 MySQL에 접근할 수 있습니다.

## 실행 방법

### 1. 전체 서비스 실행 (권장)

```bash
# 프로젝트 루트에서 실행
docker-compose up -d --build

# 로그 확인
docker-compose logs -f

# 특정 서비스 로그만 확인
docker-compose logs -f backend
docker-compose logs -f mysql
```

### 2. MySQL만 실행

```bash
docker-compose up -d mysql

# MySQL 상태 확인
docker-compose ps mysql
docker-compose logs mysql
```

### 3. 백엔드만 실행 (MySQL이 이미 실행 중인 경우)

```bash
docker-compose up -d backend

# 백엔드 로그 확인
docker-compose logs -f backend
```

## 접속 확인

### 브라우저에서 확인

- **프론트엔드**: http://localhost:3000 (또는 `FRONTEND_PORT`에 설정된 포트)
- **백엔드 API**: http://localhost:5000 (또는 `BACKEND_PORT`에 설정된 포트)
- **API 문서 (Swagger)**: http://localhost:5000/api-docs/

### Docker 로그로 확인

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

### 컨테이너 상태 확인

```bash
# 모든 컨테이너 상태
docker-compose ps

# 특정 컨테이너 상태
docker-compose ps backend
docker-compose ps mysql
```

### 헬스체크 확인

```bash
# 백엔드 헬스체크
curl http://localhost:5000/health

# 또는 Docker 컨테이너 내부에서
docker-compose exec backend curl http://localhost:5000/health
```

## 보안 설정

### MySQL 포트 노출 없음

- ✅ **보안**: MySQL은 Docker 내부 네트워크(`privalert-network`)에서만 접근 가능
- ✅ **보안**: 외부에서 MySQL 포트(3306)에 직접 접근 불가능
- ✅ **보안**: 백엔드는 `mysql` 호스트명으로 MySQL에 접근 (Docker DNS)

### 네트워크 격리

- Docker 네트워크 `privalert-network` 사용
- MySQL은 내부 네트워크에서만 접근 가능
- 프로덕션 환경에서는 `internal: true`로 설정 권장

## 문제 해결

### MySQL 연결 실패

```bash
# MySQL 컨테이너 상태 확인
docker-compose ps mysql

# MySQL 로그 확인
docker-compose logs mysql

# MySQL 재시작
docker-compose restart mysql

# MySQL 컨테이너 내부 접속
docker-compose exec mysql mysql -u privalert_user -p privalert
```

### 백엔드 연결 실패

```bash
# 백엔드 로그 확인
docker-compose logs backend

# 백엔드 재시작
docker-compose restart backend

# 백엔드 컨테이너 내부 접속
docker-compose exec backend bash
```

### 데이터베이스 초기화 확인

백엔드 로그에서 다음 메시지 확인:
- `데이터베이스 테이블 생성 완료`
- `기본 관리자 계정 생성: admin`
- `더미 사용자 데이터 생성 완료: demo_user`

## 개발 팁

### 코드 변경 시 자동 재로드

백엔드 볼륨이 마운트되어 있으므로 코드 변경 시 자동으로 재로드됩니다.

### 데이터베이스 초기화 재실행

```bash
# MySQL 컨테이너 재시작 (데이터는 유지됨)
docker-compose restart mysql

# 데이터베이스 초기화는 백엔드 시작 시 자동으로 실행됨
```

### 환경 변수 확인

```bash
# 백엔드 컨테이너의 환경 변수 확인
docker-compose exec backend env | grep MYSQL
```

## 로컬 개발 환경 설정 (백엔드/프론트엔드 로컬 실행)

Docker 빌드가 오래 걸리는 경우, 백엔드와 프론트엔드는 로컬에서 실행하고 MySQL만 Docker로 실행할 수 있습니다.

### 1. MySQL만 Docker로 실행

**방법 1: 배치 스크립트 사용 (Windows, 권장)**

```bash
# 프로젝트 루트에서 실행
start-mysql-docker.bat
```

이 스크립트는:
- 로컬 MySQL 서비스가 실행 중인지 확인
- 필요 시 로컬 MySQL 중지 (관리자 권한 필요)
- Docker MySQL 컨테이너 정리 및 실행

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

### 2. 환경 변수 설정 (.env 파일)

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

### 3. 백엔드 로컬 실행

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

### 4. 프론트엔드 로컬 실행

```bash
# frontend 디렉토리로 이동
cd frontend

# 의존성 설치
npm install

# 개발 서버 실행
npm run dev
```

### 5. 접속 확인

- **프론트엔드**: http://localhost:5173 (Vite 기본 포트) 또는 http://localhost:3000
- **백엔드 API**: http://localhost:5000
- **API 문서**: http://localhost:5000/api-docs/

### 6. MySQL 중지

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

### 로컬 개발 환경의 장점

- ✅ 빠른 코드 변경 반영 (핫 리로드)
- ✅ 디버깅 용이
- ✅ Docker 빌드 시간 단축
- ✅ 개발 도구 사용 가능

### 주의사항

⚠️ **보안**: 
- 로컬 개발 환경에서는 MySQL 포트가 노출됩니다
- 개발 환경에서만 사용하고 프로덕션에서는 절대 사용하지 마세요
- `.env` 파일은 절대 Git에 커밋하지 마세요

## 주의사항

⚠️ **보안**: 
- MySQL 포트는 외부에 노출되지 않습니다 (docker-compose.yml만 사용 시)
- 로컬 개발 환경(docker-compose.dev.yml 사용 시)에서는 MySQL 포트가 노출됩니다
- 외부 도구(MySQL Workbench, DBeaver 등)로 접근하려면 `docker-compose.dev.yml`을 함께 사용 (개발 환경에서만)
- 프로덕션 환경에서는 절대 포트를 노출하지 마세요

