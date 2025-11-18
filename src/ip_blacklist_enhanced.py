"""
IP 블랙리스트 보안 미들웨어 - 강화된 버전
"""

import json
from pathlib import Path
from datetime import datetime
from flask import request

def get_base_dir():
    """베이스 디렉토리 가져오기"""
    return Path(__file__).parent.parent

class EnhancedBlacklistManager:
    def __init__(self):
        self.blacklist_file = get_base_dir() / 'blacklist.json'
        self.ensure_blacklist_file()
    
    def ensure_blacklist_file(self):
        """블랙리스트 파일 생성"""
        if not self.blacklist_file.exists():
            self.save_blacklist({})
    
    def load_blacklist(self):
        """블랙리스트 로드"""
        try:
            with open(self.blacklist_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    
    def save_blacklist(self, blacklist):
        """블랙리스트 저장"""
        try:
            with open(self.blacklist_file, 'w', encoding='utf-8') as f:
                json.dump(blacklist, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"블랙리스트 저장 오류: {e}")
    
    def add_ip(self, ip, reason="악성 요청", method="", url="", user_agent=""):
        """즉시 블랙리스트 추가 (상세 정보 포함)"""
        blacklist = self.load_blacklist()
        current_time = datetime.now().isoformat()
        
        if ip in blacklist:
            blacklist[ip]['attempts'] += 1
            blacklist[ip]['last_attempt'] = current_time
            if url:
                blacklist[ip]['last_url'] = url
            if method:
                blacklist[ip]['last_method'] = method
        else:
            blacklist[ip] = {
                'first_blocked': current_time,
                'last_attempt': current_time,
                'reason': reason,
                'method': method,
                'url': url,
                'user_agent': user_agent[:200] if user_agent else "",
                'attempts': 1,
                'blocked_by': 'auto_detection'
            }
        
        self.save_blacklist(blacklist)
        print(f"[BLOCKED] {ip}: {reason} [{method} {url[:50] if url else ''}...]")
    
    def is_malicious_pattern(self, ip, method, path, user_agent, headers):
        """악성 패턴 감지 (강화된 버전)"""
        path_lower = path.lower()
        user_agent_lower = user_agent.lower() if user_agent else ""
        
        # 즉시 차단 패턴들
        malicious_paths = [
            '/wp-admin', '/wp-login', '/phpmyadmin', '/admin/config',
            '/.env', '/shell', '/cmd', '/eval', '/system',
            '/etc/passwd', '/proc/version', '/boot.ini',
            '/cgi-bin', '/scripts', '/HNAP1', '/GponForm',
            '/api/v1/auth', '/solr/admin', '/jenkins',
            '/actuator', '/debug', '/console', '/manager',
            '/invoker', '/axis2', '/struts', '/drupal',
            '/security.txt', '/robots.txt', '/sitemap.xml'
        ]
        
        malicious_methods = ['CONNECT', 'TRACE', 'TRACK']
        
        malicious_agents = [
            'bot', 'crawler', 'spider', 'scan', 'hack', 'exploit',
            'nmap', 'sqlmap', 'nikto', 'dirb', 'gobuster',
            'masscan', 'zmap', 'nuclei', 'burp', 'owasp',
            'python-requests', 'curl', 'wget'
        ]
        
        malicious_urls = [
            'api.ipify.org', 'shadowserver.org', 'httpbin.org',
            'webhook.site', 'ngrok.io', 'requestbin.com'
        ]
        
        # 경로 패턴 검사
        for pattern in malicious_paths:
            if pattern in path_lower:
                return f"악성경로: {pattern}"
        
        # 메소드 검사
        if method in malicious_methods:
            return f"악성메소드: {method}"
        
        # User-Agent 검사
        for pattern in malicious_agents:
            if pattern in user_agent_lower:
                return f"악성Agent: {pattern}"
        
        # URL 패턴 검사
        full_url = path.lower()
        for pattern in malicious_urls:
            if pattern in full_url:
                return f"악성URL: {pattern}"
        
        # SQL 인젝션 패턴
        sql_patterns = ['union', 'select', 'drop', 'insert', 'update', 'delete', "'", '"', ';--']
        for pattern in sql_patterns:
            if pattern in path_lower:
                return f"SQL인젝션: {pattern}"
        
        # XSS 패턴
        xss_patterns = ['<script', 'javascript:', 'onerror=', 'onload=', 'alert(']
        for pattern in xss_patterns:
            if pattern in path_lower:
                return f"XSS시도: {pattern}"
        
        # 디렉토리 순회 공격
        traversal_patterns = ['../', '..\\', '%2e%2e', '%252e']
        for pattern in traversal_patterns:
            if pattern in path_lower:
                return f"디렉토리순회: {pattern}"
        
        # 명령어 인젝션
        cmd_patterns = ['|', '&&', '||', ';', '`', '$(']
        for pattern in cmd_patterns:
            if pattern in path_lower:
                return f"명령어인젝션: {pattern}"
        
        # 헤더 기반 검사
        for header_name, header_value in headers.items():
            if any(p in header_name.lower() for p in ['proxy', 'tunnel', 'forward']):
                return f"프록시헤더: {header_name}"
        
        # 비정상적인 요청 패턴
        if len(path) > 1000:
            return "비정상경로길이"
        
        if user_agent and len(user_agent) > 500:
            return "비정상Agent길이"
        
        # 바이너리 데이터 패턴 (TLS handshake 등)
        if any(ord(c) < 32 and c not in ['\t', '\n', '\r'] for c in path):
            return "바이너리데이터"
        
        # 비정상적인 요청 라인 패턴 (MGLNDD_ 등)
        suspicious_prefixes = ['MGLNDD', 'CONNECT_', 'TUNNEL_', 'PROXY_']
        for prefix in suspicious_prefixes:
            if prefix in path or prefix in method:
                return f"비정상요청: {prefix}"
        
        # IP 주소가 포함된 비정상 경로
        import re
        ip_pattern = r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'
        if re.search(ip_pattern, path) and not path.startswith('/api/storage-image/'):
            return "IP포함경로"
        
        return None
    
    def is_blacklisted(self, ip):
        """IP 블랙리스트 확인"""
        blacklist = self.load_blacklist()
        return ip in blacklist
    
    def remove_ip(self, ip):
        """블랙리스트에서 IP 제거"""
        blacklist = self.load_blacklist()
        if ip in blacklist:
            del blacklist[ip]
            self.save_blacklist(blacklist)
            return True
        return False
    
    def get_all(self):
        """전체 블랙리스트 조회 (정렬된 상태로)"""
        blacklist = self.load_blacklist()
        sorted_blacklist = dict(sorted(blacklist.items(), 
                                     key=lambda x: x[1].get('last_attempt', ''), 
                                     reverse=True))
        return sorted_blacklist

# 전역 인스턴스
enhanced_blacklist_manager = EnhancedBlacklistManager()