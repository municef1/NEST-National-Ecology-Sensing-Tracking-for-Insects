# NEST - National Ecology Sensing & Tracking for Insects

한국 곤충 생태 모니터링 및 위험도 평가 시스템

## 프로젝트 개요

NEST는 AI 기반 곤충 탐지·분류·위험도 평가 시스템으로, 시민 참여형 생태 데이터 수집 플랫폼입니다. YOLOv8 객체 탐지와 EfficientNet, ResNet 계층적 분류 모델을 활용하여 곤충을 자동으로 식별하고, 생태학적 위험도를 평가합니다.

## 주요 기능

### 🔍 AI 기반 곤충 탐지 및 분류
- **YOLOv8 객체 탐지**: 이미지에서 곤충 자동 탐지
- **인터랙티브 바운딩 박스**: 드래그로 위치/크기 조정 가능
- **4단계 계층적 분류**: Order(목) → Family(과) → Genus(속) → Species(종)
- **다중 후보 제시**: 종 분류 시 신뢰도 기반 상위 3개 후보 제공

### ⚠️ 위험도 평가 시스템
- **6단계 위험도 분류**: 인체 고위험, 중위험, 반려동물 위험, 일반·불쾌, 보호종, 미분류
- **상세 대응 가이드**: 예방법, 관찰 요령, 응급 처치 정보 제공
- **시각적 위험도 표시**: 색상 코드 기반 직관적 표시

### 🗺️ 생태지도 및 분포 시각화
- **GPS 기반 위치 추적**: EXIF 데이터에서 위치 정보 자동 추출
- **위험도 기반 필터링**: 위험도별 관찰 지점 필터링
- **실시간 날씨 정보**: OpenWeatherMap API 연동
- **통계 대시보드**: 위험도별 관찰 통계

### 👥 소셜 기능
- **관찰 기록 공유**: 오늘의 관찰 및 베스트 관찰
- **좋아요 및 댓글**: 커뮤니티 상호작용
- **내 주변 관찰**: 위치 기반 주변 관찰 정보

## 기술 스택

### Backend
- **Flask**: 웹 프레임워크
- **PyTorch**: 딥러닝 프레임워크
- **Ultralytics YOLOv8**: 객체 탐지
- **EfficientNet / ResNet**: 계층적 이미지 분류

### Frontend
- **HTML5/CSS3**: 반응형 웹 디자인
- **Vanilla JavaScript**: 인터랙티브 UI
- **Canvas API**: 바운딩 박스 편집

### Data & APIs
- **JSON**: 분류 정보 및 위험도 데이터 저장
- **OpenWeatherMap API**: 날씨 정보
- **EXIF**: 이미지 메타데이터 추출

## 설치 및 실행

### 필수 요구사항
- Python 3.8+
- CUDA (GPU 사용 권장)

### 설치

```bash
# Windows
install_requirements.bat

# Linux/Mac
pip install -r requirements.txt
```

### 실행

```bash
python app.py
```

서버 실행 후 `http://localhost:8000` 접속

## 프로젝트 구조

```
NEST_Project_Complete_v2.0.9/
├── app.py                          # Flask 메인 애플리케이션
├── utils/                          # 유틸리티 모듈
│   ├── detector.py                 # YOLOv8 곤충 탐지
│   ├── classifier.py               # EfficientNet 목 분류
│   ├── hierarchical_classifier.py  # 계층적 분류 (과→속→종)
│   ├── risk_assessor.py            # 위험도 평가
│   ├── info_provider.py            # 곤충 상세 정보 제공
│   ├── weather_provider.py         # 날씨 정보 제공
│   ├── classification_storage.py   # 분류 결과 저장
│   ├── social_storage.py           # 소셜 기능 (좋아요/댓글)
│   ├── species_matcher.py          # 종명 매칭
│   ├── map_location_extract.py     # GPS 위치 추출
│   ├── data/                       # 데이터 파일
│   │   ├── classifications.json    # 분류 결과 저장소
│   │   ├── social_data.json        # 소셜 데이터 저장소
│   │   ├── species_info.json       # 곤충 상세 정보 DB
│   │   └── insect_species_final.csv # 곤충 종 데이터
│   └── models/                     # AI 모델 가중치
│       ├── best_detector.pt        # 학습된 YOLOv8 모델
│       ├── yolov8n.pt              # 기본 YOLOv8 모델
│       ├── order/                  # 목 분류 모델
│       ├── family/                 # 과 분류 모델 (목별)
│       ├── genus/                  # 속 분류 모델 (과별)
│       └── species/                # 종 분류 모델 (속별)
├── templates/                      # HTML 템플릿
│   ├── index.html                  # 메인 페이지 (탐지/분류)
│   ├── board.html                  # 게시판 (관찰 공유)
│   └── map.html                    # 생태지도
├── static/                         # 정적 파일
│   ├── animations.css              # 애니메이션 스타일
│   └── app.js                      # 클라이언트 스크립트
├── uploads/                        # 업로드된 이미지
├── results/                        # 탐지 결과 이미지
├── crops/                          # 크롭된 곤충 이미지
└── docs/                           # 문서 및 스크린샷
```

## 워크플로우

### 1단계: 이미지 업로드
사용자가 곤충 사진을 업로드하면 파일 검증 후 안전하게 저장

### 2단계: 곤충 탐지
YOLOv8 기반 전이학습된 모델이 이미지에서 곤충을 탐지하고 바운딩 박스 생성

### 3단계: 바운딩 박스 조정
사용자가 드래그로 바운딩 박스 위치/크기 조정 가능

### 4단계: 계층적 분류
- 목 분류 (곤충 목 분류 모델)
- 과 분류 (목별 전문 모델)
- 속 분류 (과별 전문 모델)
- 종 분류 (속별 전문 모델, 상위 3개 후보 제시)

### 5단계: 위험도 평가 및 정보 제공
- 위험도 등급 및 대응 가이드 표시
- 곤충 상세 정보 (국명, 학명, 생태 정보)
- 날씨 정보 및 관찰 조건

## 주요 특징

### 🎯 높은 정확도
- 계층적 분류로 단계별 정확도 향상
- 목별 전문화된 모델로 세밀한 분류
- 다중 후보 제시로 사용자 선택 가능

### 🔒 안전성
- 파일 형식 검증 및 크기 제한
- 안전한 파일명 생성
- 세션 기반 데이터 관리

### 🚀 성능 최적화
- 싱글톤 패턴으로 모델 로딩 최소화
- GPU 자동 감지 및 활용
- 이미지 적응적 크기 조정

### 📱 사용자 경험
- 직관적인 5단계 프로세스
- 반응형 디자인
- 실시간 피드백


## 개발팀

2025년 새싹해커톤 NESTLab
