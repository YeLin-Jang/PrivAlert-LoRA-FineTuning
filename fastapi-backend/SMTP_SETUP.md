# SMTP 설정 가이드

## .env 파일에 필요한 SMTP 설정

이메일 인증번호를 전송하기 위해 `.env` 파일에 다음 설정을 추가해야 합니다:

```bash
# SMTP 서버 설정
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587

# 발신자 이메일 계정 (SMTP 인증용)
SMTP_EMAIL=your-email@gmail.com
SMTP_PASSWORD=your-app-password

# 발신자 표시 이름 (선택사항)
SMTP_FROM=PrivAlert <noreply@privalert.com>
```

## 각 설정 항목 설명

### 1. SMTP_SERVER
- **설명**: SMTP 서버 주소
- **Gmail 예시**: `smtp.gmail.com`
- **다른 서비스 예시**:
  - Outlook: `smtp-mail.outlook.com`
  - Naver: `smtp.naver.com`
  - Daum: `smtp.daum.net`

### 2. SMTP_PORT
- **설명**: SMTP 포트 번호
- **Gmail 예시**: `587` (TLS 사용)
- **다른 옵션**: `465` (SSL 사용)

### 3. SMTP_EMAIL ⭐ (필수)
- **설명**: **인증 메일을 보내는 이메일 주소**
- **용도**: SMTP 서버에 로그인할 때 사용하는 계정
- **예시**: `your-email@gmail.com`
- **중요**: 이 계정으로 SMTP 서버에 인증해야 합니다

### 4. SMTP_PASSWORD ⭐ (필수)
- **설명**: SMTP_EMAIL 계정의 비밀번호
- **Gmail 사용 시**: 일반 비밀번호가 아닌 **앱 비밀번호**를 사용해야 합니다
- **예시**: `abcd efgh ijkl mnop` (16자리, 공백 없이 입력)

### 5. SMTP_FROM (선택사항)
- **설명**: 이메일 수신자가 보는 "보낸 사람" 이름/주소
- **설정하지 않으면**: `SMTP_EMAIL` 값이 사용됩니다
- **형식 예시**:
  ```
  SMTP_FROM=PrivAlert <noreply@privalert.com>
  ```
  또는 간단하게:
  ```
  SMTP_FROM=noreply@privalert.com
  ```

## Gmail 앱 비밀번호 생성 방법

Gmail을 사용하는 경우, 일반 비밀번호가 아닌 **앱 비밀번호**를 생성해야 합니다:

1. **Google 계정 설정**
   - https://myaccount.google.com 접속
   - 왼쪽 메뉴에서 **보안** 클릭

2. **2단계 인증 활성화** (필수)
   - 2단계 인증이 활성화되어 있어야 앱 비밀번호를 생성할 수 있습니다

3. **앱 비밀번호 생성**
   - 보안 페이지에서 **앱 비밀번호** 클릭
   - 앱 선택: **메일**
   - 기기 선택: **기타(맞춤 이름)** → "PrivAlert" 입력
   - **생성** 클릭

4. **앱 비밀번호 복사**
   - 16자리 비밀번호가 생성됩니다 (예: `abcd efgh ijkl mnop`)
   - 공백 없이 `.env` 파일에 입력: `SMTP_PASSWORD=abcdefghijklmnop`

## 다른 이메일 서비스 설정

### Outlook/Hotmail
```bash
SMTP_SERVER=smtp-mail.outlook.com
SMTP_PORT=587
SMTP_EMAIL=your-email@outlook.com
SMTP_PASSWORD=your-password
```

### Naver
```bash
SMTP_SERVER=smtp.naver.com
SMTP_PORT=587
SMTP_EMAIL=your-email@naver.com
SMTP_PASSWORD=your-password
```

### Daum
```bash
SMTP_SERVER=smtp.daum.net
SMTP_PORT=465
SMTP_EMAIL=your-email@daum.net
SMTP_PASSWORD=your-password
```

## .env 파일 예시

```bash
# 필수 설정
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_EMAIL=myapp@gmail.com
SMTP_PASSWORD=abcdefghijklmnop

# 선택사항 (설정하지 않으면 SMTP_EMAIL이 사용됨)
SMTP_FROM=PrivAlert <noreply@privalert.com>
```

## 테스트 방법

설정이 올바른지 확인하려면:

1. `.env` 파일에 SMTP 설정 추가
2. 서버 실행:
   ```bash
   python main.py
   ```
3. 회원가입 API 호출:
   ```bash
   curl -X POST "http://localhost:8000/api/v1/register" \
     -H "Content-Type: application/json" \
     -d '{"email": "test@example.com", "password": "SecurePass123!"}'
   ```
4. 설정한 `SMTP_EMAIL` 계정의 이메일함에서 인증번호 확인

## 문제 해결

### "SMTP 인증 실패" 오류
- Gmail 사용 시: **앱 비밀번호**를 사용했는지 확인
- 비밀번호에 공백이 없는지 확인
- 2단계 인증이 활성화되어 있는지 확인

### "SMTP 서버 연결 실패" 오류
- `SMTP_SERVER`와 `SMTP_PORT`가 올바른지 확인
- 방화벽에서 해당 포트가 차단되지 않았는지 확인

### 이메일이 전송되지 않음
- 스팸함 확인
- `SMTP_EMAIL` 계정의 이메일함 확인 (발신된 이메일이 있을 수 있음)

