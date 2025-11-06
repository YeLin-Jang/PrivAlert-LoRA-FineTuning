-- 데이터베이스 초기화 스크립트
-- 보안: 스크립트 실행 시 자동으로 실행됨
-- Docker 환경에서는 docker-compose.yml에서 데이터베이스와 사용자가 생성되므로
-- 여기서는 추가 권한 설정 및 보안 설정만 수행합니다

-- 데이터베이스 생성 (docker-compose에서 생성되지 않은 경우를 대비)
CREATE DATABASE IF NOT EXISTS privalert CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- 사용자 권한 확인 및 부여 (docker-compose에서 생성된 사용자에게 권한 부여)
-- 환경 변수에서 사용자 정보를 가져와야 하므로, 여기서는 기본 권한만 설정
GRANT ALL PRIVILEGES ON privalert.* TO 'privalert_user'@'%';
GRANT ALL PRIVILEGES ON privalert.* TO 'privalert_user'@'localhost';

-- 권한 새로고침
FLUSH PRIVILEGES;

-- 보안: 불필요한 사용자 제거
DELETE FROM mysql.user WHERE User='';
DELETE FROM mysql.user WHERE User='root' AND Host NOT IN ('localhost', '127.0.0.1', '::1');

-- 보안: 테스트 데이터베이스 제거 (프로덕션)
DROP DATABASE IF EXISTS test;

-- 권한 재새로고침
FLUSH PRIVILEGES;

-- 초기화 완료 메시지
SELECT 'Database initialization completed successfully' AS status;

