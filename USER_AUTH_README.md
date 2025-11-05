# 사용자 인증 시스템 (HTTP 전용 환경)

## ⚠️ 중요 안내

**이 시스템은 HTTP 전용 환경에서 동작합니다. HTTPS가 적용되지 않았으므로 보안에 취약할 수 있습니다.**

- 운영 환경에서는 **반드시 HTTPS로 전환**해야 합니다
- 자세한 전환 가이드는 `SECURITY.md`의 "HTTPS 전환 체크리스트" 섹션을 참조하세요
- HTTP 환경에서의 위험 사항은 `SECURITY.md`를 확인하세요

---

## 개요

이 프로젝트는 HTTP 전용 환경에서 작동하는 안전한 사용자 인증 시스템을 제공합니다.

### 주요 기능

- **회원가입 및 이메일 검증**
- **로그인/로그아웃** (세션 기반)
- **비밀번호 재설정**
- **마이페이지** (프로필 수정, 비밀번호 변경)
- **MFA (Multi-Factor Authentication)** - TOTP 기반
- **세션 관리** (세션 목록, 개별/전체 로그아웃)
- **계정 삭제** (7일 유예 기간)

### 보안 조치

- **Argon2id 비밀번호 해싱** (권장 파라미터)
- **토큰 해시 저장** (원문은 DB에 저장하지 않음)
- **CSRF 보호** (Double Submit Cookie + 서버 세션 기반)
- **Rate Limiting** (IP/계정 기반)
- **세션 회전** 및 만료 관리
- **감사 로그** (모든 중요한 이벤트 기록)
- **XSS 방어** (입력 검증, HTML 이스케이프)
- **CORS 제한** (허용된 오리진만)

---

## 설치 및 설정

### 1. 환경 변수 설정

`.env` 파일에 다음 변수를 추가하세요:

```bash
# 암호화 키 (MFA 시크릿 암호화용)
# Fernet 키 생성: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
ENCRYPTION_KEY=your-fernet-key-here

# 이메일 발송 설정 (선택사항)
# SMTP_SERVER=smtp.gmail.com
# SMTP_PORT=587
# SMTP_USER=your-email@gmail.com
# SMTP_PASSWORD=your-app-password
# SMTP_FROM=noreply@privalert.com
```

### 2. 의존성 설치

```bash
cd backend
pip install -r requirements.txt
```

필요한 패키지:
- `argon2-cffi` - Argon2id 비밀번호 해싱
- `pyotp` - TOTP (MFA)
- `qrcode[pil]` - QR 코드 생성
- `cryptography` - 암호화

### 3. 데이터베이스 초기화

```bash
cd backend
python wsgi.py
```

서버 시작 시 자동으로 테이블이 생성됩니다.

---

## API 엔드포인트

### 인증 (Authentication)

#### 회원가입
```
POST /api/v1/auth/signup
Body: { "email": "...", "password": "..." }
Response: { "success": true, "message": "...", "data": {...} }
```

#### 이메일 검증
```
GET /api/v1/auth/verify?token=...
Response: { "success": true, "message": "..." }
```

#### 로그인
```
POST /api/v1/auth/login
Body: { "email": "...", "password": "...", "totp": "..." (선택) }
Response: { "success": true, "data": { "user": {...}, "csrf_token": "...", "session_id": "..." } }
Set-Cookie: session_id=..., session_token=...
```

#### 로그아웃
```
POST /api/v1/auth/logout
Response: { "success": true, "message": "..." }
```

#### 비밀번호 재설정 요청
```
POST /api/v1/auth/request-reset
Body: { "email": "..." }
Response: { "success": true, "message": "..." }
```

#### 비밀번호 재설정
```
POST /api/v1/auth/reset
Body: { "token": "...", "newPassword": "..." }
Response: { "success": true, "message": "..." }
```

### 사용자 프로필 (User Profile)

#### 프로필 조회
```
GET /api/v1/user/me
Headers: Cookie: session_id=..., session_token=...
Response: { "success": true, "data": {...} }
```

#### 프로필 수정
```
PATCH /api/v1/user/me
Headers: X-CSRF-Token: ...
Body: { "email": "..." (선택), "csrf_token": "..." }
Response: { "success": true, "data": {...} }
```

#### 비밀번호 변경
```
POST /api/v1/user/password-change
Headers: X-CSRF-Token: ...
Body: { "currentPassword": "...", "newPassword": "...", "csrf_token": "..." }
Response: { "success": true, "message": "..." }
```

#### 세션 목록 조회
```
GET /api/v1/user/sessions
Response: { "success": true, "data": { "sessions": [...], "current_session_id": "..." } }
```

#### 특정 세션 무효화
```
DELETE /api/v1/user/sessions/<session_id>
Headers: X-CSRF-Token: ...
Body: { "csrf_token": "..." }
Response: { "success": true, "message": "..." }
```

#### 모든 세션 무효화
```
POST /api/v1/user/sessions/revoke-all
Headers: X-CSRF-Token: ...
Body: { "csrf_token": "..." }
Response: { "success": true, "message": "..." }
```

#### 계정 삭제 요청
```
POST /api/v1/user/delete-account
Headers: X-CSRF-Token: ...
Body: { "password": "...", "csrf_token": "..." }
Response: { "success": true, "message": "..." }
```

### MFA (Multi-Factor Authentication)

#### MFA 활성화
```
POST /api/v1/user/mfa/enable
Headers: X-CSRF-Token: ...
Body: { "csrf_token": "..." }
Response: { "success": true, "data": { "secret": "...", "qr_code": "...", "backup_codes": [...] } }
```

#### MFA 활성화 확인
```
POST /api/v1/user/mfa/confirm
Headers: X-CSRF-Token: ...
Body: { "totp": "...", "csrf_token": "..." }
Response: { "success": true, "message": "..." }
```

#### MFA 비활성화
```
POST /api/v1/user/mfa/disable
Headers: X-CSRF-Token: ...
Body: { "password": "...", "csrf_token": "..." }
Response: { "success": true, "message": "..." }
```

---

## 보안 주의사항

### HTTP 환경의 제한사항

1. **쿠키 탈취 위험**: HTTP 환경에서는 네트워크 스니핑으로 쿠키를 탈취할 수 있습니다
   - 완화 조치: `HttpOnly`, `SameSite=Strict` 플래그 적용
   - 권장: HTTPS 전환

2. **HSTS 미적용**: HTTP 환경에서는 HSTS를 설정하지 않습니다
   - 자세한 내용은 `SECURITY.md` 참조

3. **Secure 플래그 미설정**: HTTP 환경에서는 `Secure` 쿠키 플래그를 사용하지 않습니다
   - HTTPS 전환 시 `Secure` 플래그를 활성화해야 합니다

### 보안 권장사항

1. **MFA 활성화**: 가능한 모든 계정에 MFA를 활성화하세요
2. **강력한 비밀번호**: 최소 12자, 대소문자, 숫자, 특수문자 포함
3. **세션 관리**: 사용하지 않는 세션은 정기적으로 무효화하세요
4. **HTTPS 전환**: 운영 환경에서는 반드시 HTTPS로 전환하세요

---

## 개발 환경 실행

```bash
# 백엔드 실행
cd backend
python wsgi.py

# 또는 Docker 사용
docker-compose up -d
```

---

## 테스트

```bash
# 백엔드 테스트
cd backend
pytest tests/
```

---

## 문제 해결

### Argon2id 설치 오류
```bash
# Windows
pip install argon2-cffi-binary

# Linux/Mac
pip install argon2-cffi
```

### 이메일 발송 오류
- `.env` 파일에 SMTP 설정이 있는지 확인하세요
- 개발 환경에서는 이메일 발송이 비활성화될 수 있습니다 (토큰은 응답에 포함)

---

## 참고 문서

- `SECURITY.md` - 보안 조치 상세 설명 및 HTTPS 전환 체크리스트
- `README.md` - 프로젝트 전체 개요

