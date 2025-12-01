"""
곤충 정보 제공 모듈

선정된 종에 대한 상세 생태 정보, 특징, 서식지, 주의사항 등을 제공합니다.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional


class InfoProvider:
    """곤충 정보 제공 시스템"""
    
    def __init__(self, data_path: Optional[str] = None):
        """
        초기화
        
        Args:
            data_path: 정보 데이터 JSON 파일 경로
        """
        if data_path is None:
            data_path = Path(__file__).parent / "data" / "species_info.json"
        
        self.data_path = Path(data_path)
        self.info_database = self._load_info_database()
    
    def _load_info_database(self) -> Dict:
        """정보 데이터베이스 로드"""
        if self.data_path.exists():
            with open(self.data_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # 기본 데이터베이스와 병합 (기본 데이터 우선)
                default_db = self._get_default_database()
                default_db.update(data)
                return default_db
        else:
            return self._get_default_database()
    
    def _get_default_database(self) -> Dict:
        """기본 정보 데이터베이스"""
        return {
            # Type A: 무섭게 생겼지만 안전한 종
            "장수풍뎅이": {
                "scientific_name": "Allomyrina dichotoma",
                "english_name": "Japanese rhinoceros beetle",
                "taxonomy": {
                    "order": "딱정벌레목 (Coleoptera)",
                    "family": "풍뎅이과 (Scarabaeidae)",
                    "genus": "Allomyrina",
                    "species": "A. dichotoma"
                },
                "description": "한국, 일본, 중국 등 동아시아에 분포하는 대형 딱정벌레입니다. 수컷은 머리와 가슴에 큰 뿔을 가지고 있어 위압적으로 보이지만, 실제로는 매우 온순하여 애완곤충으로 인기가 높습니다.",
                "characteristics": {
                    "size": "성충 수컷 30-54mm, 암컷 32-48mm",
                    "color": "적갈색에서 흑갈색",
                    "lifespan": "성충 2-3개월, 유충 1-2년",
                    "activity": "야행성, 주로 밤에 활동"
                },
                "ecology": {
                    "habitat": "참나무, 느티나무 등 활엽수림",
                    "distribution": "한국 전역 (산림 지역)",
                    "season": "6월~8월 (여름)",
                    "diet": "성충: 나무 수액, 유충: 부엽토",
                    "behavior": "나무 수액 자리에서 다른 곤충들과 경쟁"
                },
                "reproduction": {
                    "mating": "여름철 나무 수액 자리에서 만남",
                    "eggs": "암컷이 땅속에 20-30개 산란",
                    "development": "알 → 유충(1-2년) → 번데기 → 성충"
                },
                "interaction": {
                    "with_humans": "무해, 애완곤충으로 인기",
                    "handling": "부드럽게 다루면 안전",
                    "benefits": "생태 교육, 관찰 학습 자료",
                    "cautions": [
                        "떨어뜨리지 않도록 주의",
                        "다리가 부러지기 쉬우므로 조심",
                        "관찰 후 자연으로 돌려보내기"
                    ]
                },
                "conservation": {
                    "status": "보통종 (개체수 안정)",
                    "threats": "서식지 감소, 남획",
                    "protection": "특별한 보호 조치 없음"
                },
                "cultural": {
                    "significance": "어린이들에게 인기 있는 곤충",
                    "folklore": "힘의 상징, 여름의 대표 곤충",
                    "education": "곤충 생태 교육의 좋은 소재"
                },
                "references": [
                    "한국의 딱정벌레 (2007), 국립생물자원관",
                    "한국곤충생태도감 (2015), 환경부"
                ]
            },
            
            "왕사슴벌레": {
                "scientific_name": "Dorcus hopei",
                "english_name": "Korean stag beetle",
                "taxonomy": {
                    "order": "딱정벌레목 (Coleoptera)",
                    "family": "사슴벌레과 (Lucanidae)",
                    "genus": "Dorcus",
                    "species": "D. hopei"
                },
                "description": "한국 고유아종으로, 수컷은 발달한 큰턱을 가지고 있습니다. 외형이 위협적이지만 독이 없고 온순하여 애완용으로 사육됩니다.",
                "characteristics": {
                    "size": "수컷 28-75mm, 암컷 25-45mm",
                    "color": "흑갈색에서 검은색",
                    "lifespan": "성충 1-2년",
                    "activity": "야행성"
                },
                "ecology": {
                    "habitat": "참나무류 고사목, 썩은 나무",
                    "distribution": "한국 전역 (산림 지역)",
                    "season": "6월~9월",
                    "diet": "성충: 나무 수액, 유충: 썩은 나무",
                    "behavior": "영역 다툼 시 큰턱으로 위협"
                },
                "reproduction": {
                    "mating": "여름철 고사목에서",
                    "eggs": "썩은 나무 속에 산란",
                    "development": "유충 기간 1-2년"
                },
                "interaction": {
                    "with_humans": "무해, 애완곤충",
                    "handling": "큰턱에 물리지 않도록 주의",
                    "benefits": "생태 교육, 관찰 학습",
                    "cautions": [
                        "큰턱에 손가락을 오래 물리지 않기",
                        "물려도 경미한 상처 수준",
                        "억지로 떼어내지 말고 자연스럽게 놓을 때까지 기다리기"
                    ]
                },
                "conservation": {
                    "status": "보통종",
                    "threats": "서식지 감소",
                    "protection": "없음"
                },
                "cultural": {
                    "significance": "애완곤충으로 인기",
                    "folklore": "힘과 용맹의 상징",
                    "education": "곤충 사육 교육 자료"
                },
                "references": [
                    "한국의 사슴벌레 (2010), 국립생물자원관"
                ]
            },
            
            "장수하늘소": {
                "scientific_name": "Callipogon relictus",
                "english_name": "Korean longhorn beetle",
                "taxonomy": {
                    "order": "딱정벌레목 (Coleoptera)",
                    "family": "하늘소과 (Cerambycidae)",
                    "genus": "Callipogon",
                    "species": "C. relictus"
                },
                "description": "한국 특산종으로 국내 최대 딱정벌레입니다. 천연기념물 제218호이자 멸종위기 야생동물 1급으로 지정되어 엄격히 보호받고 있습니다.",
                "characteristics": {
                    "size": "수컷 60-110mm, 암컷 50-80mm",
                    "color": "광택 있는 흑갈색",
                    "lifespan": "성충 수개월, 유충 3-5년",
                    "activity": "야행성"
                },
                "ecology": {
                    "habitat": "원시림의 대형 고사목 (참나무, 물푸레나무 등)",
                    "distribution": "광릉숲, 설악산, 지리산 등 극히 제한적",
                    "season": "7월~8월",
                    "diet": "유충: 썩은 나무, 성충: 나무 수액",
                    "behavior": "야간에 불빛에 끌려 날아옴"
                },
                "reproduction": {
                    "mating": "여름철 원시림에서",
                    "eggs": "대형 고사목에 산란",
                    "development": "유충 기간 3-5년 (매우 긴 편)"
                },
                "interaction": {
                    "with_humans": "무해하나 접촉 금지 (보호종)",
                    "handling": "절대 포획 금지 (법적 처벌)",
                    "benefits": "생태계 건강성 지표종",
                    "cautions": [
                        "발견 시 국립수목원 또는 환경부에 신고",
                        "사진 촬영 후 그대로 두기",
                        "포획 시 최대 5년 이하 징역 또는 5천만원 이하 벌금"
                    ]
                },
                "conservation": {
                    "status": "천연기념물 제218호, 멸종위기 야생동물 1급",
                    "threats": "서식지 파괴, 기후변화, 불법 채집",
                    "protection": "문화재보호법, 야생생물법으로 보호",
                    "efforts": "광릉숲 보호, 인공 증식 연구"
                },
                "cultural": {
                    "significance": "한국의 보물, 생태계 건강성 상징",
                    "folklore": "원시림의 수호자",
                    "education": "생물다양성 보전 교육 자료"
                },
                "references": [
                    "장수하늘소 생태 연구 (2015), 국립수목원",
                    "멸종위기종 복원 연구 (2020), 환경부"
                ]
            },
            
            "왕사마귀": {
                "scientific_name": "Tenodera angustipennis",
                "english_name": "Narrow-winged mantis",
                "taxonomy": {
                    "order": "사마귀목 (Mantodea)",
                    "family": "사마귀과 (Mantidae)",
                    "genus": "Tenodera",
                    "species": "T. angustipennis"
                },
                "description": "한국에서 가장 흔한 대형 사마귀로, 포식성 곤충입니다. 위협 자세가 공격적으로 보이지만 사람에게는 무해하며, 해충을 잡아먹는 익충입니다.",
                "characteristics": {
                    "size": "60-95mm",
                    "color": "녹색 또는 갈색",
                    "lifespan": "성충 수개월",
                    "activity": "주간 활동"
                },
                "ecology": {
                    "habitat": "풀밭, 관목지, 농경지",
                    "distribution": "한국 전역",
                    "season": "7월~10월",
                    "diet": "곤충, 거미 등 (포식성)",
                    "behavior": "매복 사냥, 위협 시 앞다리 치켜듦"
                },
                "reproduction": {
                    "mating": "가을철, 교미 후 암컷이 수컷을 잡아먹기도 함",
                    "eggs": "난낭(알집)에 100-200개 산란",
                    "development": "알 → 약충 → 성충 (불완전변태)"
                },
                "interaction": {
                    "with_humans": "무해, 익충",
                    "handling": "물릴 수 있으나 경미",
                    "benefits": "해충 포식, 생태계 균형 유지",
                    "cautions": [
                        "억지로 잡지 않기",
                        "물려도 국소적 상처 수준",
                        "연가시는 사람에게 감염 안 됨"
                    ]
                },
                "conservation": {
                    "status": "보통종",
                    "threats": "서식지 감소, 농약",
                    "protection": "없음"
                },
                "cultural": {
                    "significance": "익충으로 인식",
                    "folklore": "연가시 괴담 (실제로는 무해)",
                    "education": "포식자-피식자 관계 학습"
                },
                "references": [
                    "한국의 사마귀목 (2012), 국립생물자원관"
                ]
            },
            
            # Type B: 무해해 보이지만 위험한 종
            "장수말벌": {
                "scientific_name": "Vespa mandarinia",
                "english_name": "Asian giant hornet",
                "taxonomy": {
                    "order": "벌목 (Hymenoptera)",
                    "family": "말벌과 (Vespidae)",
                    "genus": "Vespa",
                    "species": "V. mandarinia"
                },
                "description": "세계 최대 말벌로, 국내 말벌류 중 독성이 가장 강합니다. 매년 벌쏘임 사고로 사망자가 발생하는 위험한 종입니다.",
                "characteristics": {
                    "size": "여왕벌 40-45mm, 일벌 27-40mm",
                    "color": "주황색 머리, 검은색과 노란색 줄무늬",
                    "lifespan": "여왕벌 1년, 일벌 수개월",
                    "activity": "주간 활동"
                },
                "ecology": {
                    "habitat": "산림, 농촌 지역",
                    "distribution": "한국 전역 (산림 지역)",
                    "season": "5월~11월 (8-9월 가장 공격적)",
                    "diet": "곤충, 꿀벌, 수액 등",
                    "behavior": "집단 생활, 영역 방어 시 매우 공격적"
                },
                "reproduction": {
                    "mating": "가을철",
                    "nest": "땅속, 나무 구멍, 처마 밑",
                    "colony": "수백 마리 집단"
                },
                "interaction": {
                    "with_humans": "매우 위험",
                    "venom": "강한 신경독, 용혈독",
                    "symptoms": "극심한 통증, 부종, 아나필락시스",
                    "mortality": "연평균 10명 이상 사망",
                    "cautions": [
                        "둥지 접근 절대 금지",
                        "여러 마리에게 쏘이면 생명 위협",
                        "쏘인 후 호흡곤란 시 즉시 119",
                        "향수나 밝은 색 옷 피하기"
                    ]
                },
                "first_aid": {
                    "immediate": [
                        "쏘인 부위를 깨끗이 씻기",
                        "얼음찜질로 부기 완화",
                        "침이 남아있으면 카드로 긁어내기"
                    ],
                    "emergency": [
                        "호흡곤란, 어지러움 발생 시 즉시 응급실",
                        "전신 두드러기나 구토 증상 주의",
                        "과거 벌 알레르기 있으면 에피펜 사용"
                    ],
                    "reporting": "둥지 발견 시 소방서(119) 또는 지자체에 신고"
                },
                "conservation": {
                    "status": "보통종",
                    "management": "위험 둥지 제거 사업",
                    "protection": "없음 (위해 종)"
                },
                "cultural": {
                    "significance": "위험 곤충으로 인식",
                    "folklore": "공포의 대상",
                    "education": "벌쏘임 예방 교육"
                },
                "references": [
                    "국내 말벌류 독성 연구 (2023), 국립수목원",
                    "벌쏘임 사고 통계 (2024), 소방청"
                ]
            },
            
            "등검은말벌": {
                "scientific_name": "Vespa velutina nigrithorax",
                "english_name": "Asian hornet",
                "taxonomy": {
                    "order": "벌목 (Hymenoptera)",
                    "family": "말벌과 (Vespidae)",
                    "genus": "Vespa",
                    "species": "V. velutina nigrithorax"
                },
                "description": "2000년대 초반 국내에 유입된 외래 침입종으로, 꿀벌을 대량으로 포식하여 생태계를 교란합니다. 공격성이 높고 도시 지역에도 둥지를 틉니다.",
                "characteristics": {
                    "size": "여왕벌 30mm, 일벌 17-24mm",
                    "color": "검은색 가슴, 주황색 배 끝",
                    "lifespan": "여왕벌 1년, 일벌 수개월",
                    "activity": "주간 활동"
                },
                "ecology": {
                    "habitat": "도시, 농촌, 산림 (다양한 환경)",
                    "distribution": "한국 전역 (급속 확산 중)",
                    "season": "4월~11월",
                    "diet": "꿀벌 (주식), 곤충",
                    "behavior": "꿀벌 포식, 집단 공격"
                },
                "reproduction": {
                    "mating": "가을철",
                    "nest": "나무, 처마, 전봇대 등 (축구공 크기)",
                    "colony": "수천 마리 집단"
                },
                "interaction": {
                    "with_humans": "위험",
                    "venom": "강한 독성",
                    "symptoms": "통증, 부종, 아나필락시스 위험",
                    "cautions": [
                        "회갈색 축구공 크기 둥지 주의",
                        "공원, 주택가에서도 발견",
                        "둥지 접근 금지",
                        "쏘임 시 즉시 병원"
                    ]
                },
                "first_aid": {
                    "immediate": [
                        "쏘인 부위 씻기",
                        "얼음찜질",
                        "항히스타민제 복용"
                    ],
                    "emergency": [
                        "호흡곤란 시 즉시 응급실",
                        "여러 마리에게 쏘인 경우 119"
                    ],
                    "reporting": "둥지 발견 시 지자체 또는 119 신고"
                },
                "conservation": {
                    "status": "외래 침입종 (생태계 교란종)",
                    "management": "적극적 퇴치 사업 진행 중",
                    "impact": "꿀벌 개체수 감소, 양봉 피해"
                },
                "cultural": {
                    "significance": "외래종 문제 인식",
                    "education": "생태계 보전 교육"
                },
                "references": [
                    "등검은말벌 확산 현황 (2024), 환경부",
                    "외래 침입종 관리 (2023), 국립생태원"
                ]
            },
            
            "화상벌레": {
                "scientific_name": "Paederus fuscipes",
                "english_name": "Rove beetle",
                "taxonomy": {
                    "order": "딱정벌레목 (Coleoptera)",
                    "family": "반날개과 (Staphylinidae)",
                    "genus": "Paederus",
                    "species": "P. fuscipes"
                },
                "description": "작고 무해해 보이지만 파데린 독소를 보유한 딱정벌레입니다. 손으로 누르면 화상 같은 통증과 물집이 생깁니다.",
                "characteristics": {
                    "size": "7-10mm",
                    "color": "머리와 배 끝 검정, 가슴과 배 주황색",
                    "lifespan": "수개월",
                    "activity": "야행성, 불빛에 끌림"
                },
                "ecology": {
                    "habitat": "논, 밭, 습지 주변",
                    "distribution": "한국 전역",
                    "season": "5월~9월 (여름철)",
                    "diet": "작은 곤충, 유충",
                    "behavior": "불빛에 끌려 실내 침입"
                },
                "reproduction": {
                    "mating": "여름철",
                    "eggs": "습한 토양에 산란",
                    "development": "알 → 유충 → 번데기 → 성충"
                },
                "interaction": {
                    "with_humans": "위험 (접촉 시)",
                    "toxin": "파데린 (pederin) - 강한 피부 자극 물질",
                    "symptoms": "화상 같은 통증, 선형 발진, 물집",
                    "cautions": [
                        "절대 손으로 누르거나 문지르지 말 것",
                        "종이나 테이프로 제거",
                        "접촉 시 즉시 비누로 씻기"
                    ]
                },
                "first_aid": {
                    "immediate": [
                        "접촉 부위를 즉시 비누와 물로 씻기",
                        "문지르지 말고 흐르는 물로 헹구기",
                        "냉찜질로 통증 완화"
                    ],
                    "treatment": [
                        "스테로이드 연고 도포",
                        "항히스타민제 복용",
                        "물집 터뜨리지 않기"
                    ],
                    "medical": [
                        "심한 발진이나 물집 발생 시 피부과 진료",
                        "눈이나 입에 닿았다면 즉시 응급실"
                    ]
                },
                "conservation": {
                    "status": "보통종",
                    "management": "실내 침입 예방 (불빛 관리)"
                },
                "cultural": {
                    "significance": "인지도 낮은 위험 곤충",
                    "education": "작은 곤충도 위험할 수 있음을 알리는 사례"
                },
                "references": [
                    "화상벌레 피부염 사례 (2020), 대한피부과학회",
                    "Paederus 속 독성 연구 (2018), 한국곤충학회"
                ]
            },
            
            "독나방": {
                "scientific_name": "Euproctis spp.",
                "english_name": "Tussock moth",
                "taxonomy": {
                    "order": "나비목 (Lepidoptera)",
                    "family": "독나방과 (Erebidae)",
                    "genus": "Euproctis",
                    "species": "여러 종"
                },
                "description": "유충의 미세한 독모와 성충의 날개 가루로 독나방피부염을 일으킵니다. 특히 어린이와 반려동물에게 주의가 필요합니다.",
                "characteristics": {
                    "size": "성충 20-40mm, 유충 30-40mm",
                    "color": "성충: 흰색, 유충: 털이 많음",
                    "lifespan": "성충 1-2주, 유충 수개월",
                    "activity": "야행성 (성충)"
                },
                "ecology": {
                    "habitat": "활엽수림, 과수원",
                    "distribution": "한국 전역",
                    "season": "6월~9월",
                    "diet": "유충: 나뭇잎 (식엽성)",
                    "behavior": "집단 발생 가능"
                },
                "reproduction": {
                    "mating": "여름철",
                    "eggs": "나뭇잎에 집단 산란",
                    "development": "알 → 유충 → 번데기 → 성충"
                },
                "interaction": {
                    "with_humans": "주의 필요",
                    "toxin": "독모 (urticating setae)",
                    "symptoms": "발진, 가려움, 물집, 결막염",
                    "cautions": [
                        "유충 맨손 접촉 금지",
                        "성충의 날개 가루도 위험",
                        "어린이 교육 필요",
                        "반려견 산책 시 주의"
                    ]
                },
                "first_aid": {
                    "immediate": [
                        "접촉 시 문지르지 말고 물로 씻어내기",
                        "테이프로 독모 제거",
                        "냉찜질"
                    ],
                    "treatment": [
                        "항히스타민제 복용",
                        "스테로이드 연고 도포",
                        "가려워도 긁지 않기"
                    ],
                    "medical": [
                        "심한 발진 시 피부과 진료",
                        "눈에 들어간 경우 안과 진료"
                    ]
                },
                "conservation": {
                    "status": "보통종",
                    "management": "과수원 해충 관리"
                },
                "cultural": {
                    "significance": "어린이 안전 교육 대상",
                    "education": "예쁜 애벌레도 만지면 안 됨"
                },
                "references": [
                    "독나방피부염 연구 (2019), 대한피부과학회",
                    "한국의 나비목 해충 (2016), 농촌진흥청"
                ]
            },
            
            "쐐기나방": {
                "scientific_name": "Limacodidae spp.",
                "english_name": "Slug caterpillar moth",
                "taxonomy": {
                    "order": "나비목 (Lepidoptera)",
                    "family": "쐐기나방과 (Limacodidae)",
                    "genus": "여러 속",
                    "species": "여러 종"
                },
                "description": "화려한 가시털을 가진 유충으로, 각 털이 미세한 독침 역할을 합니다. 접촉 시 강한 통증과 염증을 유발합니다.",
                "characteristics": {
                    "size": "유충 20-30mm",
                    "color": "녹색, 노란색, 빨간색 등 화려함",
                    "lifespan": "유충 수개월",
                    "activity": "주간 활동"
                },
                "ecology": {
                    "habitat": "활엽수림, 과수원",
                    "distribution": "한국 전역",
                    "season": "7월~9월",
                    "diet": "나뭇잎 (식엽성)",
                    "behavior": "나뭇잎 위에서 천천히 이동"
                },
                "reproduction": {
                    "mating": "여름철",
                    "eggs": "나뭇잎에 산란",
                    "development": "알 → 유충 → 번데기 → 성충"
                },
                "interaction": {
                    "with_humans": "위험",
                    "toxin": "독침 가시털",
                    "symptoms": "즉각적인 강한 통증, 부종, 발진",
                    "cautions": [
                        "화려한 애벌레는 절대 접촉 금지",
                        "나무 밑 지나갈 때 주의",
                        "반려견 입·혀 접촉 시 응급",
                        "어린이 교육 필수"
                    ]
                },
                "first_aid": {
                    "immediate": [
                        "테이프로 가시 제거",
                        "물로 씻어내기 (문지르지 말 것)",
                        "얼음찜질로 통증 완화"
                    ],
                    "treatment": [
                        "진통제 복용",
                        "항히스타민제 복용",
                        "스테로이드 연고 도포"
                    ],
                    "medical": [
                        "심한 통증이나 부종 시 병원 방문",
                        "반려동물 구강 접촉 시 즉시 동물병원"
                    ]
                },
                "conservation": {
                    "status": "보통종",
                    "management": "과수원 해충 관리"
                },
                "cultural": {
                    "significance": "위험한 애벌레로 인식",
                    "folklore": "쐐기벌레",
                    "education": "야외 활동 시 주의 교육"
                },
                "references": [
                    "쐐기나방 유충 독성 연구 (2017), 한국곤충학회",
                    "야외 활동 안전 가이드 (2021), 산림청"
                ]
            }
        }
    
    def get_info(self, species_name: str) -> Optional[Dict]:
        """
        종에 대한 상세 정보 제공
        
        Args:
            species_name: 종 이름 (국명 또는 학명)
            
        Returns:
            상세 정보 딕셔너리
        """
        print(f"[INFO_PROVIDER] 검색 중: {species_name}")
        
        # 국명으로 검색
        if species_name in self.info_database:
            print(f"[INFO_PROVIDER] 국명 매칭 성공: {species_name}")
            return self._format_info(species_name, self.info_database[species_name])
        
        # 학명으로 검색
        for korean_name, data in self.info_database.items():
            scientific = data.get("scientific_name", "")
            print(f"[INFO_PROVIDER] 학명 비교: '{species_name}' vs '{scientific}'")
            if scientific == species_name:
                print(f"[INFO_PROVIDER] 학명 매칭 성공: {korean_name}")
                return self._format_info(korean_name, data)
        
        # 부분 매칭 (언더스코어를 공백으로 변환하여 매칭)
        normalized_species = species_name.replace("_", " ")
        print(f"[INFO_PROVIDER] 정규화된 종명: '{normalized_species}'")
        
        # 정확한 매칭 우선
        for korean_name, data in self.info_database.items():
            scientific = data.get("scientific_name", "")
            print(f"[INFO_PROVIDER] 정확한 매칭 비교: '{normalized_species}' vs '{scientific}'")
            if normalized_species == scientific:
                print(f"[INFO_PROVIDER] 정확한 매칭 성공: {korean_name}")
                return self._format_info(korean_name, data)
        
        # 부분 매칭 (종명 포함)
        for korean_name, data in self.info_database.items():
            scientific = data.get("scientific_name", "")
            print(f"[INFO_PROVIDER] 부분 매칭 비교: '{normalized_species}' vs '{scientific}'")
            if normalized_species in scientific or scientific in normalized_species:
                print(f"[INFO_PROVIDER] 부분 매칭 성공: {korean_name}")
                return self._format_info(korean_name, data)
        
        # 속명 매칭 제거 - 정확한 종명만 반환
        print(f"[INFO_PROVIDER] 매칭 실패: {species_name}")
        return None
    
    def _format_info(self, species_name: str, data: Dict) -> Dict:
        """정보 포맷팅 - species_info.json의 모든 필드 포함"""
        result = {
            "species_name": species_name,
            "scientific_name": data.get("scientific_name", ""),
            "korean_name": data.get("korean_name", species_name),
            "english_name": data.get("english_name", ""),
            "ktsn": data.get("ktsn", ""),
            "taxonomy": data.get("taxonomy", {}),
            "synonyms": data.get("synonyms", []),
            "description": data.get("description", ""),
            "distribution": data.get("distribution", {}),
            "characteristics": data.get("characteristics", {}),
            "physical_characteristics": data.get("physical_characteristics", {}),
            "habitat": data.get("habitat", {}),
            "ecology": data.get("ecology", {}),
            "reproduction": data.get("reproduction", {}),
            "interaction": data.get("interaction", {}),
            "risk_assessment": data.get("risk_assessment", {}),
            "prevention_measures": data.get("prevention_measures", []),
            "first_aid": data.get("first_aid", {}),
            "conservation": data.get("conservation", {}),
            "cultural": data.get("cultural", {}),
            "references": data.get("references", []),
            "other_info": data.get("other_info", ""),
            "specimen_count": data.get("specimen_count", 0),
            "material_count": data.get("material_count", 0),
            "genetic_count": data.get("genetic_count", 0),
            "utility_count": data.get("utility_count", 0),
            "beneficial_effects": data.get("beneficial_effects", []),
            "invasion_routes": data.get("invasion_routes", {}),
            "special_adaptations": data.get("special_adaptations", [])
        }
        # data에 있는 모든 추가 필드도 포함
        for key, value in data.items():
            if key not in result:
                result[key] = value
        return result
    
    def get_summary(self, species_name: str) -> Optional[str]:
        """종에 대한 간단한 요약 정보"""
        info = self.get_info(species_name)
        if not info:
            return None
        
        return f"{info['species_name']} ({info['scientific_name']})는 {info['description']}"
    
    def get_quick_facts(self, species_name: str) -> Optional[Dict]:
        """종에 대한 핵심 정보만 추출"""
        info = self.get_info(species_name)
        if not info:
            return None
        
        return {
            "species_name": info["species_name"],
            "scientific_name": info["scientific_name"],
            "size": info["characteristics"].get("size", "정보 없음"),
            "habitat": info["ecology"].get("habitat", "정보 없음"),
            "season": info["ecology"].get("season", "정보 없음"),
            "description": info["description"]
        }


# 싱글톤 인스턴스
_info_provider_instance = None

def get_info_provider() -> InfoProvider:
    """정보 제공자 싱글톤 인스턴스 반환"""
    global _info_provider_instance
    if _info_provider_instance is None:
        _info_provider_instance = InfoProvider()
    return _info_provider_instance
