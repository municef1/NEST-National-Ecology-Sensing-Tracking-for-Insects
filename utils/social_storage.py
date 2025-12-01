"""
좋아요 및 댓글 저장 모듈
이미지 파일명과 좋아요/댓글 정보를 JSON 파일로 저장/조회
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional


class SocialStorage:
    """좋아요 및 댓글 저장 관리 클래스"""
    
    def __init__(self, storage_path: str = None):
        """
        초기화
        
        Args:
            storage_path: JSON 저장 파일 경로 (기본: utils/data/social_data.json)
        """
        if storage_path is None:
            base_dir = Path(__file__).parent
            storage_path = base_dir / "data" / "social_data.json"
        
        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 파일이 없으면 빈 딕셔너리로 초기화
        if not self.storage_path.exists():
            self._save_data({})
    
    def _load_data(self) -> Dict:
        """JSON 파일에서 데이터 로드"""
        try:
            with open(self.storage_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"데이터 로드 오류: {e}")
            return {}
    
    def _save_data(self, data: Dict):
        """JSON 파일에 데이터 저장"""
        try:
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"데이터 저장 오류: {e}")
    
    def get_likes(self, filename: str) -> int:
        """좋아요 수 조회"""
        data = self._load_data()
        file_data = data.get(filename, {})
        likes = file_data.get('likes', [])
        return len(likes)
    
    def toggle_like(self, filename: str, user_id: str = None) -> Dict:
        """
        좋아요 토글
        
        Args:
            filename: 이미지 파일명
            user_id: 사용자 ID (기본: IP 주소 또는 세션 ID)
            
        Returns:
            {'liked': bool, 'count': int}
        """
        data = self._load_data()
        
        if filename not in data:
            data[filename] = {'likes': [], 'comments': []}
        
        file_data = data[filename]
        likes = file_data.get('likes', [])
        
        # user_id가 없으면 기본값 사용
        if user_id is None:
            user_id = 'anonymous'
        
        # 좋아요 토글
        if user_id in likes:
            likes.remove(user_id)
            liked = False
        else:
            likes.append(user_id)
            liked = True
        
        file_data['likes'] = likes
        data[filename] = file_data
        
        self._save_data(data)
        
        return {'liked': liked, 'count': len(likes)}
    
    def is_liked(self, filename: str, user_id: str = None) -> bool:
        """좋아요 여부 확인"""
        data = self._load_data()
        file_data = data.get(filename, {})
        likes = file_data.get('likes', [])
        
        if user_id is None:
            user_id = 'anonymous'
        
        return user_id in likes
    
    def get_comments(self, filename: str) -> List[Dict]:
        """댓글 목록 조회"""
        data = self._load_data()
        file_data = data.get(filename, {})
        return file_data.get('comments', [])
    
    def add_comment(self, filename: str, comment_text: str, user_id: str = None) -> Dict:
        """
        댓글 추가
        
        Args:
            filename: 이미지 파일명
            comment_text: 댓글 내용
            user_id: 사용자 ID (기본: anonymous)
            
        Returns:
            추가된 댓글 딕셔너리
        """
        data = self._load_data()
        
        if filename not in data:
            data[filename] = {'likes': [], 'comments': []}
        
        file_data = data[filename]
        comments = file_data.get('comments', [])
        
        if user_id is None:
            user_id = 'anonymous'
        
        comment = {
            'id': len(comments) + 1,
            'user_id': user_id,
            'text': comment_text,
            'timestamp': datetime.now().isoformat()
        }
        
        comments.append(comment)
        file_data['comments'] = comments
        data[filename] = file_data
        
        self._save_data(data)
        
        return comment


# 싱글톤 인스턴스
_social_storage_instance = None

def get_social_storage() -> SocialStorage:
    """소셜 저장소 싱글톤 인스턴스 반환"""
    global _social_storage_instance
    if _social_storage_instance is None:
        _social_storage_instance = SocialStorage()
    return _social_storage_instance

