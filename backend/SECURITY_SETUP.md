# 보안 설정 가이드 및 체크리스트

## 시큐어코딩 가이드 준수 사항

### ✅ 구현 완료 항목

#### 1. 권한 관리 (RBAC)
- ✅ 권한은 서버 측(DB)에서 판단
- ✅ 쿠키에는 세션 ID만 저장 (role 정보는 포함하지 않음)
- ✅ Flask-Login을 사용한 세션 관리

#### 2. 비밀번호 보안
- ✅ 솔트+해시 저장 (werkzeug.security의 PBKDF2 사용)
- ✅ 비밀번호는 평문으로 저장하지 않음
- ✅ 비밀번호 변경 시 재인증 필수

#### 3. 세션/쿠키 보안
- ✅ `SESSION_COOKIE_HTTPONLY = True` (JS 접근 차단)
- ✅ `SESSION_COOKIE_SECURE = True` (프로덕션 환경, HTTPS 전용)
- ✅ `SESSION_COOKIE_SAMESITE = "Lax"` (CSRF 추가 방어)
- ✅ 최소 보존 시간 설정 (1시간)

#### 4. CSRF 방어
- ✅ Flask-WTF의 CSRFProtect 적용
- ✅ 모든 POST 요청에 CSRF 토큰 검증

#### 5. 레이트 리미팅
- ✅ Flask-Limiter 적용
- ✅ 로그인: 5회/분
- ✅ 비밀번호 변경: 5회/시간
- ✅ 회원가입: 10회/분
- ✅ 탈퇴: 3회/시간

#### 6. SQL 인젝션 방어
- ✅ SQLAlchemy ORM 사용 (모든 쿼리 자동 바인딩)
- ✅ 직접 문자열 결합 금지

#### 7. 재인증
- ✅ 비밀번호 변경 시 현재 비밀번호 확인
- ✅ 탈퇴 시 비밀번호 재확인

#### 8. 로깅 및 감사
- ✅ 관리자 액션 로깅
- ✅ 로그인 실패 시도 기록
- ✅ 민감 정보(비밀번호/토큰)는 로그에 기록하지 않음

#### 9. 환경변수 관리
- ✅ SECRET_KEY는 환경변수로 주입
- ✅ DATABASE_URL은 환경변수로 주입
- ✅ 운영 환경에서 하드코딩 금지

## 환경변수 설정

`.env` 파일 또는 환경변수에 다음을 설정:

```bash
# Flask 설정
FLASK_SECRET_KEY=your-secret-key-here  # secrets.token_hex(32)로 생성
FLASK_ENV=development  # 또는 production

# 데이터베이스
DATABASE_URL=sqlite:///privalert.db  # 개발 환경
# DATABASE_URL=postgresql://user:pass@localhost/privalert  # 프로덕션

# 관리자 계정 (초기 시드용)
ADMIN_EMAIL=admin@privalert.com
ADMIN_PASSWORD=your-secure-password

# CORS 설정
CORS_ORIGINS=http://localhost:3000
```

## 초기 설정 단계

### 1. 의존성 설치

```bash
pip install -r requirements.txt
```

### 2. 환경변수 설정

`.env` 파일 생성 또는 환경변수 설정 (위 참조)

### 3. 마이그레이션 (선택사항)

```bash
# 마이그레이션 디렉토리 초기화
flask db init

# 초기 마이그레이션 생성
flask db migrate -m "init user/role models"

# 마이그레이션 적용
flask db upgrade
```

또는 개발 환경에서는 자동으로 테이블이 생성됩니다.

### 4. 초기 데이터 시드

```bash
python scripts/seed_db.py
```

이 스크립트는:
- `admin` 및 `user` 역할 생성
- 초기 관리자 계정 생성 (환경변수 또는 기본값 사용)

## API 엔드포인트

### 인증 (`/api/v1/auth`)

- `POST /api/v1/auth/signup` - 회원가입
- `POST /api/v1/auth/login` - 로그인
- `POST /api/v1/auth/logout` - 로그아웃
- `GET /api/v1/auth/me` - 현재 사용자 정보
- `POST /api/v1/auth/change-password` - 비밀번호 변경
- `POST /api/v1/auth/withdraw` - 회원 탈퇴

### 관리자 (`/api/v1/admin`)

모든 관리자 엔드포인트는 관리자 권한 필요

- `GET /api/v1/admin/dashboard` - 대시보드
- `GET /api/v1/admin/users` - 사용자 목록
- `POST /api/v1/admin/users/<id>/toggle-active` - 사용자 활성화/비활성화
- `POST /api/v1/admin/users/<id>/roles` - 역할 부여
- `DELETE /api/v1/admin/users/<id>/roles/<role_id>` - 역할 제거

## 보안 체크리스트

### ✅ 인증/인가
- [x] 비밀번호는 솔트+해시로 저장
- [x] 권한은 서버 측에서 판단
- [x] 쿠키에는 세션 ID만 저장
- [x] 재인증: 비밀번호 변경/탈퇴 시 필수

### ✅ 세션/쿠키
- [x] HttpOnly 설정
- [x] Secure 설정 (프로덕션)
- [x] SameSite 설정
- [x] 최소 보존 시간

### ✅ CSRF 방어
- [x] Flask-WTF CSRFProtect 적용
- [x] 모든 POST 요청 검증

### ✅ SQL 인젝션 방어
- [x] ORM 사용 (SQLAlchemy)
- [x] 직접 문자열 결합 금지

### ✅ 레이트 리미팅
- [x] 로그인/가입 엔드포인트 제한
- [x] 브루트포스 공격 방지

### ✅ 로깅
- [x] 관리자 액션 기록
- [x] 로그인 실패 기록
- [x] 민감 정보 마스킹

### ✅ 환경변수
- [x] SECRET_KEY 환경변수로 주입
- [x] DB 비밀번호 환경변수로 주입
- [x] 하드코딩 금지

## 테스트 시나리오

### 1. 회원가입 → 로그인 → 세션 확인
```bash
# 회원가입
curl -X POST http://localhost:5000/api/v1/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"test1234"}'

# 로그인 (세션 쿠키 확인)
curl -X POST http://localhost:5000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"test1234"}' \
  -c cookies.txt

# 현재 사용자 정보
curl -X GET http://localhost:5000/api/v1/auth/me \
  -b cookies.txt
```

### 2. 쿠키 확인
- 개발자 도구에서 쿠키 확인
- `HttpOnly` 플래그 확인
- `Secure` 플래그 확인 (프로덕션)
- 권한 정보가 쿠키에 없는지 확인

### 3. CSRF 보호 확인
- CSRF 토큰 없이 POST 요청 시 차단 확인

### 4. 재인증 확인
- 비밀번호 변경 시 현재 비밀번호 불일치 테스트
- 탈퇴 시 비밀번호 재확인 테스트

### 5. 권한 확인
- 관리자 URL에 일반 사용자 접근 시 403 확인
- 일반 사용자로 로그인 후 `/api/v1/admin/dashboard` 접근 시도

## 추가 보안 권장사항

### 운영 환경
1. **HTTPS 강제**: 모든 통신은 HTTPS로
2. **인증서 검증**: 적절한 인증서 설정
3. **DB 최소권한**: 애플리케이션 계정은 DDL 권한 제한
4. **비밀관리**: AWS Secrets Manager, HashiCorp Vault 등 사용
5. **모니터링**: 로그인 실패, 비정상적인 접근 패턴 모니터링

### 코드 리뷰 체크리스트
- [ ] SQL 쿼리에 직접 문자열 결합 없음
- [ ] 비밀번호/토큰이 로그에 기록되지 않음
- [ ] 모든 관리자 경로에 인가 검사 있음
- [ ] 민감 정보가 주석/리포지토리에 노출되지 않음
- [ ] 환경변수를 통한 설정 주입

## 문제 해결

### DB 연결 오류
- `DATABASE_URL` 환경변수 확인
- SQLite 파일 권한 확인

### CSRF 오류
- API 전용인 경우 CSRF 예외 설정 가능:
```python
csrf.exempt(auth_bp)  # Blueprint 전체 예외
```

### 레이트 리미팅 오류
- 메모리 기반이므로 서버 재시작 시 리셋됨
- 프로덕션에서는 Redis 등 사용 권장

