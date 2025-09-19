"""
app/extensions.py

Flask 확장 객체들을 정의하는 파일입니다.
(ex: SQLAlchemy, Migrate, CORS, Swagger 등)

- 이 파일에서는 객체 생성만 하고 (db = SQLAlchemy(), migrate = Migrate() 등),
- 실제 Flask 앱에 연결(init_app)은 app/__init__.py에서 수행합니다.

현재는 확장이 없어 비어 있으며, 확장이 추가되면 이 파일에 등록해 주세요.

지금도 init에서 분리하려면 가능한데 아직은 작으니까 확장파일에 옮겨담지는 않을게요
"""
