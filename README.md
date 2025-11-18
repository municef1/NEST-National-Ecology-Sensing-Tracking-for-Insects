# 🐛 곤충 탐지 및 분류 시스템 (Lite Version)

AI 기반 2단계 곤충 분석 시스템의 핵심 기능만 포함한 경량화 버전입니다.

## ✨ 주요 기능

### 🎯 **2단계 AI 파이프라인**
1. **곤충 탐지**: YOLOv8 기반 이미지에서 곤충 자동 탐지 (TTA 제거로 속도 향상)
2. **목 분류**: EfficientNet 기반 곤충 목(目) 분류 (TTA 적용으로 정확도 향상)

### 🔐 **보안 시스템**
- IP 화이트리스트 기반 접근 제어
- 악성 패턴 자동 감지 및 차단
- 사용자 인증 시스템

### 🎨 **사용자 인터페이스**
- 토스 스타일 모던 디자인
- 드래그앤드롭 파일 업로드
- 반응형 웹 디자인

## 🚀 빠른 시작

### 1. 환경 설정
```bash
cd insect-detection-demo2
pip install -r requirements.txt
```

### 2. 환경 변수 설정
```bash
cp .env.example .env
# .env 파일을 편집하여 Supabase 설정 추가
```

### 3. 실행
```bash
cd src
python main.py
```

### 4. 접속
```
http://localhost:8000
```

## 📁 프로젝트 구조

```
insect-detection-demo2/
├── src/                    # 소스 코드
│   ├── main.py            # 메인 Flask 서버
│   ├── detector.py        # 곤충 탐지 모듈
│   ├── order_classifier.py # 목 분류 모듈
│   ├── auth.py            # 인증 시스템
│   ├── utils.py           # 유틸리티 함수
│   └── ip_*.py            # 보안 모듈
├── templates/             # HTML 템플릿
│   ├── index.html         # 메인 페이지
│   └── login.html         # 로그인 페이지
├── static/                # 정적 파일
│   ├── style.css          # 스타일시트
│   └── script.js          # JavaScript
├── uploads/               # 업로드 폴더
├── results/               # 결과 폴더
└── requirements.txt       # 의존성 패키지
```

## 🔧 모델 설정

### 탐지 모델
- **경로**: `runs_insect_new/augmented_train/weights/best.pt`
- **폴백**: YOLOv8n (모델 파일이 없는 경우)
- **TTA**: 비활성화 (속도 우선)

### 분류 모델
- **경로**: `best_detected_order_classifier_224.pth`
- **클래스**: 24개 곤충 목
- **TTA**: 활성화 (정확도 우선)

## 🛡️ 보안 기능

### IP 화이트리스트
- `whitelist.json`에서 허용 IP 관리
- 사설 IP 대역 기본 허용
- 동적 IP 추가/제거 가능

### 악성 패턴 감지
- SQL 인젝션, XSS 공격 차단
- 디렉토리 순회 공격 방지
- 비정상적인 요청 패턴 감지

## 📊 API 엔드포인트

### 핵심 API
- `POST /api/detect` - 곤충 탐지
- `POST /api/classify` - 목 분류
- `GET /api/health` - 헬스 체크

### 인증 API
- `POST /login` - 로그인
- `GET /logout` - 로그아웃

## 🎯 성능 최적화

### 탐지 모델 (속도 우선)
- ❌ TTA 제거
- ⚡ 단일 추론으로 빠른 처리
- 🎯 신뢰도 임계값: 70%

### 분류 모델 (정확도 우선)
- ✅ TTA 적용 (4가지 변환)
- 🔄 원본, 수평뒤집기, 회전, 스케일
- 📊 예측 결과 평균으로 정확도 향상

## 🔄 원본 버전과의 차이점

### 제거된 기능
- 라벨링 시스템
- 관리자 페이지
- 데이터베이스 관리
- 배치 처리 기능
- 중복 파일 관리
- 통계 및 분석 기능

### 유지된 핵심 기능
- 곤충 탐지 및 분류
- 사용자 인증
- 보안 시스템
- 파일 업로드/다운로드

## 🚀 배포

### 로컬 개발
```bash
python src/main.py
```

### 프로덕션 (Gunicorn)
```bash
gunicorn -w 4 -b 0.0.0.0:8000 src.main:app
```

## 📝 라이선스

이 프로젝트는 연구 및 교육 목적으로 제작되었습니다.

## 🤝 기여

버그 리포트나 기능 제안은 이슈로 등록해 주세요.

---

**Made with ❤️ for Insect Research**