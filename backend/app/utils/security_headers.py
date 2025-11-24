"""보안 헤더 설정"""
from flask import Flask, Response
import os


def setup_security_headers(app: Flask):
    """보안 헤더 설정"""
    
    @app.after_request
    def set_security_headers(response: Response) -> Response:
        """보안 헤더 설정"""
        response.headers.pop('Server', None)
        response.headers['Server'] = 'PrivAlert'
        response.headers.pop('X-Powered-By', None)
        
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response.headers['Permissions-Policy'] = (
            'geolocation=(), microphone=(), camera=(), payment=(), usb=(), '
            'magnetometer=(), gyroscope=(), speaker=()'
        )
        
        # CSP: blob: URL 허용 (로컬 파일 미리보기용)
        csp = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: blob:; "
            "font-src 'self' data:; "
            "connect-src 'self'; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self'; "
            "media-src 'self' blob:"
        )
        
        response.headers['Content-Security-Policy'] = csp
        
        # Content-Type 설정
        content_type = response.headers.get('Content-Type', '')
        if not content_type:
            response.headers['Content-Type'] = 'application/json; charset=utf-8'
        elif 'charset' not in content_type.lower():
            if 'text/' in content_type or 'application/json' in content_type:
                response.headers['Content-Type'] = f'{content_type}; charset=utf-8'
        
        return response

