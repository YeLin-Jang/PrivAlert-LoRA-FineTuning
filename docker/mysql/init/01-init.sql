-- 데이터베이스 초기화 스크립트
-- MySQL 컨테이너 시작 시 자동 실행됨

-- 사용자 생성 (이미 docker-compose에서 생성되지만, 권한 확인)
GRANT SELECT, INSERT, UPDATE, DELETE ON privalert.* TO 'app_user'@'%';
FLUSH PRIVILEGES;

-- validate_password 플러그인 설치 (선택)
-- INSTALL PLUGIN validate_password SONAME 'validate_password.so';

-- 비밀번호 정책 설정 (선택)
-- SET GLOBAL validate_password.policy = STRONG;
-- SET GLOBAL validate_password.length = 8;
-- SET GLOBAL validate_password.mixed_case_count = 1;
-- SET GLOBAL validate_password.number_count = 1;
-- SET GLOBAL validate_password.special_char_count = 1;

