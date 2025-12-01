import os
import uuid
from flask import Flask, request, render_template, redirect, url_for, send_from_directory, flash, session, jsonify
from werkzeug.utils import secure_filename
from PIL import Image
from pathlib import Path
from datetime import datetime, date
import sys

# utils 모듈 경로 추가
BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

from utils.detector import InsectDetector
from utils.classifier import InsectClassifier
from utils.hierarchical_classifier import HierarchicalClassifier
from utils.risk_assessor import get_risk_assessor
from utils.info_provider import get_info_provider
from utils.map_location_extract import extract_locations_from_folder
from utils.classification_storage import get_classification_storage
from utils.social_storage import get_social_storage
from utils.weather_provider import get_weather_info, get_weather_icon

app = Flask(__name__)
app.secret_key = "super-secret-key"  # flash 메시지용. 나중엔 env로 빼는 게 좋음

# 업로드 폴더 설정
BASE_DIR = Path(__file__).parent
UPLOAD_FOLDER = BASE_DIR / "uploads"
RESULTS_FOLDER = BASE_DIR / "results"
UPLOAD_FOLDER.mkdir(exist_ok=True)
RESULTS_FOLDER.mkdir(exist_ok=True)

app.config["UPLOAD_FOLDER"] = str(UPLOAD_FOLDER)
app.config["RESULTS_FOLDER"] = str(RESULTS_FOLDER)
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16MB 제한

# 곤충 탐지기 초기화
DETECTOR_MODEL_PATH = BASE_DIR / "utils" / "models" / "best_detector.pt"
CLASSIFIER_MODEL_PATH = BASE_DIR / "utils" / "models" / "best_classifier.pth"
CROPS_FOLDER = BASE_DIR / "crops"
CROPS_FOLDER.mkdir(exist_ok=True)

detector = None
classifier = None
hierarchical_classifier = None
risk_assessor = None
info_provider = None

def get_detector():
    """곤충 탐지기 싱글톤 인스턴스 반환"""
    global detector
    if detector is None:
        model_path = DETECTOR_MODEL_PATH if DETECTOR_MODEL_PATH.exists() else None
        detector = InsectDetector(model_path=model_path)
    return detector

def get_classifier():
    """곤충 분류기 싱글톤 인스턴스 반환"""
    global classifier
    if classifier is None:
        model_path = CLASSIFIER_MODEL_PATH if CLASSIFIER_MODEL_PATH.exists() else None
        classifier = InsectClassifier(model_path=model_path)
    return classifier

def get_hierarchical_classifier():
    """계층적 분류기 싱글톤 인스턴스 반환"""
    global hierarchical_classifier
    if hierarchical_classifier is None:
        models_dir = BASE_DIR / "utils" / "models"
        hierarchical_classifier = HierarchicalClassifier(models_dir=models_dir)
    return hierarchical_classifier

def get_risk_assessor_instance():
    """위험도 평가기 싱글톤 인스턴스 반환"""
    global risk_assessor
    if risk_assessor is None:
        risk_assessor = get_risk_assessor()
    return risk_assessor

def get_info_provider_instance():
    """정보 제공자 싱글톤 인스턴스 반환"""
    global info_provider
    if info_provider is None:
        info_provider = get_info_provider()
    return info_provider

# 허용 확장자
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}

def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def detect_image_ext(path: str) -> str | None:
    """Detect real image extension from file bytes without re-encoding."""
    try:
        with Image.open(path) as img:
            fmt = (img.format or "").lower()
        # Pillow uses 'jpeg' for jpg
        if fmt == "jpeg":
            return "jpg"
        return fmt if fmt in ALLOWED_EXTENSIONS else None
    except Exception:
        return None

def ensure_unique_filename(original_filename: str) -> str:
    """Generate a safe unique filename while preserving extension."""
    safe = secure_filename(original_filename)
    name, ext = os.path.splitext(safe)
    ext = ext.lower()
    if not name:  # secure_filename can blank out non-ascii names
        name = str(uuid.uuid4())
    if not ext:
        ext = ".jpg"
    return f"{name}_{uuid.uuid4().hex[:8]}{ext}"

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        # 중복 요청 방지
        request_id = request.form.get('request_id')
        if request_id and session.get('last_request_id') == request_id:
            return redirect(url_for("index", show_result="true"))
        session['last_request_id'] = request_id
        if "photo" not in request.files:
            flash("파일이 전송되지 않았어요.")
            return redirect(request.url)

        file = request.files["photo"]

        if file.filename == "":
            flash("파일을 선택해 주세요.")
            return redirect(request.url)

        if not allowed_file(file.filename):
            flash("허용되지 않는 파일 형식입니다.")
            return redirect(request.url)

        # 안전 + 유니크 파일명 생성 (원본 바이트는 그대로 저장)
        filename = ensure_unique_filename(file.filename)
        save_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)

        file.save(save_path)  # 여기서 실제 바이트 그대로 저장

        # 저장된 파일이 진짜 이미지인지, 그리고 확장자가 맞는지 검증
        real_ext = detect_image_ext(save_path)
        if real_ext is None:
            # 이미지가 아니거나 손상되었으면 삭제
            try:
                os.remove(save_path)
            except OSError:
                pass
            flash("이미지 파일이 아니거나 손상된 파일입니다.")
            return redirect(request.url)

        # 실제 포맷과 확장자가 다르면 이름만 교정 (재인코딩 X)
        current_ext = os.path.splitext(filename)[1].lstrip(".").lower()
        if current_ext != real_ext:
            new_filename = os.path.splitext(filename)[0] + f".{real_ext}"
            new_path = os.path.join(app.config["UPLOAD_FOLDER"], new_filename)
            os.replace(save_path, new_path)
            filename = new_filename
            save_path = new_path

        # 곤충 탐지 수행
        try:
            detector = get_detector()
            result_filename = f"detected_{filename}"
            result_path = os.path.join(app.config["RESULTS_FOLDER"], result_filename)
            
            detection_result = detector.detect(save_path, save_path=result_path)
            print(f"탐지: {detection_result['count']}개")
            
            # 탐지 결과만 저장 (분류는 사용자가 확인 버튼을 눌렀을 때 수행)
            session['last_detection'] = {
                'original_image': filename,
                'detected_image': result_filename,
                'count': detection_result['count'],
                'detections': detection_result['detections'],
                'classifications': None,  # 분류는 나중에 수행
                'risk_assessment': None,  # 위험도 평가는 나중에 수행
                'species_info': None  # 정보 제공은 나중에 수행
            }
            
            if detection_result['count'] > 0:
                flash(f"업로드 완료! {detection_result['count']}개의 곤충이 탐지되었습니다. 바운딩 박스를 조정한 후 확인 버튼을 눌러주세요.")
            else:
                flash("업로드 완료! 곤충이 탐지되지 않았습니다.")
                
        except Exception as e:
            print(f"탐지 중 오류 발생: {str(e)}")
            import traceback
            traceback.print_exc()
            flash("업로드 완료! (탐지 중 오류가 발생했습니다.)")
            session['last_detection'] = None

        return redirect(url_for("index", show_result="true"))

    # 업로드된 파일 목록
    files = sorted(os.listdir(app.config["UPLOAD_FOLDER"]))
    
    # 탐지 결과 표시 여부 결정
    detection = None
    if request.method == "GET":
        # show_result 쿼리 파라미터가 있으면 결과 표시 (POST 후 리다이렉트)
        if request.args.get('show_result') == 'true':
            detection = session.get('last_detection', None)
        else:
            # 직접 접근 또는 새로고침 시 세션 초기화
            session.pop('last_detection', None)
    
    return render_template("index.html", files=files, detection=detection)

# 업로드 파일 서빙
@app.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

# 탐지 결과 이미지 서빙
@app.route("/results/<filename>")
def result_file(filename):
    return send_from_directory(app.config["RESULTS_FOLDER"], filename)

# 세션 초기화 라우트
@app.route("/reset", methods=["GET", "POST"])
def reset_session():
    """세션 초기화"""
    session.pop('last_detection', None)
    return redirect(url_for("index"))

# 바운딩 박스 업데이트 라우트
@app.route("/update_bboxes", methods=["POST"])
def update_bboxes():
    """바운딩 박스 업데이트"""
    try:
        data = request.get_json()
        bboxes = data.get('bboxes', [])
        
        # 세션의 탐지 결과 업데이트
        if 'last_detection' in session:
            session['last_detection']['detections'] = bboxes
            session['last_detection']['count'] = len(bboxes)
            session.modified = True
        
        return jsonify({'success': True, 'count': len(bboxes)})
    except Exception as e:
        print(f"바운딩 박스 업데이트 오류: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 400

# 분류 수행 라우트
@app.route("/classify", methods=["POST"])
def classify():
    """조정된 바운딩 박스로 분류 및 위험도 평가 수행"""
    try:
        # JSON 파싱 시도, 실패하면 빈 딕셔너리 사용
        try:
            data = request.get_json() or {}
        except:
            data = {}
        bboxes = data.get('bboxes', [])
        selected_index = data.get('selected_index', 0)
        
        # 세션에서 바운딩 박스 가져오기 (JSON에 없으면)
        if not bboxes and 'last_detection' in session:
            detection = session['last_detection']
            if detection.get('detections'):
                bboxes = detection['detections']
        
        if 'last_detection' not in session:
            return jsonify({'success': False, 'error': '탐지 결과가 없습니다.'}), 400
        
        detection = session['last_detection']
        original_image = detection['original_image']
        save_path = os.path.join(app.config["UPLOAD_FOLDER"], original_image)
        
        if not os.path.exists(save_path):
            return jsonify({'success': False, 'error': '원본 이미지를 찾을 수 없습니다.'}), 400
        
        # 바운딩 박스 업데이트
        detection['detections'] = bboxes
        detection['count'] = len(bboxes)
        
        # 분류 수행 (2단계: 목 분류 -> 계층적 분류)
        classification_results = None
        risk_assessment = None
        species_info = None
        
        # 선택된 바운딩 박스만 분류
        if len(bboxes) > 0 and selected_index < len(bboxes):
            try:
                # 선택된 바운딩 박스만 추출
                selected_bbox = [bboxes[selected_index]]
                
                # 1단계: 목 분류
                classifier = get_classifier()
                order_results = classifier.classify_detections(
                    save_path,
                    selected_bbox,
                    crop_dir=str(CROPS_FOLDER)
                )
                
                # 목 분류 결과 로그 출력
                for i, result in enumerate(order_results):
                    print(f"\n=== 곤충 #{i+1} 목 분류 결과 ===")
                    if result.get('classification'):
                        print("상위 3개 목 후보:")
                        for j, cls in enumerate(result['classification'][:3]):
                            print(f"  {j+1}. {cls['class_name']}: {cls['confidence']*100:.1f}%")
                
                # 2단계: 계층적 분류 (목 -> 과 -> 속 -> 종)
                try:
                    hierarchical_classifier = get_hierarchical_classifier()
                    classification_results = hierarchical_classifier.classify_detections(
                        save_path,
                        selected_bbox,
                        order_results,
                        crop_dir=str(CROPS_FOLDER)
                    )
                except Exception as hier_error:
                    print(f"계층적 분류 오류: {hier_error}")
                    print("기본 목 분류 결과만 사용")
                    classification_results = order_results
                
                # 3단계: 위험도 평가
                try:
                    assessor = get_risk_assessor_instance()
                    risk_assessment = []
                    
                    print(f"분류 결과 개수: {len(classification_results)}")
                    
                    for i, result in enumerate(classification_results):
                        print(f"\n=== 곤충 #{i+1} 분류 결과 ===")
                        print(f"결과 구조: {type(result)}")
                        
                        # 분류 결과에서 종명 추출
                        species_name = None
                        
                        # 계층적 분류 결과 구조 파싱
                        if isinstance(result, dict):
                            print(f"결과 키들: {list(result.keys())}")
                            
                            # hierarchical_result에서 추출
                            if 'hierarchical_result' in result:
                                hier_result = result['hierarchical_result']
                                print(f"계층적 결과: {hier_result}")
                                if hier_result.get('species'):
                                    species_name = hier_result['species']
                                    print(f"종 발견: {species_name}")
                                elif hier_result.get('genus'):
                                    species_name = hier_result['genus']
                                    print(f"속 발견: {species_name}")
                                elif hier_result.get('family'):
                                    species_name = hier_result['family']
                                    print(f"과 발견: {species_name}")
                                elif hier_result.get('order'):
                                    species_name = hier_result['order']
                                    print(f"목 발견: {species_name}")
                            
                            # classification 리스트에서 추출
                            elif 'classification' in result and result['classification']:
                                print(f"분류 리스트: {result['classification']}")
                                # 종 레벨부터 역순으로 검색
                                for cls in reversed(result['classification']):
                                    if cls.get('level') == 'species' and cls.get('class_name'):
                                        species_name = cls['class_name']
                                        print(f"종 발견 (분류): {species_name}")
                                        break
                                    elif cls.get('level') == 'genus' and cls.get('class_name'):
                                        species_name = cls['class_name']
                                        print(f"속 발견 (분류): {species_name}")
                                        break
                                    elif cls.get('level') == 'family' and cls.get('class_name'):
                                        species_name = cls['class_name']
                                        print(f"과 발견 (분류): {species_name}")
                                        break
                                    elif cls.get('level') == 'order' and cls.get('class_name'):
                                        species_name = cls['class_name']
                                        print(f"목 발견 (분류): {species_name}")
                                        break
                        
                        print(f"최종 추출된 종명: {species_name}")
                        
                        # 위험도 평가 수행
                        if species_name:
                            # 후보 표시 제거 (예: "Vespa mandarinia (후보 #2)" -> "Vespa mandarinia")
                            clean_name = species_name.split(' (후보')[0].strip()
                            print(f"정리된 종명: {clean_name}")
                            
                            risk_result = assessor.assess_risk(clean_name)
                            print(f"위험도 평가 결과: {risk_result is not None}")
                            
                            if risk_result:
                                risk_assessment.append(risk_result)
                            else:
                                # 기본 위험도 (분류되었지만 위험도 DB에 없는 경우)
                                risk_assessment.append({
                                    "species_name": clean_name,
                                    "threat_level": "미분류",
                                    "risk_level_color": "#9E9E9E",
                                    "description": "이 종에 대한 위험도 정보가 아직 등록되지 않았습니다.",
                                    "warnings": ["⚠️ 알 수 없는 종: 접촉을 피하고 전문가에게 문의하세요"],
                                    "response_guide": {
                                        "prevention": ["접촉 피하기", "사진 촬영 후 전문가 문의"],
                                        "observation": ["안전 거리 유지", "행동 관찰"]
                                    }
                                })
                        else:
                            print("종명을 추출할 수 없음")
                            risk_assessment.append(None)
                
                except Exception as risk_error:
                    print(f"위험도 평가 오류: {risk_error}")
                    import traceback
                    traceback.print_exc()
                    risk_assessment = None
                
                # 4단계: 상세 정보 제공
                try:
                    provider = get_info_provider_instance()
                    species_info = []
                    
                    for i, result in enumerate(classification_results):
                        # 분류 결과에서 종명 추출 (위험도 평가와 동일한 로직)
                        species_name = None
                        
                        if isinstance(result, dict):
                            print(f"[INFO] 분류 결과 #{i+1} 키: {list(result.keys())}")
                            
                            # hierarchical_result에서 추출
                            if 'hierarchical_result' in result:
                                hier_result = result['hierarchical_result']
                                print(f"[INFO] hierarchical_result: {hier_result}")
                                if hier_result.get('species'):
                                    species_name = hier_result['species']
                                    print(f"[INFO] hierarchical_result에서 종 추출: {species_name}")
                                elif hier_result.get('genus'):
                                    species_name = hier_result['genus']
                                    print(f"[INFO] hierarchical_result에서 속 추출: {species_name}")
                                elif hier_result.get('family'):
                                    species_name = hier_result['family']
                                    print(f"[INFO] hierarchical_result에서 과 추출: {species_name}")
                                elif hier_result.get('order'):
                                    species_name = hier_result['order']
                                    print(f"[INFO] hierarchical_result에서 목 추출: {species_name}")
                            
                            # classification 리스트에서 추출 (hierarchical_result에 없을 경우)
                            if not species_name and 'classification' in result and result['classification']:
                                print(f"[INFO] classification 리스트에서 추출 시도: {len(result['classification'])}개 항목")
                                for cls in reversed(result['classification']):
                                    print(f"[INFO]   - level: {cls.get('level')}, class_name: {cls.get('class_name')}")
                                    if cls.get('level') == 'species' and cls.get('class_name'):
                                        species_name = cls['class_name']
                                        print(f"[INFO] classification에서 종 추출: {species_name}")
                                        break
                                    elif cls.get('level') == 'genus' and cls.get('class_name'):
                                        species_name = cls['class_name']
                                        print(f"[INFO] classification에서 속 추출: {species_name}")
                                        break
                                    elif cls.get('level') == 'family' and cls.get('class_name'):
                                        species_name = cls['class_name']
                                        print(f"[INFO] classification에서 과 추출: {species_name}")
                                        break
                                    elif cls.get('level') == 'order' and cls.get('class_name'):
                                        species_name = cls['class_name']
                                        print(f"[INFO] classification에서 목 추출: {species_name}")
                                        break
                        
                        # 정보 제공
                        if species_name:
                            # 후보 표시 제거
                            clean_name = species_name.split(' (후보')[0].strip()
                            # 언더스코어를 공백으로 변환 (Vespa_mandarinia -> Vespa mandarinia)
                            clean_name = clean_name.replace('_', ' ')
                            print(f"[INFO] 정보 조회 종명: '{clean_name}' (원본: '{species_name}')")
                            
                            info_result = provider.get_info(clean_name)
                            print(f"[INFO] 정보 조회 결과: {info_result is not None}")
                            if info_result:
                                print(f"[INFO] 정보 조회 성공: {info_result.get('species_name', 'N/A')}")
                                species_info.append(info_result)
                            else:
                                print(f"[INFO] 정보 조회 실패: '{clean_name}'에 대한 정보 없음")
                                species_info.append({
                                    "species_name": clean_name,
                                    "description": "이 종에 대한 상세 정보가 아직 등록되지 않았습니다.",
                                    "note": "전문가에게 문의하거나 추가 조사가 필요합니다."
                                })
                        else:
                            print(f"[INFO] 종명을 추출할 수 없음 (result: {result})")
                            species_info.append(None)
                
                except Exception as info_error:
                    print(f"정보 제공 오류: {info_error}")
                    import traceback
                    traceback.print_exc()
                    species_info = None
                
            except Exception as e:
                print(f"분류 중 오류 발생: {str(e)}")
                import traceback
                traceback.print_exc()
                classification_results = None
                risk_assessment = None
                species_info = None
        
        # 세션 업데이트 - 선택된 인덱스에만 저장
        total_detections = len(detection['detections'])
        if not detection.get('classifications'):
            detection['classifications'] = [None] * total_detections
        if not detection.get('risk_assessment'):
            detection['risk_assessment'] = [None] * total_detections
        if not detection.get('detailed_info'):
            detection['detailed_info'] = [None] * total_detections
        
        # 인덱스 범위 확인
        if selected_index >= total_detections:
            print(f"경고: selected_index({selected_index})가 범위를 벗어남. 0으로 설정")
            selected_index = 0
        
        if classification_results and len(classification_results) > 0:
            detection['classifications'][selected_index] = classification_results[0]
        if risk_assessment and len(risk_assessment) > 0:
            detection['risk_assessment'][selected_index] = risk_assessment[0]
        if species_info and len(species_info) > 0:
            detection['detailed_info'][selected_index] = species_info[0]
        
        # 분류 정보를 파일로 저장
        if classification_results and len(classification_results) > 0:
            try:
                storage = get_classification_storage()
                result = classification_results[0]
                
                # 계층적 분류 결과에서 정보 추출
                if 'hierarchical_result' in result:
                    hier_result = result['hierarchical_result']
                    
                    classification_data = {
                        'order': hier_result.get('order', ''),
                        'family': hier_result.get('family', ''),
                        'genus': hier_result.get('genus', ''),
                        'species': hier_result.get('species', ''),
                        'confidence_scores': hier_result.get('confidence_scores', {}),
                        'species_candidates': hier_result.get('species_candidates', [])
                    }
                    
                    # 국명 추출 (여러 소스에서 시도)
                    korean_name = None
                    
                    # 1. species_info에서 가져오기 (우선순위 1)
                    if species_info and len(species_info) > 0 and species_info[0]:
                        korean_name = species_info[0].get('korean_name') or species_info[0].get('species_name', '')
                        
                        # 위험도 분류 정보 저장 (species_info의 risk_assessment)
                        if species_info[0].get('risk_assessment'):
                            species_risk_assessment = species_info[0]['risk_assessment']
                            classification_data['threat_level'] = species_risk_assessment.get('threat_level', '')
                            classification_data['risk_category'] = species_risk_assessment.get('risk_category', '')
                            # species_info의 risk_assessment도 저장 (전체 객체)
                            classification_data['risk_assessment_from_species_info'] = species_risk_assessment
                    
                    # 2. species_info에 없으면 info_provider에서 직접 조회
                    if not korean_name and classification_data.get('species'):
                        try:
                            provider = get_info_provider_instance()
                            # species에서 언더스코어를 공백으로 변환
                            clean_species = classification_data['species'].replace('_', ' ')
                            info_result = provider.get_info(clean_species)
                            if info_result:
                                korean_name = info_result.get('korean_name') or info_result.get('species_name', '')
                                # 위험도 정보도 함께 저장
                                if info_result.get('risk_assessment'):
                                    species_risk_assessment = info_result['risk_assessment']
                                    classification_data['threat_level'] = species_risk_assessment.get('threat_level', '')
                                    classification_data['risk_category'] = species_risk_assessment.get('risk_category', '')
                                    # species_info의 risk_assessment도 저장 (전체 객체)
                                    classification_data['risk_assessment_from_species_info'] = species_risk_assessment
                        except Exception as info_error:
                            print(f"정보 조회 오류 (저장 시): {info_error}")
                    
                    # 3. 그래도 없으면 과나 속 이름 사용
                    if not korean_name:
                        if classification_data.get('family'):
                            korean_name = classification_data['family']
                        elif classification_data.get('genus'):
                            korean_name = classification_data['genus']
                        elif classification_data.get('order'):
                            korean_name = classification_data['order']
                    
                    # korean_name 저장
                    if korean_name:
                        classification_data['korean_name'] = korean_name
                    
                    # 위험도 평가 결과 전체 저장 (risk_assessment에서)
                    if risk_assessment and len(risk_assessment) > 0 and risk_assessment[0]:
                        risk_data = risk_assessment[0]
                        # risk_assessment 전체 객체 저장
                        classification_data['risk_assessment'] = risk_data
                        
                        # 하위 호환성을 위해 개별 필드도 저장
                        if not classification_data.get('threat_level'):
                            threat_level = risk_data.get('threat_level', '')
                            if threat_level == 'unknown' or threat_level == '정보 없음':
                                threat_level = '미분류'
                            classification_data['threat_level'] = threat_level
                            classification_data['risk_level_color'] = risk_data.get('risk_level_color', '')
                    
                    # 파일명에 개체 인덱스 추가 (filename_insect0, filename_insect1, ...)
                    base_name, ext = os.path.splitext(original_image)
                    indexed_filename = f"{base_name}_insect{selected_index}{ext}"
                    # filename 필드는 원본 파일명 유지
                    classification_data['filename'] = original_image
                    storage.save_classification(indexed_filename, classification_data)
                    print(f"✓ 분류 정보 저장 완료: {indexed_filename} -> korean_name: {korean_name}, species: {classification_data.get('species', 'N/A')}, risk_assessment: {bool(classification_data.get('risk_assessment'))}")
            except Exception as save_error:
                print(f"분류 정보 저장 오류: {save_error}")
        
        session['last_detection'] = detection
        session.modified = True
        
        # JSON 응답으로 리다이렉트 URL 반환 (fetch에서 처리하기 위해)
        return jsonify({
            'success': True,
            'redirect': url_for("index", show_result="true")
        })
        
    except Exception as e:
        print(f"분류 오류: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route("/select_candidate", methods=["POST"])
def select_candidate():
    try:
        data = request.get_json()
        insect_index = data.get('insect_index')
        species_name = data.get('species_name')
        
        print(f"\n=== 후보 선택: 곤충 #{insect_index}, 종: {species_name} ===")
        
        if 'last_detection' not in session:
            return jsonify({'success': False}), 400
        
        detection = session['last_detection']
        
        # 분류 결과 업데이트
        if detection.get('classifications') and insect_index < len(detection['classifications']):
            result = detection['classifications'][insect_index]
            if result and 'hierarchical_result' in result:
                result['hierarchical_result']['species'] = species_name
                result['hierarchical_result']['selected_species'] = species_name
                print(f"분류 결과 업데이트 완료: {species_name}")
        
        # 위험도 평가 업데이트
        assessor = get_risk_assessor_instance()
        risk_result = assessor.assess_risk(species_name) or {
            "species_name": species_name,
            "threat_level": "미분류",
            "risk_level_color": "#9E9E9E",
            "description": "이 종에 대한 위험도 정보가 아직 등록되지 않았습니다."
        }
        
        if not detection.get('risk_assessment'):
            detection['risk_assessment'] = []
        while len(detection['risk_assessment']) <= insect_index:
            detection['risk_assessment'].append(None)
        detection['risk_assessment'][insect_index] = risk_result
        
        # 상세 정보 업데이트
        provider = get_info_provider_instance()
        # 언더스코어를 공백으로 변환
        clean_species_name = species_name.replace('_', ' ')
        print(f"정보 조회 종명: {clean_species_name}")
        
        info_result = provider.get_info(clean_species_name)
        print(f"정보 조회 결과: {info_result is not None}")
        
        if not info_result:
            info_result = {
                "species_name": clean_species_name,
                "description": "이 종에 대한 상세 정보가 아직 등록되지 않았습니다."
            }
        
        if not detection.get('detailed_info'):
            detection['detailed_info'] = []
        while len(detection['detailed_info']) <= insect_index:
            detection['detailed_info'].append(None)
        detection['detailed_info'][insect_index] = info_result
        
        print(f"업데이트된 detailed_info[{insect_index}]: {info_result.get('species_name')}")
        
        # 후보종 선택 정보를 파일로 업데이트
        try:
            storage = get_classification_storage()
            original_image = detection.get('original_image')
            
            if original_image:
                # 기존 데이터 로드
                existing_data = storage.get_classification(original_image) or {}
                
                # 선택된 종 정보로 업데이트
                existing_data['species'] = clean_species_name
                
                # korean_name 확보 (여러 소스에서 시도)
                korean_name = info_result.get('korean_name') or info_result.get('species_name', clean_species_name)
                
                # info_result에 없으면 info_provider에서 직접 조회
                if not korean_name or korean_name == clean_species_name:
                    try:
                        provider = get_info_provider_instance()
                        info_from_provider = provider.get_info(clean_species_name)
                        if info_from_provider:
                            korean_name = info_from_provider.get('korean_name') or info_from_provider.get('species_name', clean_species_name)
                    except Exception as provider_error:
                        print(f"정보 제공자 조회 오류: {provider_error}")
                
                existing_data['korean_name'] = korean_name
                
                # 위험도 분류 정보 저장
                if info_result.get('risk_assessment'):
                    risk_assessment = info_result['risk_assessment']
                    existing_data['threat_level'] = risk_assessment.get('threat_level', '')
                    existing_data['risk_category'] = risk_assessment.get('risk_category', '')
                
                # 위험도 평가 결과 전체 저장
                if risk_result:
                    # risk_assessment 전체 객체 저장
                    existing_data['risk_assessment'] = risk_result
                    
                    # threat_level로 통일
                    threat_level = risk_result.get('threat_level', '')
                    if not threat_level:
                        threat_level = risk_result.get('risk_level', '')
                    if threat_level == 'unknown' or threat_level == '정보 없음':
                        threat_level = '미분류'
                    existing_data['threat_level'] = threat_level
                    existing_data['risk_level_color'] = risk_result.get('risk_level_color', '')
                
                # 파일명에 개체 인덱스 추가
                base_name, ext = os.path.splitext(original_image)
                indexed_filename = f"{base_name}_insect{insect_index}{ext}"
                # filename 필드는 원본 파일명 유지
                existing_data['filename'] = original_image
                storage.save_classification(indexed_filename, existing_data)
                print(f"✓ 후보종 선택 정보 저장 완료: {indexed_filename} -> korean_name: {korean_name}, species: {clean_species_name}, risk_assessment: {bool(existing_data.get('risk_assessment'))}")
        except Exception as update_error:
            print(f"후보종 선택 정보 업데이트 오류: {update_error}")
        
        session['last_detection'] = detection
        session.modified = True
        
        return jsonify({
            'success': True,
            'risk': risk_result,
            'info': info_result
        })
        
    except Exception as e:
        print(f"후보 선택 오류: {str(e)}")
        return jsonify({'success': False}), 500

# 수동 바운딩 박스 추가 라우트
@app.route("/add_manual_bbox", methods=["POST"])
def add_manual_bbox():
    """수동으로 그린 바운딩 박스 추가"""
    try:
        data = request.get_json()
        bbox = data.get('bbox')
        
        if 'last_detection' not in session:
            return jsonify({'success': False, 'error': '탐지 결과가 없습니다.'}), 400
        
        detection = session['last_detection']
        
        # 새 바운딩 박스 추가
        new_detection = {
            'bbox': bbox,
            'confidence': 1.0,
            'class': 'manual'
        }
        
        if detection['detections'] is None:
            detection['detections'] = []
        
        detection['detections'].append(new_detection)
        detection['count'] = len(detection['detections'])
        
        session['last_detection'] = detection
        session.modified = True
        
        return jsonify({'success': True})
        
    except Exception as e:
        print(f"수동 바운딩 박스 추가 오류: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

# 맵 페이지 라우트
@app.route("/board")
def board_page():
    """게시판 페이지"""
    # 오늘 날짜
    today = date.today()
    
    # 업로드 폴더에서 오늘 업로드된 이미지 찾기
    upload_path = Path(app.config["UPLOAD_FOLDER"])
    image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.tiff'}
    
    today_observations = []
    
    # 분류 정보 로드
    storage = get_classification_storage()
    classifications = storage.get_all_classifications()
    
    # 위치 정보 추출
    locations = extract_locations_from_folder(app.config["UPLOAD_FOLDER"])
    # location_map 생성 및 location 문자열 추가
    location_map = {}
    for loc in locations:
        filename = loc['filename']
        # 위치 문자열 생성
        if loc.get('lat') is not None and loc.get('lon') is not None:
            lat = loc['lat']
            lon = loc['lon']
            location_str = f"위도: {lat:.6f}, 경도: {lon:.6f}"
        else:
            location_str = '위치 정보 없음'
        location_map[filename] = {
            **loc,
            'location': location_str
        }
    
    # 오늘 업로드된 파일 찾기
    for file_path in upload_path.iterdir():
        if file_path.is_file() and file_path.suffix.lower() in image_extensions:
            # 파일 수정 시간 확인
            file_mtime = datetime.fromtimestamp(file_path.stat().st_mtime).date()
            
            if file_mtime == today:
                filename = file_path.name
                
                # 분류 정보 가져오기 (filename 또는 filename_insect{N} 형식)
                classification = classifications.get(filename, {})
                if not classification:
                    # filename_insect0, filename_insect1, ... 형식으로 시도 (첫 번째 것만)
                    base_name, ext = os.path.splitext(filename)
                    for i in range(10):  # 최대 10개 개체까지 확인
                        indexed_filename = f"{base_name}_insect{i}{ext}"
                        if indexed_filename in classifications:
                            classification = classifications[indexed_filename]
                            break
                species = classification.get('species', '')
                korean_name = classification.get('korean_name', '')
                
                # korean_name이 없으면 info_provider에서 조회 시도
                if not korean_name and species:
                    try:
                        provider = get_info_provider_instance()
                        # species에서 언더스코어를 공백으로 변환
                        clean_species = species.replace('_', ' ')
                        info_result = provider.get_info(clean_species)
                        if info_result:
                            korean_name = info_result.get('korean_name') or info_result.get('species_name', '')
                            # 조회한 정보를 classification에 추가 (다음에 빠르게 사용)
                            if korean_name:
                                classification['korean_name'] = korean_name
                                # 저장은 하지 않고 메모리에서만 사용 (선택적)
                    except Exception as info_error:
                        print(f"정보 조회 오류 (게시판 표시 시): {info_error}")
                
                # 표시할 이름 결정
                display_name = korean_name if korean_name else (species if species else '미분류')
                
                # 디버깅 로그
                if not korean_name and species:
                    print(f"⚠ 게시판: {filename} - korean_name 없음, species: {species}")
                
                # 위치 정보 가져오기
                location_info = location_map.get(filename, {})
                location = location_info.get('location', '위치 정보 없음')
                
                # 날씨 정보 가져오기
                weather_info = None
                if location_info.get('lat') and location_info.get('lon') and location_info.get('datetime_taken'):
                    weather_info = get_weather_info(
                        location_info['lat'],
                        location_info['lon'],
                        location_info['datetime_taken']
                    )
                    if weather_info:
                        weather_info['icon'] = get_weather_icon(weather_info.get('weather_code'))
                
                today_observations.append({
                    'filename': filename,
                    'species': display_name,
                    'location': location,
                    'classification': classification,
                    'weather': weather_info,
                    'lat': location_info.get('lat'),
                    'lon': location_info.get('lon'),
                    'datetime_taken': location_info.get('datetime_taken', '')
                })
    
    # 최신순으로 정렬 (파일 수정 시간 기준)
    today_observations.sort(key=lambda x: (upload_path / x['filename']).stat().st_mtime, reverse=True)
    
    # 좋아요/댓글 통계 가져오기
    social_storage = get_social_storage()
    
    # 오늘의 베스트 관찰 (좋아요/댓글 수 기준)
    best_observations = []
    for obs in today_observations:
        filename = obs['filename']
        likes_count = social_storage.get_likes(filename)
        comments = social_storage.get_comments(filename)
        comments_count = len(comments)
        
        # 좋아요나 댓글이 하나라도 있으면 베스트에 포함
        if likes_count > 0 or comments_count > 0:
            # today_observations에 이미 lat, lon, datetime_taken이 포함되어 있음
            weather_info = obs.get('weather')
            classification = obs.get('classification', {})
            
            best_observations.append({
                'filename': filename,
                'species': obs['species'],
                'location': obs['location'],
                'classification': classification,  # 분류 정보 추가
                'likes_count': likes_count,
                'comments_count': comments_count,
                'total_score': likes_count + comments_count * 2,  # 댓글에 가중치 부여
                'weather': weather_info,
                'lat': obs.get('lat'),
                'lon': obs.get('lon'),
                'datetime_taken': obs.get('datetime_taken', '')
            })
    
    # 총점 기준으로 정렬 (좋아요 + 댓글*2)
    best_observations.sort(key=lambda x: x['total_score'], reverse=True)
    
    # 상위 6개만 선택
    best_observations = best_observations[:6]
    
    # 내 주변 최신 관찰을 위한 데이터 준비 (오늘 날짜의 관찰 중 위치 정보가 있는 것만)
    all_observations_with_location = []
    for obs in today_observations:
        if obs.get('location') and obs['location'] != '위치 정보 없음':
            # 위치 정보에서 위도, 경도 추출
            location_info = location_map.get(obs['filename'], {})
            if location_info.get('lat') is not None and location_info.get('lon') is not None:
                all_observations_with_location.append({
                    'filename': obs['filename'],
                    'species': obs['species'],
                    'location': obs['location'],
                    'lat': location_info['lat'],
                    'lon': location_info['lon'],
                    'datetime_taken': location_info.get('datetime_taken', '')
                })
    
    return render_template("board.html", 
                         today_observations=today_observations,
                         best_observations=best_observations,
                         all_observations_with_location=all_observations_with_location)

@app.route("/map")
def map_page():
    """위치 지도 페이지"""
    # 업로드 폴더에서 위치 정보 추출
    locations = extract_locations_from_folder(app.config["UPLOAD_FOLDER"])
    
    # 분류 정보 로드
    storage = get_classification_storage()
    classifications = storage.get_all_classifications()
    risk_assessor = get_risk_assessor_instance()
    
    # 위험도 통계 계산
    risk_stats = {
        'critical': 0,
        'danger': 0,
        'caution': 0,
        'safe': 0,
        'unknown': 0,
        'unclassified': 0
    }
    
    # 위치 정보에 분류 정보 및 위험도 정보 추가
    for loc in locations:
        filename = loc['filename']
        
        # 날씨 정보 추가
        if loc.get('lat') and loc.get('lon') and loc.get('datetime_taken'):
            weather_info = get_weather_info(
                loc['lat'],
                loc['lon'],
                loc['datetime_taken']
            )
            if weather_info:
                weather_info['icon'] = get_weather_icon(weather_info.get('weather_code'))
                loc['weather'] = weather_info
        
        # 분류 정보 가져오기 (filename 또는 filename_insect{N} 형식)
        classification = classifications.get(filename)
        if not classification:
            base_name, ext = os.path.splitext(filename)
            for i in range(10):  # 최대 10개 개체까지 확인
                indexed_filename = f"{base_name}_insect{i}{ext}"
                if indexed_filename in classifications:
                    classification = classifications[indexed_filename]
                    break
        
        if classification:
            loc['classification'] = classification
            
            # threat_level로 위험도 분류 (우선순위 1)
            threat_level = classification.get('threat_level', '')
            
            # threat_level 값을 필터링 기준으로 변환
            filter_level = 'unclassified'  # 기본값
            
            if threat_level:
                if '인체 고위험' in threat_level or '공격성·독성' in threat_level:
                    filter_level = 'critical'
                elif '인체 중위험' in threat_level or '독성·피부염' in threat_level or '질병 매개' in threat_level:
                    filter_level = 'danger'
                elif '반려동물 위험' in threat_level:
                    filter_level = 'caution'
                elif '일반·불쾌' in threat_level or '불쾌 곤충' in threat_level or '일반·불쾌 곤충' in threat_level or '불쾌' in threat_level or '일반' in threat_level:
                    filter_level = 'safe'
                elif '보호' in threat_level or '천연기념물' in threat_level:
                    filter_level = 'unknown'
                else:
                    # threat_level이 있지만 매칭되지 않는 경우 미분류
                    filter_level = 'unclassified'
            
            # threat_level이 없으면 risk_assessment에서 가져오기 (하위 호환)
            if not threat_level:
                # risk_assessment 객체가 있으면 사용
                if classification.get('risk_assessment'):
                    risk_result = classification['risk_assessment']
                    loc['risk_assessment'] = risk_result
                    threat_level = risk_result.get('threat_level', '')
                    if not threat_level:
                        threat_level = risk_result.get('risk_level', '미분류')
                    if threat_level == 'unknown' or threat_level == '정보 없음':
                        threat_level = '미분류'
                    # risk_stats는 기존 키 유지 (하위 호환)
                    risk_level_key = 'unclassified' if threat_level == '미분류' else threat_level
                    if risk_level_key in risk_stats:
                        risk_stats[risk_level_key] += 1
                    else:
                        risk_stats['unclassified'] += 1
                else:
                    # 종명 또는 국명으로 위험도 평가
                    species = classification.get('species', '')
                    korean_name = classification.get('korean_name', '')
                    species_name = species if species else korean_name
                    
                    if species_name:
                        risk_result = risk_assessor.assess_risk(species_name)
                        if risk_result:
                            loc['risk_assessment'] = risk_result
                            threat_level = risk_result.get('threat_level', '')
                            if not threat_level:
                                threat_level = risk_result.get('risk_level', '미분류')
                            if threat_level == 'unknown' or threat_level == '정보 없음':
                                threat_level = '미분류'
                            # risk_stats는 기존 키 유지 (하위 호환)
                            risk_level_key = 'unclassified' if threat_level == '미분류' else threat_level
                            if risk_level_key in risk_stats:
                                risk_stats[risk_level_key] += 1
                            else:
                                risk_stats['unclassified'] += 1
                        else:
                            loc['risk_assessment'] = {
                                'threat_level': '미분류',
                                'risk_level_color': '#9E9E9E',
                                'description': '이 종에 대한 위험도 정보가 아직 등록되지 않았습니다.'
                            }
                            risk_stats['unclassified'] += 1
                    else:
                        # 분류 정보는 있지만 종명이 없는 경우 (미분류)
                        loc['risk_assessment'] = {
                            'threat_level': '미분류',
                            'risk_level_color': '#9E9E9E',
                            'description': '분류 정보가 없습니다.'
                        }
                        risk_stats['unclassified'] += 1
            else:
                # threat_level이 있으면 필터링 기준으로 사용
                loc['risk_assessment'] = {
                    'threat_level': threat_level,
                    'risk_category': classification.get('risk_category', ''),
                    'risk_level_color': '#9E9E9E'  # 기본 색상
                }
                # 위험도별 색상 설정
                if filter_level == 'critical':
                    loc['risk_assessment']['risk_level_color'] = '#F44336'
                elif filter_level == 'danger':
                    loc['risk_assessment']['risk_level_color'] = '#FF9800'
                elif filter_level == 'caution':
                    loc['risk_assessment']['risk_level_color'] = '#FFC107'
                elif filter_level == 'safe':
                    loc['risk_assessment']['risk_level_color'] = '#4CAF50'
                elif filter_level == 'unknown':
                    loc['risk_assessment']['risk_level_color'] = '#9E9E9E'
                else:
                    loc['risk_assessment']['risk_level_color'] = '#6366F1'
                
                if filter_level in risk_stats:
                    risk_stats[filter_level] += 1
                else:
                    risk_stats['unclassified'] += 1
        else:
            # 분류 정보가 없는 경우 (미분류)
            loc['risk_assessment'] = {
                'risk_level': 'unclassified',
                'risk_level_name': '미분류',
                'risk_level_color': '#9E9E9E',
                'description': '분류 정보가 없습니다.'
            }
            risk_stats['unclassified'] += 1
    
    # 전체 이미지 수 계산
    upload_path = Path(app.config["UPLOAD_FOLDER"])
    image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.tiff'}
    total_images = sum(1 for f in upload_path.iterdir() 
                      if f.is_file() and f.suffix.lower() in image_extensions)
    
    return render_template("map.html", 
                         locations=locations, 
                         total_images=total_images,
                         risk_stats=risk_stats)

@app.route("/api/likes/<filename>", methods=["GET", "POST"])
def handle_likes(filename):
    """좋아요 조회 및 토글"""
    social_storage = get_social_storage()
    
    if request.method == "GET":
        # 좋아요 수 및 사용자 좋아요 여부 조회
        count = social_storage.get_likes(filename)
        user_id = request.remote_addr  # IP 주소를 사용자 ID로 사용
        is_liked = social_storage.is_liked(filename, user_id)
        
        return jsonify({
            'count': count,
            'liked': is_liked
        })
    
    elif request.method == "POST":
        # 좋아요 토글
        user_id = request.remote_addr
        result = social_storage.toggle_like(filename, user_id)
        
        return jsonify(result)

@app.route("/api/comments/<filename>", methods=["GET", "POST"])
def handle_comments(filename):
    """댓글 조회 및 추가"""
    social_storage = get_social_storage()
    
    if request.method == "GET":
        # 댓글 목록 조회
        comments = social_storage.get_comments(filename)
        return jsonify({'comments': comments})
    
    elif request.method == "POST":
        # 댓글 추가
        data = request.get_json()
        comment_text = data.get('text', '').strip()
        
        if not comment_text:
            return jsonify({'error': '댓글 내용이 없습니다.'}), 400
        
        user_id = request.remote_addr
        comment = social_storage.add_comment(filename, comment_text, user_id)
        
        return jsonify(comment)

if __name__ == "__main__":
    # 외부 접속을 위해 host='0.0.0.0' 설정
    # 같은 네트워크의 다른 기기에서 접속 가능
    app.run(debug=True, host='0.0.0.0', port=8000)
