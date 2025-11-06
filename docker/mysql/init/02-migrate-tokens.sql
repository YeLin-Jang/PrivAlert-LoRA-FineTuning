-- 토큰 테이블 마이그레이션 스크립트
-- 이메일 인증 완료 후에만 계정을 저장하도록 변경
-- 실행: MySQL 컨테이너 내부에서 또는 외부에서 실행

USE privalert;

-- 1. metadata 컬럼 추가 (이메일 인증 토큰에 회원가입 정보 저장)
-- MySQL 8.0은 IF NOT EXISTS를 지원하지 않으므로, 컬럼이 없을 때만 추가
SET @col_exists = 0;
SELECT COUNT(*) INTO @col_exists 
FROM information_schema.COLUMNS 
WHERE TABLE_SCHEMA = 'privalert' 
  AND TABLE_NAME = 'tokens' 
  AND COLUMN_NAME = 'metadata';

SET @sql = IF(@col_exists = 0,
    'ALTER TABLE tokens ADD COLUMN metadata TEXT NULL COMMENT ''이메일 인증 토큰용: 회원가입 정보 임시 저장 (JSON: {email, password_hash})''',
    'SELECT ''Column metadata already exists'' AS status');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- 2. user_id를 nullable로 변경 (이메일 인증 토큰은 user_id 없음)
-- 기존 NOT NULL 제약이 있는 경우에만 변경
SET @col_not_null = 0;
SELECT COUNT(*) INTO @col_not_null 
FROM information_schema.COLUMNS 
WHERE TABLE_SCHEMA = 'privalert' 
  AND TABLE_NAME = 'tokens' 
  AND COLUMN_NAME = 'user_id' 
  AND IS_NULLABLE = 'NO';

SET @sql2 = IF(@col_not_null > 0,
    'ALTER TABLE tokens MODIFY COLUMN user_id INT NULL',
    'SELECT ''Column user_id is already nullable'' AS status');
PREPARE stmt2 FROM @sql2;
EXECUTE stmt2;
DEALLOCATE PREPARE stmt2;

-- 3. 기존 이메일 인증 토큰 정리 (필요시)
-- 이메일 인증이 완료되지 않은 사용자 계정 삭제 (선택사항)
-- DELETE u FROM users u 
-- LEFT JOIN tokens t ON u.id = t.user_id AND t.token_type = 'email_verification' AND t.used = FALSE
-- WHERE u.email_verified = FALSE AND u.id NOT IN (SELECT DISTINCT user_id FROM tokens WHERE token_type = 'email_verification' AND used = TRUE);

-- 3. users 테이블에 nickname 컬럼 추가
SET @nickname_exists = 0;
SELECT COUNT(*) INTO @nickname_exists 
FROM information_schema.COLUMNS 
WHERE TABLE_SCHEMA = 'privalert' 
  AND TABLE_NAME = 'users' 
  AND COLUMN_NAME = 'nickname';

SET @sql3 = IF(@nickname_exists = 0,
    'ALTER TABLE users ADD COLUMN nickname VARCHAR(50) NULL COMMENT ''별명 (이메일 대신 표시용)''',
    'SELECT ''Column nickname already exists'' AS status');
PREPARE stmt3 FROM @sql3;
EXECUTE stmt3;
DEALLOCATE PREPARE stmt3;

-- 마이그레이션 완료
SELECT 'Token and Users table migration completed successfully' AS status;

