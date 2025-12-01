"""
곤충 위험도 평가 모듈

선정된 5종의 곤충에 대한 과학적 위험도 평가를 수행합니다.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class RiskAssessor:
    """곤충 위험도 평가 시스템"""
    
    # 위험도 등급 정의
    RISK_LEVELS = {
        "safe": {"name": "안전", "color": "#4CAF50", "range": (0, 1.5)},
        "caution": {"name": "주의", "color": "#FFC107", "range": (1.5, 3.0)},
        "danger": {"name": "위험", "color": "#FF9800", "range": (3.0, 4.0)},
        "critical": {"name": "매우 위험", "color": "#F44336", "range": (4.0, 5.0)}
    }
    
    def __init__(self, data_path: Optional[str] = None):
        """
        초기화
        
        Args:
            data_path: 위험도 데이터 JSON 파일 경로
        """
        if data_path is None:
            data_path = Path(__file__).parent / "data" / "risk_data.json"
        
        self.data_path = Path(data_path)
        self.risk_database = self._load_risk_database()
    
    def _load_risk_database(self) -> Dict:
        """위험도 데이터베이스 로드"""
        if self.data_path.exists():
            with open(self.data_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            # 기본 데이터베이스 반환
            return self._get_default_database()
    
    def _get_default_database(self) -> Dict:
        """기본 위험도 데이터베이스"""
        return {
            # Type A: 무섭게 생겼지만 안전한 종
            "장수풍뎅이": {
                "scientific_name": "Allomyrina dichotoma",
                "category": "딱정벌레목",
                "risk_factors": {
                    "toxicity": 0,  # 독성
                    "aggression": 0,  # 공격성
                    "bite_sting": 0,  # 물림/쏘임
                    "allergy": 0,  # 알레르기
                    "severity": 0  # 중증도
                },
                "overall_risk": 0.0,
                "risk_level": "safe",
                "description": "큰 뿔과 위압적인 외형에도 불구하고 독이 없고 매우 온순합니다. 애완곤충으로 대량 사육될 정도로 안전합니다."
            },
            "왕사슴벌레": {
                "scientific_name": "Dorcus hopei",
                "category": "딱정벌레목",
                "risk_factors": {
                    "toxicity": 0,
                    "aggression": 1,
                    "bite_sting": 1,
                    "allergy": 0,
                    "severity": 0.5
                },
                "overall_risk": 0.5,
                "risk_level": "safe",
                "description": "큰 턱이 위협적으로 보이지만 독이 없습니다. 물려도 경미한 상처 수준으로, 애완용으로 인기가 있습니다."
            },
            "장수하늘소": {
                "scientific_name": "Callipogon relictus",
                "category": "딱정벌레목",
                "risk_factors": {
                    "toxicity": 0,
                    "aggression": 0.5,
                    "bite_sting": 0.5,
                    "allergy": 0,
                    "severity": 0
                },
                "overall_risk": 0.2,
                "risk_level": "safe",
                "protection_status": "천연기념물 제218호, 멸종위기 야생동물 1급",
                "description": "국내 최대 딱정벌레로 위압적이지만 독이 없고 공격성이 낮습니다. 천연기념물이므로 절대 포획 금지입니다."
            },
            "왕사마귀": {
                "scientific_name": "Tenodera angustipennis",
                "category": "사마귀목",
                "risk_factors": {
                    "toxicity": 0,
                    "aggression": 1,
                    "bite_sting": 1,
                    "allergy": 0,
                    "severity": 0.5
                },
                "overall_risk": 0.5,
                "risk_level": "safe",
                "description": "위협 자세가 공격적으로 보이지만 독이 없고 사람에게는 무해합니다. 포식성 곤충으로 해충을 잡아먹는 익충입니다."
            },
            
            # Type B: 무해해 보이지만 위험한 종
            "장수말벌": {
                "scientific_name": "Vespa mandarinia",
                "category": "벌목",
                "risk_factors": {
                    "toxicity": 5,
                    "aggression": 5,
                    "bite_sting": 5,
                    "allergy": 5,
                    "severity": 5
                },
                "overall_risk": 5.0,
                "risk_level": "critical",
                "mortality": "연평균 10명 이상 사망",
                "description": "국내 말벌류 중 독성이 가장 강합니다. 여러 번 반복해서 쏠 수 있으며, 아나필락시스 쇼크로 사망에 이를 수 있습니다."
            },
            "등검은말벌": {
                "scientific_name": "Vespa velutina nigrithorax",
                "category": "벌목",
                "risk_factors": {
                    "toxicity": 4.5,
                    "aggression": 5,
                    "bite_sting": 4.5,
                    "allergy": 4.5,
                    "severity": 4.5
                },
                "overall_risk": 4.6,
                "risk_level": "critical",
                "invasive_species": True,
                "description": "외래 침입종으로 공격성이 매우 높습니다. 도시 주거지에 둥지를 트는 경우가 많아 주의가 필요합니다."
            },
            "화상벌레": {
                "scientific_name": "Paederus fuscipes",
                "category": "딱정벌레목",
                "risk_factors": {
                    "toxicity": 4,
                    "aggression": 0,
                    "bite_sting": 0,
                    "allergy": 3,
                    "severity": 3.5
                },
                "overall_risk": 3.5,
                "risk_level": "danger",
                "toxin": "파데린 (pederin)",
                "description": "작고 무해해 보이지만 파데린 독소를 보유합니다. 손으로 누르면 화상 같은 통증과 물집이 생깁니다."
            },
            "독나방": {
                "scientific_name": "Euproctis spp.",
                "category": "나비목",
                "risk_factors": {
                    "toxicity": 3,
                    "aggression": 0,
                    "bite_sting": 0,
                    "allergy": 3.5,
                    "severity": 3
                },
                "overall_risk": 3.0,
                "risk_level": "caution",
                "description": "유충의 미세한 독모와 성충의 날개 가루로 독나방피부염을 일으킵니다. 맨손 접촉을 피해야 합니다."
            },
            "쐐기나방": {
                "scientific_name": "Limacodidae spp.",
                "category": "나비목",
                "risk_factors": {
                    "toxicity": 4,
                    "aggression": 0,
                    "bite_sting": 4,
                    "allergy": 3.5,
                    "severity": 4
                },
                "overall_risk": 4.0,
                "risk_level": "danger",
                "description": "화려한 가시털이 미세한 독침 역할을 합니다. 접촉 시 강한 통증과 염증, 심한 부종을 유발합니다."
            }
        }
    
    def assess_risk(self, species_name: str) -> Optional[Dict]:
        """
        종에 대한 위험도 평가 수행
        
        Args:
            species_name: 종 이름 (국명 또는 학명)
            
        Returns:
            위험도 평가 결과 딕셔너리
        """
        # 국명으로 검색
        if species_name in self.risk_database:
            return self._format_risk_result(species_name, self.risk_database[species_name])
        
        # 학명으로 검색
        for korean_name, data in self.risk_database.items():
            if data.get("scientific_name") == species_name:
                return self._format_risk_result(korean_name, data)
        
        # 부분 매칭 (속명 또는 과명)
        for korean_name, data in self.risk_database.items():
            scientific = data.get("scientific_name", "")
            if species_name in scientific or scientific in species_name:
                return self._format_risk_result(korean_name, data)
        
        return None
    
    def _format_risk_result(self, species_name: str, data: Dict) -> Dict:
        """위험도 평가 결과 포맷팅"""
        risk_level_info = self.RISK_LEVELS[data["risk_level"]]
        
        result = {
            "species_name": species_name,
            "scientific_name": data.get("scientific_name", ""),
            "category": data.get("category", ""),
            "risk_factors": data["risk_factors"],
            "overall_risk": data["overall_risk"],
            "risk_level": data["risk_level"],
            "risk_level_name": risk_level_info["name"],
            "risk_level_color": risk_level_info["color"],
            "description": data.get("description", ""),
            "warnings": self._generate_warnings(data),
            "response_guide": self._generate_response_guide(data)
        }
        
        # 추가 정보
        if "protection_status" in data:
            result["protection_status"] = data["protection_status"]
        if "mortality" in data:
            result["mortality"] = data["mortality"]
        if "invasive_species" in data:
            result["invasive_species"] = data["invasive_species"]
        if "toxin" in data:
            result["toxin"] = data["toxin"]
        
        return result
    
    def _generate_warnings(self, data: Dict) -> List[str]:
        """위험 요소별 경고 메시지 생성"""
        warnings = []
        risk_factors = data["risk_factors"]
        risk_level = data["risk_level"]
        
        if risk_level == "critical":
            warnings.append("⚠️ 매우 위험: 생명을 위협할 수 있습니다")
            if risk_factors["toxicity"] >= 4:
                warnings.append("🔴 강한 독성 보유")
            if risk_factors["aggression"] >= 4:
                warnings.append("🔴 높은 공격성")
            if risk_factors["allergy"] >= 4:
                warnings.append("🔴 아나필락시스 위험")
        
        elif risk_level == "danger":
            warnings.append("⚠️ 위험: 심각한 증상을 유발할 수 있습니다")
            if risk_factors["toxicity"] >= 3:
                warnings.append("🟠 독성 물질 보유")
            if risk_factors["allergy"] >= 3:
                warnings.append("🟠 알레르기 반응 가능")
        
        elif risk_level == "caution":
            warnings.append("⚠️ 주의: 접촉 시 불편한 증상 발생 가능")
            warnings.append("🟡 맨손 접촉 피하기")
        
        else:  # safe
            warnings.append("✅ 안전: 일반적으로 무해합니다")
            if data.get("protection_status"):
                warnings.append("🛡️ 보호종: 포획 및 채집 금지")
        
        return warnings
    
    def _generate_response_guide(self, data: Dict) -> Dict:
        """위험도별 대응 가이드 생성"""
        risk_level = data["risk_level"]
        species_name = data.get("scientific_name", "")
        
        if risk_level == "critical":
            return {
                "prevention": [
                    "둥지나 서식지 접근 금지",
                    "야외 활동 시 긴 옷 착용",
                    "향수나 밝은 색 옷 피하기"
                ],
                "first_aid": [
                    "쏘인 부위를 깨끗이 씻기",
                    "얼음찜질로 부기 완화",
                    "즉시 병원 방문 (119 연락)"
                ],
                "emergency": [
                    "호흡곤란, 어지러움 발생 시 즉시 응급실",
                    "전신 두드러기나 구토 증상 주의",
                    "과거 벌 알레르기 있으면 에피펜 휴대"
                ],
                "reporting": "둥지 발견 시 소방서(119) 또는 지자체에 신고"
            }
        
        elif risk_level == "danger":
            return {
                "prevention": [
                    "절대 손으로 만지지 말 것",
                    "종이나 테이프로 조심스럽게 제거",
                    "실내 침입 시 불빛 관리"
                ],
                "first_aid": [
                    "접촉 부위를 즉시 비누와 물로 씻기",
                    "문지르지 말고 흐르는 물로 헹구기",
                    "증상 심화 시 피부과 진료"
                ],
                "emergency": [
                    "물집이나 심한 발진 발생 시 병원 방문",
                    "눈이나 입에 닿았다면 즉시 응급실"
                ]
            }
        
        elif risk_level == "caution":
            return {
                "prevention": [
                    "맨손 접촉 피하기",
                    "어린이와 반려동물 접근 차단",
                    "발견 시 관찰만 하고 만지지 않기"
                ],
                "first_aid": [
                    "접촉 시 물로 씻어내기",
                    "가려움증 심하면 항히스타민제 복용",
                    "증상 지속 시 병원 방문"
                ]
            }
        
        else:  # safe
            guide = {
                "observation": [
                    "안전하게 관찰 가능",
                    "사진 촬영 권장",
                    "생태 교육 자료로 활용"
                ],
                "handling": [
                    "부드럽게 다루기",
                    "떨어뜨리지 않도록 주의",
                    "관찰 후 자연으로 돌려보내기"
                ]
            }
            
            if data.get("protection_status"):
                guide["legal"] = [
                    "천연기념물 또는 멸종위기종",
                    "포획 및 채집 절대 금지",
                    "발견 시 국립수목원 또는 환경부에 신고"
                ]
            
            return guide
    
    def get_risk_statistics(self) -> Dict:
        """전체 종의 위험도 통계"""
        stats = {
            "total": len(self.risk_database),
            "by_level": {"safe": 0, "caution": 0, "danger": 0, "critical": 0},
            "by_category": {}
        }
        
        for data in self.risk_database.values():
            level = data["risk_level"]
            category = data.get("category", "기타")
            
            stats["by_level"][level] += 1
            stats["by_category"][category] = stats["by_category"].get(category, 0) + 1
        
        return stats
    
    def compare_species(self, species1: str, species2: str) -> Optional[Dict]:
        """두 종의 위험도 비교"""
        risk1 = self.assess_risk(species1)
        risk2 = self.assess_risk(species2)
        
        if not risk1 or not risk2:
            return None
        
        return {
            "species1": risk1,
            "species2": risk2,
            "comparison": {
                "more_dangerous": species1 if risk1["overall_risk"] > risk2["overall_risk"] else species2,
                "risk_difference": abs(risk1["overall_risk"] - risk2["overall_risk"]),
                "key_differences": self._compare_risk_factors(risk1["risk_factors"], risk2["risk_factors"])
            }
        }
    
    def _compare_risk_factors(self, factors1: Dict, factors2: Dict) -> List[str]:
        """위험 요소별 차이점 분석"""
        differences = []
        factor_names = {
            "toxicity": "독성",
            "aggression": "공격성",
            "bite_sting": "물림/쏘임",
            "allergy": "알레르기",
            "severity": "중증도"
        }
        
        for key, name in factor_names.items():
            diff = factors1[key] - factors2[key]
            if abs(diff) >= 2:
                if diff > 0:
                    differences.append(f"{name}: 첫 번째 종이 훨씬 높음")
                else:
                    differences.append(f"{name}: 두 번째 종이 훨씬 높음")
        
        return differences


# 싱글톤 인스턴스
_risk_assessor_instance = None

def get_risk_assessor() -> RiskAssessor:
    """위험도 평가기 싱글톤 인스턴스 반환"""
    global _risk_assessor_instance
    if _risk_assessor_instance is None:
        _risk_assessor_instance = RiskAssessor()
    return _risk_assessor_instance
