# NEST 프로젝트 빠른 시작 가이드

## 🚀 5분 안에 시작하기

### 1. 새 템플릿 적용

```bash
cd /home/ubuntu/NEST_Project_Complete
mv templates/index.html templates/index.html.old
cp templates/index_enhanced.html templates/index.html
```

### 2. 서버 실행

```bash
python3 app.py
```

서버가 `http://localhost:8080`에서 실행됩니다.

### 3. 테스트

브라우저에서 `http://localhost:8080` 접속 후:
1. 곤충 이미지 업로드
2. 바운딩 박스 조정 (선택)
3. "확인 및 분류 진행" 클릭
4. 결과 확인:
   - 분류 결과
   - 위험도 평가 ⭐ (신규)
   - 상세 정보 ⭐ (신규)

---

## 📋 주요 변경 사항

### 신규 파일
- `utils/risk_assessor.py` - 위험도 평가 모듈
- `utils/info_provider.py` - 정보 제공 모듈
- `templates/index_enhanced.html` - 새 UI

### 수정 파일
- `app.py` - 위험도 평가 및 정보 제공 통합

---

## 🎯 IR 피칭 데모 시나리오

### 시나리오 1: "외형과 위험의 역설"

**준비물**: 장수하늘소 이미지 (10cm), 화상벌레 이미지 (1cm)

**데모 순서**:
1. 장수하늘소 업로드 → 위험도: 안전 (1/5)
   - "크다고 위험한 것이 아님"
2. 화상벌레 업로드 → 위험도: 위험 (3.5/5)
   - "작아도 위험할 수 있음"
3. **결론**: AI 기반 과학적 판단 필요성

### 시나리오 2: "생명을 구하는 AI"

**준비물**: 장수말벌 이미지, 등검은말벌 이미지

**데모 순서**:
1. 장수말벌 업로드 → 위험도: 매우 위험 (5/5)
   - 연평균 10명 이상 사망
2. 등검은말벌 업로드 → 위험도: 매우 위험 (4.6/5)
   - 외래종, 생태계 교란
3. **결론**: 시민 안전 보호, 생태계 보전

---

## 🐛 문제 해결

### AI 모델이 없어요
- 현재 `utils/models/` 디렉토리가 비어있습니다.
- 탐지와 분류는 작동하지 않지만, 위험도 평가와 정보 제공은 독립적으로 테스트 가능합니다.
- 모델 가중치 파일을 추가하면 전체 워크플로우가 작동합니다.

### 템플릿이 적용되지 않아요
- `app.py`의 `render_template()` 함수에서 템플릿 이름을 확인하세요.
- 또는 `index.html`을 `index_enhanced.html`로 교체하세요.

### 분류 결과가 없어요
- AI 모델이 없으면 분류가 작동하지 않습니다.
- 위험도 평가와 정보 제공은 분류 결과가 있을 때만 표시됩니다.

---

## 📚 더 알아보기

- **전체 보고서**: `/home/ubuntu/NEST_Project_Final_Report.md`
- **종 선정 전략**: `/home/ubuntu/species_selection_strategy.md`
- **프로젝트 분석**: `/home/ubuntu/NEST_project_analysis.md`

---

**문의**: NEST Lab  
**작성일**: 2025-11-23
