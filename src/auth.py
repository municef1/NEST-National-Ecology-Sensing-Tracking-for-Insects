from flask import session, request, jsonify, redirect, url_for
from functools import wraps
import hashlib
import secrets
import os
from datetime import datetime, timedelta

class AuthManager:
    def __init__(self, supabase_client=None, supabase_admin_client=None):
        self.supabase = supabase_client
        self.supabase_admin = supabase_admin_client
    
    def hash_password(self, password):
        """비밀번호 해시화"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def verify_password(self, username, password):
        """비밀번호 검증"""
        if not self.supabase:
            return False
        
        try:
            result = self.supabase.table('users').select('*').eq('username', username).eq('is_active', True).execute()
            if result.data:
                user = result.data[0]
                return user['password_hash'] == self.hash_password(password)
        except Exception as e:
            print(f"Login error: {e}")
        return False
    
    def login_user(self, username, password):
        """사용자 로그인"""
        if not self.supabase:
            return False
            
        try:
            result = self.supabase.table('users').select('*').eq('username', username).eq('is_active', True).execute()
            if result.data:
                user = result.data[0]
                if user['password_hash'] == self.hash_password(password):
                    session['user_id'] = str(user['id'])
                    session['username'] = user['username']
                    session['user_role'] = user['role']
                    session['user_name'] = user['name']
                    session['login_time'] = datetime.now().isoformat()
                    
                    # 마지막 로그인 시간 업데이트
                    self.supabase.table('users').update({'last_login': datetime.now().isoformat()}).eq('id', user['id']).execute()
                    return True
        except Exception as e:
            print(f"Login error: {e}")
        return False
    
    def logout_user(self):
        """사용자 로그아웃"""
        session.clear()
    
    def is_logged_in(self):
        """로그인 상태 확인"""
        return 'user_id' in session
    
    def get_current_user(self):
        """현재 사용자 정보"""
        if self.is_logged_in():
            return {
                'id': session['user_id'],
                'username': session.get('username'),
                'role': session['user_role'],
                'name': session['user_name']
            }
        return None
    
    def create_user(self, username, password, role, name, email=None):
        """사용자 생성 (관리자 권한 필요)"""
        if not self.supabase_admin:
            return False
        
        try:
            password_hash = self.hash_password(password)
            result = self.supabase_admin.table('users').insert({
                'username': username,
                'password_hash': password_hash,
                'role': role,
                'name': name,
                'email': email
            }).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            print(f"Create user error: {e}")
            return None
    
    def get_all_users(self):
        """모든 사용자 조회 (관리자 권한 필요)"""
        if not self.supabase_admin:
            return []
        
        try:
            result = self.supabase_admin.table('users').select('id, username, role, name, email, is_active, created_at, last_login').execute()
            return result.data
        except Exception as e:
            print(f"Get users error: {e}")
            return []

auth_manager = AuthManager()

def login_required(f):
    """로그인 필수 데코레이터"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not auth_manager.is_logged_in():
            if request.is_json:
                return jsonify({'error': '로그인이 필요합니다.'}), 401
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """관리자 권한 필수 데코레이터"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not auth_manager.is_logged_in():
            return jsonify({'error': '로그인이 필요합니다.'}), 401
        
        user = auth_manager.get_current_user()
        if user['role'] != 'admin':
            return jsonify({'error': '관리자 권한이 필요합니다.'}), 403
        
        return f(*args, **kwargs)
    return decorated_function