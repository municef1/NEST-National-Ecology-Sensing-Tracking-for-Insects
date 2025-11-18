"""
IP 화이트리스트 보안 미들웨어
"""

from flask import request, abort, jsonify
from functools import wraps
import ipaddress
import os

import json
from pathlib import Path

def get_base_dir():
    """베이스 디렉토리 가져오기"""
    return Path(__file__).parent.parent

def load_whitelist_ips():
    """whitelist.json에서 허용된 IP 목록 로드"""
    whitelist_file = get_base_dir() / 'whitelist.json'
    
    # 기본 IP 목록
    default_ips = [
        '127.0.0.1',        # 로컬호스트
        '::1',              # IPv6 로컬호스트
        '192.168.0.0/16',   # 사설 IP 대역
        '10.0.0.0/8',       # 사설 IP 대역
        '172.16.0.0/12',    # 사설 IP 대역
        '124.61.16.167',    # 협업자 IP
        '175.193.255.236',  # 메인 사용자 IP
    ]
    
    try:
        if whitelist_file.exists():
            with open(whitelist_file, 'r', encoding='utf-8') as f:
                whitelist_data = json.load(f)
                return [item['ip_address'] for item in whitelist_data]
    except Exception as e:
        print(f"화이트리스트 로드 오류: {e}")
    
    return default_ips

# 동적으로 허용된 IP 목록 로드
ALLOWED_IPS = load_whitelist_ips()

def is_ip_allowed(ip):
    """IP 주소가 허용 목록에 있는지 확인"""
    try:
        # 최신 화이트리스트 다시 로드
        current_allowed_ips = load_whitelist_ips()
        client_ip = ipaddress.ip_address(ip)
        
        for allowed in current_allowed_ips:
            if '/' in allowed:  # CIDR 표기법
                if client_ip in ipaddress.ip_network(allowed, strict=False):
                    return True
            else:  # 단일 IP
                if str(client_ip) == allowed:
                    return True
        return False
    except:
        return False

def get_real_ip():
    """실제 클라이언트 IP 주소 가져오기"""
    # 프록시 헤더들 확인
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    elif request.headers.get('X-Real-IP'):
        return request.headers.get('X-Real-IP')
    elif request.headers.get('CF-Connecting-IP'):  # Cloudflare
        return request.headers.get('CF-Connecting-IP')
    else:
        return request.remote_addr

def ip_whitelist_required(f):
    """IP 화이트리스트 데코레이터"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        client_ip = get_real_ip()
        
        if not is_ip_allowed(client_ip):
            print(f"🚫 차단된 IP: {client_ip}")
            abort(403)  # Forbidden
        
        return f(*args, **kwargs)
    return decorated_function

def init_ip_whitelist(app):
    """Flask 앱에 IP 화이트리스트 미들웨어 적용"""
    
    @app.before_request
    def check_ip_whitelist():
        client_ip = get_real_ip()
        
        if not is_ip_allowed(client_ip):
            # 화이트리스트에 없는 IP를 블랙리스트에 추가
            from ip_blacklist_enhanced import enhanced_blacklist_manager
            enhanced_blacklist_manager.add_ip(
                client_ip, 
                "화이트리스트 외부IP", 
                request.method, 
                request.url, 
                request.headers.get('User-Agent', '')
            )
            print(f"[BLOCKED] 화이트리스트 외부 IP: {client_ip}")
            return '', 403
    
    print("✓ IP 화이트리스트 보안 활성화")
    print(f"✓ 허용된 IP 대역: {load_whitelist_ips()}")
    print(f"✓ 화이트리스트 파일: {get_base_dir() / 'whitelist.json'}")