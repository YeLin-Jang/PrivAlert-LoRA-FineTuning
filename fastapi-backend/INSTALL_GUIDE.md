# 설치 가이드 (Windows)

Windows에서 Rust 컴파일 오류가 발생하는 경우를 위한 설치 가이드입니다.

## 빠른 설치 (권장)

### 방법 1: 사전 빌드된 패키지만 사용

```powershell
cd PrivAlert\fastapi-backend

# pip 업그레이드
python -m pip install --upgrade pip

# 사전 빌드된 wheel만 사용하여 설치
pip install --only-binary :all: fastapi uvicorn[standard] pydantic pydantic-settings
pip install --only-binary :all: sqlalchemy[asyncio] aiosqlite
pip install --only-binary :all: bcrypt python-dotenv python-multipart
```

### 방법 2: 개별 설치 (오류 발생 시)

```powershell
cd PrivAlert\fastapi-backend

# 1. 필수 패키지
pip install fastapi==0.109.0
pip install uvicorn[standard]==0.27.0

# 2. Pydantic (사전 빌드된 버전 사용)
pip install pydantic==2.6.1 --only-binary :all:
pip install pydantic-settings==2.1.0 --only-binary :all:

# 3. 데이터베이스
pip install sqlalchemy[asyncio]==2.0.23
pip install aiosqlite==0.19.0

# 4. 비밀번호 해싱
pip install bcrypt==4.1.2 --only-binary :all:

# 5. 기타
pip install python-dotenv==1.0.1
pip install python-multipart==0.0.6
```

## Rust 컴파일 오류 해결

### 옵션 1: Rust 완전 설치 (장기적 해결)

1. **Rust 설치**: https://rustup.rs/ 에서 설치
2. 설치 후 터미널 재시작
3. PATH에 Rust가 추가되었는지 확인:
   ```powershell
   cargo --version
   ```
4. 그 후 `pip install -r requirements.txt` 실행

### 옵션 2: 사전 빌드된 패키지만 사용 (빠른 해결) ⭐

```powershell
# 모든 패키지를 사전 빌드된 wheel로만 설치
pip install --only-binary :all: -r requirements.txt
```

### 옵션 3: pydantic 버전 낮추기

```powershell
pip install pydantic==1.10.13
pip install pydantic-settings==1.10.1
```

이 경우 `app/core/config.py`의 import를 수정해야 할 수 있습니다.

## 설치 확인

```powershell
python -c "import fastapi, bcrypt, pydantic; print('✅ 모든 패키지 설치 완료!')"
```

## 문제 해결

### "No module named 'bcrypt'" 오류

```powershell
# 사전 빌드된 wheel 사용
pip install bcrypt --only-binary :all:

# 또는 bcrypt-cffi 사용
pip install bcrypt-cffi
```

### "pydantic-core" 컴파일 오류

```powershell
# 사전 빌드된 wheel만 사용
pip install pydantic --only-binary :all: --upgrade
```

### "Microsoft Visual C++ 14.0 is required" 오류

1. Visual Studio Build Tools 설치: https://visualstudio.microsoft.com/visual-cpp-build-tools/
2. 또는 사전 빌드된 패키지만 사용:
   ```powershell
   pip install --only-binary :all: -r requirements.txt
   ```

## 최소 설치 (기본 기능만)

Rust 컴파일 문제가 계속되면 최소한의 패키지만 설치:

```powershell
pip install fastapi uvicorn sqlalchemy aiosqlite bcrypt python-dotenv
```

이렇게 하면 기본 기능은 작동합니다.

