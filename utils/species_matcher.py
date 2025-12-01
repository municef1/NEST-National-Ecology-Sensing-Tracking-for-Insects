"""
곤충 종 매칭 시스템

CSV 파일의 종 정보를 사용하여 학명과 국명을 매칭하고 
계통분류 정보를 제공합니다.
"""

import pandas as pd
import re
from pathlib import Path
from typing import Dict, Optional, List


class SpeciesMatcher:
    """곤충 종 매칭 클래스"""
    
    def __init__(self, csv_path: Optional[str] = None):
        """
        초기화
        
        Args:
            csv_path: CSV 파일 경로
        """
        if csv_path is None:
            csv_path = Path(__file__).parent / "data" / "insect_species_final.csv"
        
        self.csv_path = Path(csv_path)
        self.species_data = None
        self.load_species_data()
    
    def load_species_data(self):
        """종 데이터 로드"""
        try:
            if self.csv_path.exists():
                self.species_data = pd.read_csv(self.csv_path, encoding='utf-8')
                print(f"[SPECIES_MATCHER] 종 데이터 로드 완료: {len(self.species_data)}개 종")
                
                # 컬럼명 확인 및 정규화
                if 'scientific_name' not in self.species_data.columns:
                    # 가능한 학명 컬럼명들
                    possible_names = ['학명', 'Scientific_Name', 'scientific_name', 'species_name']
                    for col in self.species_data.columns:
                        if any(name.lower() in col.lower() for name in possible_names):
                            self.species_data['scientific_name'] = self.species_data[col]
                            break
                
                # 국명 컬럼 확인
                if 'korean_name' not in self.species_data.columns:
                    possible_names = ['국명', 'Korean_Name', 'korean_name', 'common_name']
                    for col in self.species_data.columns:
                        if any(name.lower() in col.lower() for name in possible_names):
                            self.species_data['korean_name'] = self.species_data[col]
                            break
                
                print(f"[SPECIES_MATCHER] 컬럼: {list(self.species_data.columns)}")
            else:
                print(f"[SPECIES_MATCHER] CSV 파일을 찾을 수 없음: {self.csv_path}")
                self.species_data = pd.DataFrame()
        except Exception as e:
            print(f"[SPECIES_MATCHER] 데이터 로드 오류: {str(e)}")
            self.species_data = pd.DataFrame()
    
    def normalize_name(self, name: str) -> str:
        """이름 정규화"""
        if not name:
            return ""
        
        # 언더스코어를 공백으로 변환
        name = name.replace("_", " ")
        
        # 여러 공백을 하나로
        name = re.sub(r'\s+', ' ', name)
        
        # 앞뒤 공백 제거
        name = name.strip()
        
        return name
    
    def find_species_info(self, species_name: str) -> Optional[Dict]:
        """
        종 정보 검색
        
        Args:
            species_name: 종명 (학명 또는 국명)
            
        Returns:
            종 정보 딕셔너리 또는 None
        """
        if self.species_data is None or self.species_data.empty:
            return None
        
        print(f"[SPECIES_MATCHER] 검색 중: {species_name}")
        
        normalized_input = self.normalize_name(species_name)
        
        # 1. 정확한 학명 매칭
        if 'scientific_name' in self.species_data.columns:
            for idx, row in self.species_data.iterrows():
                scientific = str(row.get('scientific_name', ''))
                if scientific and self.normalize_name(scientific) == normalized_input:
                    print(f"[SPECIES_MATCHER] 학명 정확 매칭 성공: {scientific}")
                    return self._format_species_info(row)
        
        # 2. 정확한 국명 매칭
        if 'korean_name' in self.species_data.columns:
            for idx, row in self.species_data.iterrows():
                korean = str(row.get('korean_name', ''))
                if korean and korean == species_name:
                    print(f"[SPECIES_MATCHER] 국명 정확 매칭 성공: {korean}")
                    return self._format_species_info(row)
        
        # 3. 부분 매칭 (속명 기준)
        if 'scientific_name' in self.species_data.columns:
            input_parts = normalized_input.split()
            if len(input_parts) >= 2:
                input_genus = input_parts[0]
                
                for idx, row in self.species_data.iterrows():
                    scientific = str(row.get('scientific_name', ''))
                    if scientific:
                        scientific_parts = self.normalize_name(scientific).split()
                        if len(scientific_parts) >= 2 and scientific_parts[0] == input_genus:
                            print(f"[SPECIES_MATCHER] 속명 매칭 성공: {scientific}")
                            return self._format_species_info(row)
        
        # 4. 포함 관계 매칭
        if 'scientific_name' in self.species_data.columns:
            for idx, row in self.species_data.iterrows():
                scientific = str(row.get('scientific_name', ''))
                if scientific:
                    normalized_scientific = self.normalize_name(scientific)
                    if (normalized_input in normalized_scientific or 
                        normalized_scientific in normalized_input):
                        print(f"[SPECIES_MATCHER] 부분 매칭 성공: {scientific}")
                        return self._format_species_info(row)
        
        print(f"[SPECIES_MATCHER] 매칭 실패: {species_name}")
        return None
    
    def _format_species_info(self, row: pd.Series) -> Dict:
        """종 정보 포맷팅"""
        info = {}
        
        # 기본 정보
        info['scientific_name'] = str(row.get('scientific_name', ''))
        info['korean_name'] = str(row.get('korean_name', ''))
        
        # 계통분류 정보
        taxonomy = {}
        taxonomy_fields = ['목', '과', '속', '종', 'order', 'family', 'genus', 'species']
        
        for field in taxonomy_fields:
            if field in row.index and pd.notna(row[field]):
                value = str(row[field])
                if value and value != 'nan':
                    if field in ['목', 'order']:
                        taxonomy['order'] = value
                    elif field in ['과', 'family']:
                        taxonomy['family'] = value
                    elif field in ['속', 'genus']:
                        taxonomy['genus'] = value
                    elif field in ['종', 'species']:
                        taxonomy['species'] = value
        
        info['taxonomy'] = taxonomy
        
        # 기타 정보
        other_fields = ['분포', '서식지', '크기', '특징', '생태', '비고']
        for field in other_fields:
            if field in row.index and pd.notna(row[field]):
                value = str(row[field])
                if value and value != 'nan':
                    info[field] = value
        
        return info
    
    def get_taxonomy_info(self, species_name: str) -> Optional[Dict]:
        """
        계통분류 정보만 반환
        
        Args:
            species_name: 종명
            
        Returns:
            계통분류 정보 딕셔너리
        """
        species_info = self.find_species_info(species_name)
        if species_info:
            return {
                'scientific_name': species_info.get('scientific_name', ''),
                'korean_name': species_info.get('korean_name', ''),
                'taxonomy': species_info.get('taxonomy', {})
            }
        return None
    
    def search_by_taxonomy(self, order: str = None, family: str = None, 
                          genus: str = None) -> List[Dict]:
        """
        계통분류 기준으로 검색
        
        Args:
            order: 목
            family: 과
            genus: 속
            
        Returns:
            매칭되는 종들의 리스트
        """
        if self.species_data is None or self.species_data.empty:
            return []
        
        results = []
        
        for idx, row in self.species_data.iterrows():
            match = True
            
            if order:
                row_order = str(row.get('목', row.get('order', '')))
                if order not in row_order:
                    match = False
            
            if family and match:
                row_family = str(row.get('과', row.get('family', '')))
                if family not in row_family:
                    match = False
            
            if genus and match:
                row_genus = str(row.get('속', row.get('genus', '')))
                scientific = str(row.get('scientific_name', ''))
                if genus not in row_genus and not scientific.startswith(genus):
                    match = False
            
            if match:
                results.append(self._format_species_info(row))
        
        return results[:10]  # 최대 10개만 반환


# 싱글톤 인스턴스
_species_matcher_instance = None

def get_species_matcher() -> SpeciesMatcher:
    """종 매칭기 싱글톤 인스턴스 반환"""
    global _species_matcher_instance
    if _species_matcher_instance is None:
        _species_matcher_instance = SpeciesMatcher()
    return _species_matcher_instance