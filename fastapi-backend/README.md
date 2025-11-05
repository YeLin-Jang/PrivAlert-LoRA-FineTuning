# PrivAlert FastAPI Backend

FastAPI 기반 이메일 인증번호 전송 및 검증 시스템

## 기능

- 회원가입 시 이메일로 6자리 인증번호 전송
- 인증번호 검증 및 계정 활성화
- 보안: bcrypt 비밀번호 해싱, SQL Injection 방지

## 설치 및 실행

### 1. 의존성 설치

```bash
cd fastapi-backend
pip install -r requirements.txt
```

### 2. 환경 변수 설정

`.env.example` 파일을 참고하여 `.env` 파일을 생성하세요:

```bash
cp .env.example .env
```

`.env` 파일에 다음 정보를 설정하세요:

```bash
# SMTP 설정 (Gmail 예시)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_EMAIL=your-email@gmail.com
SMTP_PASSWORD=your-app-password  # Gmail 앱 비밀번호
SMTP_FROM=noreply@privalert.com

# 보안 키
SECRET_KEY=your-secret-key-here-minimum-32-characters-long
```

### 3. Gmail 앱 비밀번호 생성 방법

1. Google 계정 설정 → 보안
2. 2단계 인증 활성화
3. 앱 비밀번호 생성
4. 생성된 비밀번호를 `SMTP_PASSWORD`에 설정

### 4. 서버 실행

```bash
python main.py
```

또는:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

서버가 실행되면 다음 URL에서 API 문서를 확인할 수 있습니다:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## API 엔드포인트

### 1. 회원가입 (`POST /api/v1/register`)

```json
{
  "email": "user@example.com",
  "password": "SecurePass123!"
}
```

**응답:**
```json
{
  "message": "회원가입이 완료되었습니다. 이메일을 확인하여 인증번호를 입력하세요.",
  "success": true
}
```

### 2. 이메일 인증 (`POST /api/v1/verify-email`)

```json
{
  "email": "user@example.com",
  "verification_code": "123456"
}
```

**응답:**
```json
{
  "id": 1,
  "email": "user@example.com",
  "is_active": true,
  "created_at": "2024-01-01T00:00:00",
  "updated_at": "2024-01-01T00:00:00"
}
```

## 보안 고려사항

1. **비밀번호 해싱**: bcrypt 사용 (12 rounds)
2. **SQL Injection 방지**: SQLAlchemy ORM 사용
3. **환경 변수 관리**: 민감 정보는 `.env` 파일로 관리
4. **로그 보안**: 비밀번호, 인증번호는 로그에 기록하지 않음
5. **인증번호 보안**: 예측 불가능한 난수 생성 (secrets 모듈)
6. **만료 시간 관리**: 인증번호는 5분 후 자동 만료

## 프로젝트 구조

```
fastapi-backend/
├── main.py                    # FastAPI 애플리케이션 진입점
├── requirements.txt           # Python 의존성
├── .env.example              # 환경 변수 예시
├── README.md                 # 프로젝트 문서
└── app/
    ├── core/
    │   └── config.py         # 설정 관리
    ├── database.py           # 데이터베이스 연결
    ├── models/
    │   └── user_model.py    # 사용자 스키마
    ├── routes/
    │   └── auth_routes.py   # 인증 API 라우트
    └── services/
        ├── email_service.py          # 이메일 전송 서비스
        └── verification_service.py    # 인증번호 생성/검증 서비스
```

## Redis 사용 (선택사항)

Redis를 사용하면 인증번호를 분산 환경에서도 공유할 수 있습니다.

1. Redis 설치 및 실행
2. `.env` 파일에 설정:
   ```bash
   USE_REDIS=true
   REDIS_URL=redis://localhost:6379
   ```

Redis를 사용하지 않으면 메모리 기반 저장소를 사용합니다.

## 테스트

```bash
# 회원가입
curl -X POST "http://localhost:8000/api/v1/register" \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "SecurePass123!"}'

# 이메일 인증
curl -X POST "http://localhost:8000/api/v1/verify-email" \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "verification_code": "123456"}'
```

## 문제 해결

### 이메일 전송 실패
- Gmail 앱 비밀번호가 올바른지 확인
- SMTP 설정이 올바른지 확인
- 방화벽에서 587 포트가 차단되지 않았는지 확인

### 인증번호 만료
- 인증번호는 5분간만 유효합니다
- 새로운 인증번호를 받으려면 다시 회원가입을 진행하세요

