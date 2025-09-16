from flask import Blueprint, jsonify

main_bp = Blueprint("main", __name__)

@main_bp.route("/api/hello")
def hello():
    """테스트용 Hello 라우트"""
    return jsonify({
        "message": "Hello, PrivAlert API is working!"
    })
