# 보안 가이드 (HTTP 전용 환경)

## ⚠️ 중요 경고

**이 시스템은 HTTP 전용 환경에서 동작합니다. HTTPS가 적용되지 않았으므로 보안에 취약할 수 있습니다.**

- 운영 환경에서는 **반드시 HTTPS로 전환**해야 합니다
- HTTP 환경에서의 위험 사항을 이해하고 적절한 보완 조치를 취하세요

---

## HTTP 전용 환경의 위험

### 1. 패킷 스니핑 (Man-in-the-Middle 공격)

**위험**: HTTP 통신은 암호화되지 않으므로 네트워크 상에서 패킷을 가로채면 모든 데이터를 볼 수 있습니다.

**영향**:
- 비밀번호 평문 노출
- 세션 쿠키 탈취
- 개인정보 노출
- CSRF 토큰 노출

**완화 조치** (현재 구현):
- `HttpOnly` 쿠키 플래그 (JavaScript 접근 방지)
- `SameSite=Strict` 쿠키 플래그 (CSRF 공격 방지)
- 세션 토큰 회전
- Double Submit Cookie 패턴 (CSRF 보호)
- Rate Limiting (무차별 대입 공격 방지)

**권장 해결책**: HTTPS 전환

### 2. 쿠키 탈취

**위험**: HTTP 환경에서는 네트워크 스니핑으로 쿠키를 탈취할 수 있습니다.

**완화 조치** (현재 구현):
- `HttpOnly` 플래그로 JavaScript 접근 차단
- `SameSite=Strict` 플래그로 크로스 사이트 요청 차단
- 세션 만료 시간 짧게 설정 (24시간)
- 세션 회전 지원

**권장 해결책**: HTTPS 전환 + `Secure` 플래그 활성화

### 3. HSTS 미적용

**위험**: HSTS (HTTP Strict Transport Security)를 적용하지 않았으므로, HTTPS로 전환 시에도 일시적으로 HTTP로 접근할 수 있습니다.

**완화 조치**:
- HSTS는 HTTP 환경에서 설정하지 않음 (현재 구현)
- HTTPS 전환 시 HSTS 활성화 필요

**권장 해결책**: HTTPS 전환 후 HSTS 활성화

---

## 구현된 보안 조치

### 1. 비밀번호 보안

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

### 2. 토큰 보안

- **토큰 해시 저장**: 원문 토큰은 DB에 저장하지 않고 SHA256 해시만 저장
- **단발성 토큰**: 사용 후 즉시 무효화
- **만료 시간**: 이메일 검증 24시간, 비밀번호 재설정 1시간
- **예측 불가능한 토큰**: `secrets.token_urlsafe()` 사용

### 3. 세션 보안

- **예측 불가능한 세션 ID**: `secrets.token_urlsafe(32)` 사용
- **Double Submit Cookie**: 세션 ID + 세션 토큰으로 검증
- **세션 회전**: 주기적 세션 갱신 지원
- **세션 만료**: 24시간 후 자동 만료
- **세션 관리**: 사용자가 세션 목록 조회 및 무효화 가능

### 4. CSRF 보호

- **Double Submit Cookie 패턴**: 쿠키와 요청 헤더의 토큰 비교
- **서버 세션 기반 CSRF 토큰**: 사용자별 토큰 생성 및 검증
- **일회용 토큰**: 사용 후 즉시 무효화
- **SameSite=Strict**: 크로스 사이트 요청 차단

### 5. Rate Limiting

- **IP 기반 제한**: Flask-Limiter 사용
- **계정 기반 제한**: 로그인 실패 5회 시 30분 잠금
- **엔드포인트별 제한**:
  - 회원가입: 5회/시간
  - 로그인: 10회/시간
  - 비밀번호 재설정 요청: 5회/시간

### 6. 입력 검증

- **서버 측 검증**: 모든 입력값 서버에서 검증
- **이메일 형식 검증**: 정규식 사용
- **XSS 방어**: HTML 이스케이프
- **SQL Injection 방지**: SQLAlchemy ORM 사용
- **Path Traversal 방지**: 파일 경로 검증

### 7. MFA (Multi-Factor Authentication)

- **TOTP (RFC 6238)**: Google Authenticator, Authy 등 호환
- **복구 코드**: 10개의 일회용 복구 코드 제공
- **시크릿 암호화**: Fernet (symmetric encryption) 사용
- **QR 코드**: Base64 인코딩된 이미지 제공

### 8. 감사 로그

- **모든 중요한 이벤트 기록**:
  - 로그인/로그아웃
  - 비밀번호 변경
  - 계정 삭제 요청
  - MFA 활성화/비활성화
  - 세션 무효화
- **민감 정보 제외**: 비밀번호, 토큰 등은 로그에 기록하지 않음
- **보관 기간**: 90일 (설정 가능)

### 9. 세션 쿠키 설정 (HTTP 환경)

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

### 10. HSTS 미설정

**현재 상태**: HSTS 헤더를 설정하지 않음

**이유**: HTTP 환경에서는 HSTS를 설정하면 안 됩니다
- HSTS는 HTTPS 환경에서만 의미가 있음
- HTTP 환경에서 HSTS를 설정하면 브라우저가 HTTPS로 강제 리다이렉트 시도
- HTTPS가 없으면 사이트 접근 불가

**HTTPS 전환 시 설정 필요**:
```
Strict-Transport-Security: max-age=31536000; includeSubDomains; preload
```

---

## HTTPS 전환 체크리스트

운영 환경에서 HTTPS로 전환할 때 다음 항목을 확인하세요:

### 1. SSL/TLS 인증서 설정

- [ ] SSL/TLS 인증서 발급 (Let's Encrypt, 상용 인증서 등)
- [ ] 인증서 파일 경로 설정
- [ ] 인증서 갱신 자동화 (Let's Encrypt의 경우 certbot 사용)

### 2. 쿠키 설정 변경

- [ ] `SESSION_COOKIE_SECURE = True` 설정
- [ ] `JWT_COOKIE_SECURE = True` 설정
- [ ] 세션 쿠키 설정에서 `Secure` 플래그 활성화
- [ ] 모든 쿠키에 `Secure` 플래그 추가

**변경 위치**:
- `backend/app/__init__.py`: `SESSION_COOKIE_SECURE`, `JWT_COOKIE_SECURE`
- `backend/app/routes/auth_routes.py`: `response.set_cookie()` 호출 시 `secure=True`

### 3. HSTS 활성화

- [ ] `Strict-Transport-Security` 헤더 추가
- [ ] `max-age` 설정 (권장: 31536000 = 1년)
- [ ] `includeSubDomains` 옵션 고려
- [ ] `preload` 옵션 고려 (HSTS Preload List 등록 시)

**변경 위치**:
- `backend/app/__init__.py`: `set_security_headers()` 함수

### 4. HTTP → HTTPS 리다이렉트

- [ ] 모든 HTTP 요청을 HTTPS로 리다이렉트
- [ ] Nginx/Apache 설정에서 리다이렉트 규칙 추가
- [ ] 프론트엔드에서 HTTPS URL 사용

**Nginx 예시**:
```nginx
server {
    listen 80;
    server_name example.com;
    return 301 https://$server_name$request_uri;
}
```

### 5. CORS 설정 업데이트

- [ ] CORS 허용 오리진을 HTTPS URL로 변경
- [ ] `.env` 파일의 `CORS_ORIGINS` 업데이트

**변경 위치**:
- `.env`: `CORS_ORIGINS=https://example.com`

### 6. 프론트엔드 설정

- [ ] API 베이스 URL을 HTTPS로 변경
- [ ] 모든 외부 리소스(이미지, 스크립트 등)를 HTTPS로 로드
- [ ] Mixed Content 경고 확인

**변경 위치**:
- `frontend/.env`: `VITE_API_BASE_URL=https://api.example.com`

### 7. 데이터베이스 연결

- [ ] 데이터베이스 연결이 내부 네트워크인지 확인
- [ ] 외부 연결이 필요한 경우 SSL/TLS 사용

### 8. 보안 헤더 재확인

- [ ] `X-Content-Type-Options: nosniff`
- [ ] `X-Frame-Options: DENY`
- [ ] `X-XSS-Protection: 1; mode=block`
- [ ] `Referrer-Policy: strict-origin-when-cross-origin`
- [ ] `Content-Security-Policy` 업데이트 (필요 시)

### 9. 테스트

- [ ] HTTPS 연결 테스트
- [ ] 쿠키가 `Secure` 플래그로 전송되는지 확인
- [ ] HSTS 헤더가 설정되는지 확인
- [ ] HTTP → HTTPS 리다이렉트 테스트
- [ ] 모든 API 엔드포인트 HTTPS로 작동하는지 확인
- [ ] Mixed Content 경고 없는지 확인

### 10. 모니터링

- [ ] SSL/TLS 인증서 만료 모니터링 설정
- [ ] HTTPS 연결 실패 모니터링
- [ ] 보안 이벤트 로깅 강화

---

## 보안 검사 체크리스트

### 배포 전 검사

- [ ] 의존성 취약점 스캔 (`pip-audit`, `snyk`, `trivy`)
- [ ] 정적 분석 (`bandit`, `pylint`, `mypy`)
- [ ] 코드 리뷰 (보안 관점)
- [ ] 펜테스팅 (선택사항)

### 정기 검사

- [ ] 의존성 업데이트 및 취약점 확인 (월 1회)
- [ ] 보안 패치 적용
- [ ] 로그 분석 (비정상 활동 확인)
- [ ] 감사 로그 검토

---

## 보안 명령어

### 의존성 취약점 스캔

```bash
# pip-audit (Python)
pip install pip-audit
pip-audit

# trivy (Docker 이미지)
trivy image privalert:1.0

# snyk (종합)
snyk test
```

### 정적 분석

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

## 추가 보안 권장사항

### 1. 프록시에서 TLS 종료

- **권장**: 리버스 프록시(Nginx, HAProxy)에서 TLS 종료
- **이점**: 애플리케이션 서버는 HTTP로 통신 (내부 네트워크)
- **주의**: 내부 네트워크 보안 강화 필요

### 2. WAF (Web Application Firewall)

- **권장**: ModSecurity, Cloudflare 등 사용
- **이점**: SQL Injection, XSS 등 공격 차단

### 3. 이메일 알림

- **권장**: 중요한 이벤트(비밀번호 변경, 새 디바이스 로그인 등) 시 이메일 알림
- **현재 상태**: 구현 예정 (TODO)

### 4. CAPTCHA

- **권장**: 비정상 활동(연속 실패 등) 시 CAPTCHA 강제
- **현재 상태**: 구현 예정 (TODO)

### 5. Redis 기반 Rate Limiting

- **현재**: 메모리 기반 (서버 재시작 시 초기화)
- **권장**: Redis 기반으로 전환 (분산 환경 대응)

---

## 참고 자료

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [OWASP Cheat Sheet Series](https://cheatsheetseries.owasp.org/)
- [Argon2id 권장 파라미터](https://github.com/P-H-C/phc-winner-argon2)
- [TOTP (RFC 6238)](https://tools.ietf.org/html/rfc6238)
- [HSTS (RFC 6797)](https://tools.ietf.org/html/rfc6797)

---

## 문의

보안 관련 문의사항이 있으면 이슈를 등록하거나 프로젝트 관리자에게 연락하세요.

