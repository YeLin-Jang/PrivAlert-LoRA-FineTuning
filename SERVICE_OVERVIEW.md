# 🔔 PrivAlert 서비스 개요서

## 📋 서비스 소개

**PrivAlert**는 사용자 맞춤 민감정보 탐지를 위한 AI 기반 텍스트 및 이미지 점검 시스템입니다.  
개인정보가 포함된 텍스트, 이미지, 비디오를 분석하여 민감 정보를 탐지하고, 안전한 수정 문구를 제안하며, 관련 법령 및 보안 교육 자료를 제공합니다.

**팀명**: 도전!보안벨  
**컨셉**: "당신의 개인정보 보호 분석 시스템"

---

## 🎯 핵심 기능

### 1. 통합 민감정보 분석
- **텍스트 분석**: 정형 데이터(전화번호, 이메일, 주민등록번호 등) 및 비정형 데이터(이름, 주소, 직장명 등) 탐지
- **이미지 분석**: 얼굴 검출, 손가락 검출, OCR 텍스트 추출
- **비디오 분석**: 프레임 추출, 오디오 추출, 동영상 내 민감정보 탐지
- **이미지 메타데이터 제거**: EXIF/GPS 정보 제거를 통한 위치 정보 보호

### 2. AI 기반 교육 콘텐츠 생성
- **Claude API 기반 프롬프팅**: 자연스러운 수정 문장 생성
- **법령 정보 제공**: 개인정보보호법, 정보통신망법 등 관련 법령 조항 상세 설명
- **위험 시나리오 분석**: 민감정보 노출 시 발생 가능한 구체적 위험 상황 설명
- **보안 대응 가이드**: 실무에서 즉시 적용 가능한 보안 조치 방안 제시

### 3. 사용자 맞춤 필터링
- **개인화된 탐지 설정**: 사용자별로 탐지하고 싶은 항목 선택 가능
- **설정 저장**: 데이터베이스에 저장되어 다음 분석 시 자동 적용
- **분석 기록 관리**: 분석 이력 조회 및 관리

### 4. 안전한 사용자 인증 시스템
- **이메일 인증**: SMTP 기반 이메일 인증 토큰 발송 및 검증
- **보안 강화**: Argon2id 비밀번호 해싱, MFA(TOTP) 지원
- **세션 관리**: 세션 추적, 개별/전체 로그아웃 기능
- **CSRF 보호**: Double Submit Cookie 패턴 적용

### 5. 관리자 기능
- **사용자 관리**: 사용자 목록 조회, 상태 변경, 권한 관리
- **분석 로그 관리**: 탐지 이력 조회 및 통계
- **감사 로그**: 모든 중요 이벤트 기록 및 조회

---

## 🏗️ 기술 스택

### Frontend
- **React 18** + **TypeScript**
- **Vite**: 빌드 도구
- **React Router**: 라우팅
- **Axios**: HTTP 클라이언트

### Backend
- **Flask**: 웹 프레임워크
- **MySQL**: 데이터베이스
- **SQLAlchemy**: ORM
- **JWT**: 관리자 인증

### AI/ML
- **MediaPipe**: 얼굴/손가락 검출
- **EasyOCR**: OCR 텍스트 추출
- **Claude API (Anthropic)**: 교육 콘텐츠 생성
- **KoBERT**: 한국어 개체명 인식 (NER)

### 보안
- **Argon2id**: 비밀번호 해싱
- **Fernet (cryptography)**: 토큰 메타데이터 암호화
- **TOTP (pyotp)**: 다단계 인증
- **CSRF Protection**: Double Submit Cookie 패턴

---

## 📊 시스템 아키텍처

```
┌─────────────────┐
│   Frontend      │
│  (React + TS)   │
└────────┬────────┘
         │
         │ HTTP/REST API
         │
┌────────▼────────┐
│    Backend      │
│    (Flask)      │
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
┌───▼───┐ ┌──▼──────┐
│ MySQL │ │ AI 모델 │
│       │ │ (NER,   │
│       │ │  OCR)   │
└───────┘ └─────────┘
         │
    ┌────▼────┐
    │ Claude  │
    │   API   │
    └─────────┘
```

---

## 🔐 보안 기능

### 인증 및 권한 관리
- ✅ **이메일 인증 필수**: 회원가입 시 이메일 인증 완료 후 계정 생성
- ✅ **비밀번호 강도 검증**: 최소 12자, 대소문자/숫자/특수문자 포함
- ✅ **Argon2id 해싱**: 최신 비밀번호 해싱 알고리즘
- ✅ **MFA 지원**: TOTP 기반 2단계 인증
- ✅ **세션 관리**: 세션 추적, 회전, 만료 관리
- ✅ **관리자 권한 분리**: 일반 사용자와 관리자 인증 시스템 분리

### 데이터 보안
- ✅ **토큰 암호화**: 이메일 인증 토큰 메타데이터 Fernet 암호화
- ✅ **SQL Injection 방지**: SQLAlchemy ORM 사용
- ✅ **XSS 방지**: 입력값 검증 및 이스케이프
- ✅ **CSRF 보호**: Double Submit Cookie 패턴
- ✅ **Rate Limiting**: 무차별 대입 공격 방지

### 네트워크 보안
- ✅ **보안 헤더**: CSP, X-Frame-Options, X-Content-Type-Options 등
- ✅ **CORS 설정**: 명시적 origin 허용
- ✅ **Session Cookie**: HttpOnly, SameSite=Strict 설정

---

## 📧 이메일 인증 시스템

### SMTP 설정
- **지원 SMTP 서비스**: Gmail, 네이버, 다음, Outlook 등
- **보안**: TLS 암호화 사용 (포트 587)
- **HTML/텍스트 이중 형식**: 모든 이메일 클라이언트 지원

### 인증 프로세스
1. 사용자가 회원가입 요청
2. 시스템이 이메일 인증 토큰 생성 (24시간 유효)
3. SMTP를 통해 인증 링크가 포함된 이메일 발송
4. 사용자가 이메일의 링크 클릭
5. 토큰 검증 완료 후 계정 생성

### 보안 특징
- **토큰 기반**: 예측 불가능한 토큰 생성 (`secrets.token_urlsafe`)
- **토큰 해시 저장**: DB에는 SHA256 해시만 저장
- **메타데이터 암호화**: 이메일/비밀번호 해시는 Fernet으로 암호화
- **단발성**: 사용 후 즉시 무효화
- **만료 시간**: 24시간 후 자동 만료

---

## 🤖 AI 프롬프팅 시스템

### Claude API 통합
- **모델**: Claude Sonnet 4.5 (기본값, 환경 변수로 변경 가능)
- **2단계 파이프라인**: Rewrite → Critique
- **캐싱**: 24시간 TTL 메모리 캐시
- **폴백 모드**: API 키 없어도 기본 기능 작동

### 프롬프트 특징
- **법령 인용 형식 강제**: "법령명 제XX조 제X항" 형식으로 정확한 법령 정보 제공
- **전문 용어 사용**: 스미싱, 피싱, 사칭, 사회공학적 공격 등
- **상세한 위험 시나리오**: 단계별 공격 과정 및 피해 내용 설명
- **실무 적용 가능한 보안 팁**: 구체적인 기술적 조치 방안 제시

### 생성되는 콘텐츠
- **수정 문장**: 마스킹된 텍스트를 자연스러운 문장으로 수정
- **법령 요약**: 관련 법령 조항 및 벌칙 내용
- **위험 시나리오**: 구체적이고 전문적인 위험 상황 설명
- **보안 대응 가이드**: 실무 적용 가능한 보안 조치 방안

---

## 👥 사용자 관리

### 일반 사용자
- **회원가입**: 이메일 인증 필수
- **마이페이지**: 프로필 수정, 필터링 설정, 분석 기록 조회
- **로그인 필수 기능**: 분석 페이지, 마이페이지 접근 시 로그인 필요

### 관리자
- **별도 인증 시스템**: JWT 기반 관리자 인증
- **접근 제어**: 일반 사용자는 관리자 페이지 접근 불가
- **기능**: 사용자 관리, 분석 로그 조회, 통계 조회

---

## 📈 데이터베이스 구조

### 주요 테이블
- **users**: 사용자 정보 (이메일, 비밀번호 해시, 이메일 인증 상태 등)
- **tokens**: 이메일 인증/비밀번호 재설정 토큰
- **user_sessions**: 사용자 세션 관리
- **user_filtering_settings**: 사용자별 필터링 설정
- **audit_logs**: 감사 로그
- **admin_users**: 관리자 계정

### 보안 특징
- **비밀번호 해시**: Argon2id 사용
- **토큰 메타데이터 암호화**: Fernet 암호화
- **세션 추적**: 세션 ID, IP 주소, User-Agent 기록
- **감사 로그**: 모든 중요 이벤트 기록

---

## 🔧 환경 변수 설정

### 필수 환경 변수
```bash
# Flask 설정
FLASK_SECRET_KEY=your-secret-key-minimum-32-characters
JWT_SECRET_KEY=your-jwt-secret-key

# MySQL 설정
MYSQL_HOST=mysql (Docker) 또는 localhost (로컬)
MYSQL_PORT=3306
MYSQL_DATABASE=privalert
MYSQL_USER=privalert_user
MYSQL_PASSWORD=your-password
MYSQL_ROOT_PASSWORD=your-root-password

# 암호화 키 (토큰 메타데이터 암호화)
ENCRYPTION_KEY=your-fernet-key
```

### 선택 환경 변수
```bash
# SMTP 설정 (이메일 인증)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_EMAIL=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM=noreply@privalert.com

# Claude API (프롬프팅)
ANTHROPIC_API_KEY=sk-ant-...
CLAUDE_MODEL=claude-sonnet-4-5-20250929

# CORS 설정
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
```

---

## 🚀 배포 및 실행

### Docker (권장)
```bash
# 프로젝트 루트에서
docker-compose up -d --build
```

### 로컬 개발
```bash
# 백엔드
cd backend
python wsgi.py

# 프론트엔드
cd frontend
npm run dev
```

---

## 📝 주요 API 엔드포인트

### 인증
- `POST /api/v1/auth/signup` - 회원가입 (이메일 인증 토큰 발송)
- `GET /api/v1/auth/verify?token=...` - 이메일 인증
- `POST /api/v1/auth/login` - 로그인
- `POST /api/v1/auth/logout` - 로그아웃

### 분석
- `POST /api/v1/analyze` - 통합 분석 (이미지 + 텍스트)
- `POST /api/v1/filter/filter` - 텍스트 필터링
- `POST /api/v1/face/detect` - 얼굴 검출
- `POST /api/v1/hand/detect` - 손가락 검출
- `POST /api/v1/ocr/text` - OCR 텍스트 추출

### 사용자
- `GET /api/v1/user/me` - 현재 사용자 정보
- `PATCH /api/v1/user/me` - 프로필 수정
- `GET /api/v1/user/filtering-settings` - 필터링 설정 조회
- `PATCH /api/v1/user/filtering-settings` - 필터링 설정 저장

### 관리자
- `POST /api/v1/admin/auth/login` - 관리자 로그인
- `GET /api/v1/admin/users` - 사용자 목록 조회
- `GET /api/v1/admin/logs/activity` - 활동 로그 조회

---

## 🎨 사용자 인터페이스

### 디자인 컨셉
- **컬러**: 파란색 계열 (#1e3a8a, #3b82f6)
- **스타일**: 모던하고 깔끔한 디자인
- **반응형**: 모바일/태블릿/데스크톱 지원

### 주요 페이지
- **홈페이지**: 서비스 소개 및 브랜드 소개
- **로그인/회원가입**: 이메일 인증 포함
- **분석 페이지**: 파일 업로드 및 분석 결과 표시
- **마이페이지**: 사용자 설정 및 분석 기록
- **관리자 페이지**: 사용자 관리 및 통계

---

## ⚠️ 보안 주의사항

### HTTP 환경 제한사항
현재 시스템은 **HTTP 전용 환경**에서 동작합니다. 프로덕션 환경에서는 **반드시 HTTPS로 전환**해야 합니다.

### 완화 조치
- HttpOnly 쿠키 플래그
- SameSite=Strict 쿠키 플래그
- CSRF 보호 (Double Submit Cookie)
- Rate Limiting
- 입력 검증 및 SQL Injection 방지

### 권장 사항
1. **HTTPS 전환**: SSL/TLS 인증서 적용
2. **Secure 쿠키 플래그**: HTTPS 전환 시 활성화
3. **HSTS 활성화**: HTTPS 전환 후 적용
4. **정기 보안 감사**: 취약점 스캔 및 패치 적용

---

## 📞 지원 및 문의

- **이메일**: support@privalert.com
- **프로젝트**: GitHub Repository
- **API 문서**: http://localhost:5000/api-docs/

---

## 📅 버전 정보

- **현재 버전**: 1.0.0
- **최종 업데이트**: 2025-11-06
- **주요 기능**: 이메일 인증, 사용자 맞춤 필터링, Claude API 프롬프팅, 관리자 페이지

---

**PrivAlert** - 당신의 개인정보 보호 분석 시스템

