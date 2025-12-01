"""
곤충 분류 정보 저장 모듈
이미지 파일명과 종 분류 정보를 JSON 파일로 저장/조회
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional


class ClassificationStorage:
    """분류 정보 저장 관리 클래스"""
    
    def __init__(self, storage_path: str = None):
        """
        초기화
        
        Args:
            storage_path: JSON 저장 파일 경로 (기본: utils/data/classifications.json)
        """
        if storage_path is None:
            base_dir = Path(__file__).parent
            storage_path = base_dir / "data" / "classifications.json"
        
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
    
    def save_classification(self, filename: str, classification_data: Dict):
        """
        분류 정보 저장
        
        Args:
            filename: 이미지 파일명
            classification_data: 분류 정보 딕셔너리
                {
                    'order': 목,
                    'family': 과,
                    'genus': 속,
                    'species': 종,
                    'korean_name': 국명,
                    'confidence': 신뢰도,
                    'timestamp': 분류 시각
                }
        """
        data = self._load_data()
        
        # 타임스탬프 추가
        classification_data['timestamp'] = datetime.now().isoformat()
        classification_data['filename'] = filename
        
        # 파일명을 키로 저장
        data[filename] = classification_data
        
        self._save_data(data)
        print(f"분류 정보 저장 완료: {filename} -> {classification_data.get('species', 'Unknown')}")
    
    def get_classification(self, filename: str) -> Optional[Dict]:
        """
        파일명으로 분류 정보 조회
        
        Args:
            filename: 이미지 파일명
            
        Returns:
            분류 정보 딕셔너리 또는 None
        """
        data = self._load_data()
        return data.get(filename)
    
    def get_all_classifications(self) -> Dict:
        """모든 분류 정보 조회"""
        return self._load_data()
    
    def delete_classification(self, filename: str):
        """분류 정보 삭제"""
        data = self._load_data()
        if filename in data:
            del data[filename]
            self._save_data(data)
            print(f"분류 정보 삭제 완료: {filename}")
    
    def clear_all(self):
        """모든 분류 정보 삭제"""
        self._save_data({})
        print("모든 분류 정보 삭제 완료")


# 싱글톤 인스턴스
_storage_instance = None

def get_classification_storage() -> ClassificationStorage:
    """분류 정보 저장소 싱글톤 인스턴스 반환"""
    global _storage_instance
    if _storage_instance is None:
        _storage_instance = ClassificationStorage()
    return _storage_instance
