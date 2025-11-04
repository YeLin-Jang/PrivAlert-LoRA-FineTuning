-- 데이터베이스 초기화 스크립트
-- 보안: 스크립트 실행 시 자동으로 실행됨

-- 보안: 기본 데이터베이스 생성 (이미 docker-compose에서 생성됨)
-- USE privalert;

-- 보안: 불필요한 사용자 제거
-- DELETE FROM mysql.user WHERE User='';
-- DELETE FROM mysql.user WHERE User='root' AND Host NOT IN ('localhost', '127.0.0.1', '::1');

-- 보안: 권한 새로고침
-- FLUSH PRIVILEGES;

-- 보안: 테스트 데이터베이스 제거 (프로덕션)
-- DROP DATABASE IF EXISTS test;

-- 초기화 완료 메시지
SELECT 'Database initialization completed successfully' AS status;

