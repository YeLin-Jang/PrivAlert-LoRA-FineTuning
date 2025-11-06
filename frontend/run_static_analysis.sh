#!/bin/bash
# Frontend 정적 분석 실행 스크립트 (Linux/Mac)

cd "$(dirname "$0")"

echo "========================================"
echo "Frontend 정적 분석 시작"
echo "========================================"
echo ""

echo "[1/3] TypeScript 타입 검사..."
npm run type-check
if [ $? -ne 0 ]; then
    echo "TypeScript 타입 검사 실패"
    exit 1
fi

echo ""
echo "[2/3] ESLint 코드 품질 검사..."
npm run lint:warn
if [ $? -ne 0 ]; then
    echo "ESLint 검사에서 경고 발견 (자동 수정 시도: npm run lint:fix)"
fi

echo ""
echo "[3/3] npm audit 보안 검사..."
npm run audit
if [ $? -ne 0 ]; then
    echo "npm audit에서 취약점 발견 (자동 수정 시도: npm run audit:fix)"
fi

echo ""
echo "========================================"
echo "Frontend 정적 분석 완료"
echo "========================================"

