# 마이그레이션 가이드

## 초기 설정

```bash
# 마이그레이션 디렉토리 초기화
flask db init

# 초기 마이그레이션 생성
flask db migrate -m "init user/role models"

# 마이그레이션 적용
flask db upgrade
```

## 초기 데이터 시드

```bash
# 역할 및 관리자 계정 생성
python scripts/seed_db.py
```

또는 환경변수 설정:

```bash
export ADMIN_EMAIL=admin@example.com
export ADMIN_PASSWORD=your_secure_password
python scripts/seed_db.py
```

