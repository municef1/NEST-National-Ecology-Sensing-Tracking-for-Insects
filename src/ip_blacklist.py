"""
IP 블랙리스트 보안 미들웨어 - 로컬 JSON 파일 관리
"""

import json
from pathlib import Path
from datetime import datetime
from flask import request

def get_base_dir():
    """베이스 디렉토리 가져오기"""
    return Path(__file__).parent.parent

class BlacklistManager:
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
        else:
            blacklist[ip] = {
                'first_blocked': current_time,
                'last_attempt': current_time,
                'reason': reason,
                'method': method,
                'url': url,
                'user_agent': user_agent,
                'attempts': 1
            }
        
        self.save_blacklist(blacklist)
        print(f"🚫 {ip} 차단: {reason} [{method} {url}]")
    
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
blacklist_manager = BlacklistManager()