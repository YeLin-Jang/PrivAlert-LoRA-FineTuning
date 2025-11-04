# 데이터베이스 설정 가이드 (초간단 버전)

## MySQL과의 차이점

**MySQL**: 별도 서버 설치 필요, 데이터베이스 생성 필요
```bash
# MySQL은 이렇게 해야 함
mysql -u root -p
CREATE DATABASE privalert;
# 별도 설치/설정 필요
```

**SQLAlchemy (SQLite)**: **아무것도 설치 안 해도 됨!** 파일 하나로 끝
- SQLite는 파일 기반 DB (MySQL처럼 별도 서버 없음)
- `privalert.db` 파일 하나만 생성되면 끝
- 개발/테스트에 완벽

## 초기 설정 (3단계로 끝!)

### 1단계: 의존성 설치
```bash
cd backend
pip install -r requirements.txt
```

### 2단계: SECRET_KEY 생성 (한 번만)
```bash
python scripts/generate_secret_key.py
```
출력된 키를 복사해서 `.env` 파일에 추가:
```bash
FLASK_SECRET_KEY=복사한_키_여기에_붙여넣기
```

### 3단계: DB 생성 및 초기 데이터 넣기
```bash
python scripts/seed_db.py
```

**끝!** 이제 서버 실행하면 됩니다:
```bash
python wsgi.py
```

## MySQL처럼 사용하고 싶다면?

MySQL을 사용하고 싶다면 `.env` 파일에만 추가하면 됩니다:

```bash
# .env 파일에 추가
DATABASE_URL=mysql+pymysql://사용자명:비밀번호@localhost:3306/privalert
```

그리고 MySQL에 데이터베이스만 미리 생성:
```sql
CREATE DATABASE privalert CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

그러면 자동으로 MySQL 사용합니다.

## 현재 설정 (SQLite - 기본값)

현재는 별도 설정 없이 SQLite 사용:
- DB 파일: `backend/privalert.db` (자동 생성됨)
- 설치 필요 없음
- 설정 필요 없음

## 테스트 방법

```bash
# 1. 회원가입
curl -X POST http://localhost:5000/api/v1/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"email":"test@test.com","password":"test1234"}'

# 2. 로그인
curl -X POST http://localhost:5000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@test.com","password":"test1234"}' \
  -c cookies.txt

# 3. 내 정보 확인
curl -X GET http://localhost:5000/api/v1/auth/me -b cookies.txt
```

## 문제 해결

### "No module named 'flask_sqlalchemy'"
→ `pip install -r requirements.txt` 실행

### "privalert.db 파일이 안 생겨요"
→ 서버를 한 번 실행하면 자동 생성됨 (또는 `python scripts/seed_db.py`)

### "role이 없다고 에러"
→ `python scripts/seed_db.py` 실행

