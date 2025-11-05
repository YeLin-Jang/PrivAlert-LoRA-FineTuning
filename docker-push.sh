#!/bin/bash
# Docker 이미지 빌드 및 푸시 스크립트
# Git 푸시 전에 Docker 이미지를 Docker Hub에 푸시

set -e

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== PrivAlert Docker 이미지 빌드 및 푸시 ===${NC}"
echo ""

# Docker Hub 사용자명 확인
if [ -z "$DOCKER_USERNAME" ]; then
    echo -e "${YELLOW}Docker Hub 사용자명을 입력하세요:${NC}"
    read DOCKER_USERNAME
    export DOCKER_USERNAME
fi

echo -e "${GREEN}Docker Hub 사용자명: ${DOCKER_USERNAME}${NC}"
echo ""

# 이미지 태그 설정
BACKEND_IMAGE="${DOCKER_USERNAME}/privalert-backend:latest"
FRONTEND_IMAGE="${DOCKER_USERNAME}/privalert-frontend:latest"

# 1. 이미지 빌드
echo -e "${YELLOW}1. Docker 이미지 빌드 중...${NC}"
docker-compose build --no-cache

echo ""
echo -e "${YELLOW}2. 이미지 태그 지정 중...${NC}"

# 백엔드 이미지 태그
docker tag privalert-backend:latest ${BACKEND_IMAGE} || {
    echo -e "${RED}백엔드 이미지를 찾을 수 없습니다. docker-compose build를 먼저 실행하세요.${NC}"
    exit 1
}

# 프론트엔드 이미지 태그
docker tag privalert-frontend:latest ${FRONTEND_IMAGE} || {
    echo -e "${RED}프론트엔드 이미지를 찾을 수 없습니다. docker-compose build를 먼저 실행하세요.${NC}"
    exit 1
}

echo -e "${GREEN}✓ 이미지 태그 지정 완료${NC}"
echo "  - ${BACKEND_IMAGE}"
echo "  - ${FRONTEND_IMAGE}"
echo ""

# 3. Docker Hub 로그인 확인
echo -e "${YELLOW}3. Docker Hub 로그인 확인 중...${NC}"
if ! docker info | grep -q "Username"; then
    echo -e "${YELLOW}Docker Hub에 로그인이 필요합니다.${NC}"
    docker login
fi

# 4. 이미지 푸시
echo ""
echo -e "${YELLOW}4. Docker Hub에 이미지 푸시 중...${NC}"
echo -e "${GREEN}백엔드 이미지 푸시 중...${NC}"
docker push ${BACKEND_IMAGE}

echo -e "${GREEN}프론트엔드 이미지 푸시 중...${NC}"
docker push ${FRONTEND_IMAGE}

echo ""
echo -e "${GREEN}✓ 모든 작업 완료!${NC}"
echo ""
echo "푸시된 이미지:"
echo "  - ${BACKEND_IMAGE}"
echo "  - ${FRONTEND_IMAGE}"
echo ""
echo -e "${YELLOW}이제 Git에 푸시할 수 있습니다!${NC}"

