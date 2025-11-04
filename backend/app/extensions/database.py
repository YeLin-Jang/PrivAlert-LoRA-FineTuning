"""
데이터베이스 연결 설정
보안: SQLAlchemy ORM을 사용하여 SQL 인젝션 방지
"""
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool
from sqlalchemy.orm import sessionmaker
import os
from urllib.parse import quote_plus

# SQLAlchemy 인스턴스 생성
db = SQLAlchemy()

def init_db(app):
    """
    데이터베이스 초기화
    보안: 연결 풀링 및 연결 문자열 보안 설정
    """
    # 데이터베이스 URL 구성
    database_url = os.getenv('DATABASE_URL')
    
    if not database_url:
        # 환경 변수에서 개별 구성
        mysql_host = os.getenv('MYSQL_HOST', 'localhost')
        mysql_port = os.getenv('MYSQL_PORT', '3306')
        mysql_database = os.getenv('MYSQL_DATABASE', 'privalert')
        mysql_user = os.getenv('MYSQL_USER', 'privalert_user')
        mysql_password = os.getenv('MYSQL_PASSWORD', '')
        
        # 보안: 비밀번호 URL 인코딩 (특수문자 처리)
        mysql_password_encoded = quote_plus(mysql_password)
        
        database_url = (
            f"mysql+pymysql://{mysql_user}:{mysql_password_encoded}"
            f"@{mysql_host}:{mysql_port}/{mysql_database}"
            f"?charset=utf8mb4"
        )
    
    # 보안: 연결 풀 설정 (DDoS 방지)
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'poolclass': QueuePool,
        'pool_size': 10,  # 최대 연결 수
        'pool_recycle': 3600,  # 1시간마다 연결 재사용
        'pool_pre_ping': True,  # 연결 유효성 검사
        'max_overflow': 20,  # 추가 연결 허용
        'echo': False,  # SQL 쿼리 로깅 (프로덕션에서는 False)
    }
    
    # 보안: 트래킹 비활성화 (성능 및 보안)
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # 데이터베이스 초기화
    db.init_app(app)
    
    return db

