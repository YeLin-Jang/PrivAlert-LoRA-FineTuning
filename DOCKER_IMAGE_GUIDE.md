# Docker 이미지 빌드 및 푸시 가이드

Git에 푸시하기 전에 Docker 이미지를 Docker Hub에 푸시하는 방법입니다.

## 방법 1: 스크립트 사용 (권장)

### Windows
```powershell
cd C:\도전보안벨\PrivAlert
.\docker-push.bat
```

### Linux/Mac
```bash
cd PrivAlert
chmod +x docker-push.sh
./docker-push.sh
```

## 방법 2: 수동 실행

### 1단계: Docker Hub 로그인
```bash
docker login
```

### 2단계: 이미지 빌드
```bash
cd PrivAlert
docker-compose build --no-cache
```

### 3단계: 이미지 태그 지정
```bash
# Docker Hub 사용자명으로 변경하세요
export DOCKER_USERNAME=your-username

# 이미지 태그 지정 (docker-compose에서 빌드된 이미지 이름 사용)
docker tag ${DOCKER_USERNAME}/privalert-backend:1.0 ${DOCKER_USERNAME}/privalert-backend:latest
docker tag ${DOCKER_USERNAME}/privalert-frontend:1.0 ${DOCKER_USERNAME}/privalert-frontend:latest
```

### 4단계: Docker Hub에 푸시
```bash
docker push ${DOCKER_USERNAME}/privalert-backend:latest
docker push ${DOCKER_USERNAME}/privalert-frontend:latest
```

## 방법 3: Docker Compose로 직접 푸시 (선택사항)

`docker-compose.yml`에 이미지 이름을 추가하면 자동으로 푸시됩니다:

```yaml
backend:
  build:
    context: ./backend
    dockerfile: Dockerfile
  image: your-username/privalert-backend:latest  # 추가

frontend:
  build:
    context: ./frontend
    dockerfile: Dockerfile
  image: your-username/privalert-frontend:latest  # 추가
```

그 후:
```bash
docker-compose build
docker-compose push
```

## 주의사항

1. **Docker Hub 계정 필요**: 무료 계정 생성: https://hub.docker.com
2. **이미지 크기**: 큰 이미지는 푸시에 시간이 걸릴 수 있습니다
3. **비공개 레포지토리**: Docker Hub Pro 필요 (유료)
4. **대안**: 
   - GitHub Container Registry (ghcr.io)
   - AWS ECR
   - Google Container Registry

## Git 푸시 전 체크리스트

- [ ] Docker 이미지 빌드 완료
- [ ] Docker Hub에 푸시 완료
- [ ] `.env` 파일이 Git에 포함되지 않았는지 확인
- [ ] `.gitignore`에 Docker 이미지 파일 제외 확인
- [ ] Git 커밋 및 푸시

## 문제 해결

### 이미지가 너무 큰 경우
```bash
# 이미지 크기 확인
docker images | grep privalert

# 불필요한 레이어 제거
docker system prune -a
```

### 푸시 권한 오류
```bash
# Docker Hub 로그인 확인
docker login

# 로그인 정보 확인
cat ~/.docker/config.json
```

