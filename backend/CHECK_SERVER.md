# 서버 네트워크 오류 진단 가이드

## 관리자 로그인 네트워크 오류 해결 방법

### 1. 서버 상태 확인

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

### 2. 서버 재시작

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

### 3. 포트 확인

- 기본 포트: **5000**
- Docker 포트 매핑: `BACKEND_PORT:5000`
- 프론트엔드에서 접근하는 URL 확인:
  - `http://localhost:5000/api/v1/admin/auth/login`
  - 또는 `http://localhost:${BACKEND_PORT}/api/v1/admin/auth/login`

### 4. CORS 설정 확인

`.env` 파일에 다음이 설정되어 있는지 확인:
```bash
CORS_ORIGINS=http://localhost:3000
```

프론트엔드가 다른 포트에서 실행 중이라면 추가:
```bash
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
```

### 5. API 엔드포인트 확인

관리자 로그인 엔드포인트:
```
POST /api/v1/admin/auth/login
```

프론트엔드에서 요청하는 URL이 정확한지 확인:
- ✅ `http://localhost:5000/api/v1/admin/auth/login`
- ❌ `http://localhost:5000/admin/login` (잘못된 경로)

### 6. 네트워크 오류 종류별 해결

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

### 7. 빠른 해결 방법

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

### 8. 테스트 요청

터미널에서 직접 테스트:
```bash
curl -X POST http://localhost:5000/api/v1/admin/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"your-password"}'
```

성공하면 서버는 정상 작동 중입니다.


