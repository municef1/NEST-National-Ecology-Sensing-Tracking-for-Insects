"""
곤충 탐지 및 분류 데모 시스템 - 메인 서버

2단계 추론 파이프라인:
1. 이미지 업로드 → 곤충 탐지 (YOLOv8)
2. 세부 이미지 업로드 → 종 분류 (EfficientNet)
"""

import os
import sys
import platform
from pathlib import Path
from flask import Flask, render_template, request, jsonify, send_from_directory, redirect, url_for
from werkzeug.utils import secure_filename
import json

# 로컬 모듈 임포트
from detector import InsectDetector
from order_classifier import OrderClassifier
from utils import (
    generate_unique_filename,
    ensure_dir,
    get_file_size,
    allowed_file,
    format_confidence,
    get_base_dir
)

# Supabase 연결
import os
from supabase import create_client, Client
from dotenv import load_dotenv
import time

# 간단한 캐시 시스템
taxonomy_cache = {}
cache_timestamp = {}
CACHE_DURATION = 300  # 5분

# 인증 시스템
from auth import AuthManager, login_required, admin_required
from ip_whitelist import init_ip_whitelist
from ip_blacklist import blacklist_manager
from ip_blacklist_enhanced import enhanced_blacklist_manager

load_dotenv()
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_ANON_KEY")
supabase_service_key = os.getenv("SUPABASE_SERVICE_KEY")
supabase: Client = create_client(supabase_url, supabase_key) if supabase_url and supabase_key else None
supabase_admin: Client = create_client(supabase_url, supabase_service_key) if supabase_url and supabase_service_key else None

# 인증 관리자 초기화 (관리자 작업용 서비스 키 클라이언트 포함)
try:
    auth_manager = AuthManager(supabase, supabase_admin)
except Exception as e:
    print(f"인증 관리자 초기화 실패: {e}")
    auth_manager = None



# 플랫폼 감지
PLATFORM = platform.system()
print(f"Running on {PLATFORM}")

# 경로 설정
BASE_DIR = get_base_dir()
UPLOAD_DIR = BASE_DIR / "uploads"
RESULT_DIR = BASE_DIR / "results"

ensure_dir(UPLOAD_DIR)
ensure_dir(RESULT_DIR)

# Flask 앱 초기화
app = Flask(__name__,
            template_folder='../templates',
            static_folder='../static')

app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB 제한
app.config['UPLOAD_FOLDER'] = str(UPLOAD_DIR)
app.config['RESULT_FOLDER'] = str(RESULT_DIR)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')

# IP 화이트리스트 보안 적용
init_ip_whitelist(app)

# 강화된 즉시 차단 보안 미들웨어
@app.before_request
def enhanced_instant_block_security():
    client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
    if not client_ip:
        return
    
    client_ip = client_ip.split(',')[0].strip()
    
    # 1단계: 기존 블랙리스트 즉시 차단 (로그 없이)
    if enhanced_blacklist_manager.is_blacklisted(client_ip):
        return '', 403
    
    # 2단계: 강화된 악성 패턴 감지
    user_agent = request.headers.get('User-Agent', '')
    method = request.method
    path = request.path
    headers = dict(request.headers)
    
    # 3단계: 비정상적인 요청 라인 검사 (MGLNDD_ 등)
    # HTTP 메소드가 비정상인 경우 차단
    if method and not method in ['GET', 'POST', 'PUT', 'DELETE', 'HEAD', 'OPTIONS', 'PATCH']:
        if 'MGLNDD' in method or '_' in method:
            enhanced_blacklist_manager.add_ip(
                client_ip, f"비정상메소드: {method}", method, request.url, user_agent
            )
            return '', 403
    
    # 요청 라인 전체 검사
    try:
        request_line = f"{method} {request.path}"
        suspicious_patterns = ['MGLNDD', 'CONNECT_', 'TUNNEL_', 'PROXY_']
        for pattern in suspicious_patterns:
            if pattern in request_line or pattern in str(request.environ.get('REQUEST_METHOD', '')):
                enhanced_blacklist_manager.add_ip(
                    client_ip, f"비정상요청: {pattern}", method, request_line, user_agent
                )
                return '', 403
    except:
        pass
    
    # 4단계: 일반 악성 패턴 검사
    malicious_reason = enhanced_blacklist_manager.is_malicious_pattern(
        client_ip, method, path, user_agent, headers
    )
    
    if malicious_reason:
        # 즉시 차단 후 블랙리스트 추가
        enhanced_blacklist_manager.add_ip(
            client_ip, malicious_reason, method, request.url, user_agent
        )
        return '', 403

# 모델 및 데이터베이스 초기화
print("학습된 모델로 초기화 중...")

# 학습된 모델 경로 설정
trained_model_path = BASE_DIR / "runs_insect_new" / "augmented_train" / "weights" / "best.pt"

try:
    if trained_model_path.exists():
        print(f"학습된 모델 로드: {trained_model_path}")
        detector = InsectDetector(
            model_path=str(trained_model_path),
            conf_threshold=0.70,  # 높은 신뢰도만 (70%)
            iou_threshold=0.45
        )
        print("✓ 학습된 탐지 모델 로드 완료")
    else:
        print(f"경고: 학습된 모델을 찾을 수 없습니다: {trained_model_path}")
        print("기본 YOLOv8 모델을 사용합니다.")
        detector = InsectDetector()
except Exception as e:
    print(f"모델 로드 실패: {e}")
    print("기본 YOLOv8 모델을 사용합니다.")
    detector = InsectDetector()

# 목 분류 모델 초기화
order_classifier = None
try:
    order_classifier_path = BASE_DIR / "best_detected_order_classifier_224.pth"
    if order_classifier_path.exists():
        print(f"목 분류 모델 로드: {order_classifier_path}")
        order_classifier = OrderClassifier(str(order_classifier_path))
        print("✓ 목 분류 모델 로드 완료")
    else:
        print("목 분류 모델을 찾을 수 없습니다.")
except Exception as e:
    print(f"목 분류 모델 로드 실패: {e}")

classifier = None
db = None
print("✓ 모델 초기화 완료")


@app.route('/login', methods=['GET', 'POST'])
def login():
    """로그인 페이지"""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        if auth_manager and auth_manager.login_user(username, password):
            return redirect(url_for('index'))
        else:
            return render_template('login.html', error='사용자명 또는 비밀번호가 잘못되었습니다.')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    """로그아웃"""
    auth_manager.logout_user()
    return redirect(url_for('login'))

@app.route('/')
@login_required
def index():
    """메인 페이지"""
    return render_template('index.html')








@app.route('/labeling_improved')
@login_required
def labeling_improved():
    """개선된 라벨링 페이지"""
    return render_template('labeling_improved.html')


@app.route('/labeling_pro')
@login_required
def labeling_pro():
    """라벨링 Pro 페이지 (배치 처리)"""
    return render_template('labeling_pro.html')


@app.route('/api/orders')
def get_orders():
    """곤충 목 목록 조회"""
    try:
        if db is None:
            return jsonify({'error': '데이터베이스 연결 실패'}), 500
        
        orders = db.get_orders()
        return jsonify(orders)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/taxonomy')
def get_taxonomy():
    """분류 정보 조회"""
    try:
        if db is None:
            return jsonify({'error': '데이터베이스 연결 실패'}), 500
        
        taxonomy = db.get_taxonomy()
        return jsonify(taxonomy)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/detect', methods=['POST'])
@login_required
def detect_insects():
    """곳충 탐지 API"""
    try:
        if detector is None:
            return jsonify({'error': '탐지 모델이 로드되지 않았습니다.'}), 500
        
        # 파일 업로드 확인
        file = None
        if 'file' in request.files:
            file = request.files['file']
        elif 'image' in request.files:
            file = request.files['image']
        
        if file is None:
            return jsonify({'error': '파일이 업로드되지 않았습니다.'}), 400
        if file.filename == '':
            return jsonify({'error': '파일이 선택되지 않았습니다.'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'error': '지원되지 않는 파일 형식입니다.'}), 400
        
        # 파일 저장
        filename = generate_unique_filename(file.filename)
        file_path = Path(app.config['UPLOAD_FOLDER']) / filename
        file.save(str(file_path))
        
        # 결과 저장 경로
        result_filename = f"detected_{filename}"
        result_path = Path(app.config['RESULT_FOLDER']) / result_filename
        
        # 탐지 수행 (TTA 제거)
        detection_result = detector.detect(
            image_path=str(file_path),
            save_path=str(result_path),
            use_tta=False
        )
        
        # 결과 반환
        return jsonify({
            'success': True,
            'detections': detection_result['detections'],
            'count': detection_result['count'],
            'result_image': f'/results/{result_filename}',
            'original_image': f'/uploads/{filename}'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/uploads/<filename>')
def uploaded_file(filename):
    """업로드된 파일 제공"""
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


@app.route('/results/<filename>')
def result_file(filename):
    """결과 파일 제공"""
    return send_from_directory(app.config['RESULT_FOLDER'], filename)


@app.route('/api/save_training_data', methods=['POST'])
@login_required
def save_training_data():
    """학습 데이터 저장 (미검수 파일 연동)"""
    try:
        if not supabase:
            return jsonify({'error': 'Supabase 연결 실패'}), 500
        
        # 현재 사용자 정보
        current_user = auth_manager.get_current_user()
        
        # 라벨링 데이터 수집
        pending_file_id = request.form.get('pending_file_id')  # 미검수 파일 ID
        image_type = request.form.get('image_type', 'detection')
        order_name = request.form.get('order_name', '')
        family_name = request.form.get('family_name', '')
        genus_name = request.form.get('genus_name', '')
        species_name = request.form.get('species_name', '')
        scientific_name = request.form.get('scientific_name', '')
        korean_name = request.form.get('korean_name', '')
        bbox_annotations = request.form.get('bbox_annotations', '')
        
        # 미검수 파일에서 오는 경우
        if pending_file_id:
            # 프론트엔드에서 보낸 파일명 사용
            filename = request.form.get('filename', 'unknown.jpg')
            
            # 중복 저장 방지: pending_file_id가 이미 completed 상태인지 확인
            pending_status = supabase.table('pending_review_files').select('status').eq('id', int(pending_file_id)).execute()
            if pending_status.data and pending_status.data[0].get('status') == 'completed':
                return jsonify({
                    'success': False,
                    'error': '이미 완료된 파일입니다. 중복 저장을 방지합니다.'
                })
            
            # 기존 데이터 확인 (덮어쓰기용)
            existing = supabase.table('labeled_images').select('id').eq('pending_file_id', int(pending_file_id)).execute()
            
            labeled_data = {
                'pending_file_id': int(pending_file_id),
                'filename': filename,
                'file_path': '',
                'image_type': image_type,
                'order_name': order_name or None,
                'family_name': family_name or None,
                'genus_name': genus_name or None,
                'species_name': species_name or None,
                'scientific_name': scientific_name or None,
                'korean_name': korean_name or None,
                'bbox_data': json.loads(bbox_annotations) if bbox_annotations else None,
                'reviewer_name': current_user['name']
            }
            
            if existing.data:
                # 덮어쓰기
                result = supabase.table('labeled_images').update(labeled_data).eq('id', existing.data[0]['id']).execute()
            else:
                # 새로 삽입
                result = supabase.table('labeled_images').insert(labeled_data).execute()
            
            # 미검수 파일 상태를 완료로 변경
            supabase.table('pending_review_files').update({
                'status': 'completed',
                'reviewed_at': 'now()'
            }).eq('id', pending_file_id).execute()
            
            return jsonify({
                'success': True,
                'message': '라벨링이 완료되었습니다.',
                'data': result.data[0] if result.data else None
            })
        
        # 기존 방식 (직접 업로드)
        else:
            # 파일 확인
            if 'image' not in request.files:
                return jsonify({'error': '이미지 파일이 없습니다.'}), 400
            
            file = request.files['image']
            if file.filename == '':
                return jsonify({'error': '파일이 선택되지 않았습니다.'}), 400
            
            # 파일 저장
            filename = generate_unique_filename(file.filename)
            file_path = UPLOAD_DIR / filename
            file.save(str(file_path))
            
            # labeled_images 테이블에 저장
            labeled_data = {
                'filename': filename,
                'file_path': str(file_path),
                'image_type': image_type,
                'order_name': order_name or None,
                'family_name': family_name or None,
                'genus_name': genus_name or None,
                'species_name': species_name or None,
                'scientific_name': scientific_name or None,
                'korean_name': korean_name or None,
                'bbox_data': json.loads(bbox_annotations) if bbox_annotations else None,
                'reviewer_name': current_user['name']
            }
            
            result = supabase.table('labeled_images').insert(labeled_data).execute()
            
            return jsonify({
                'success': True,
                'message': '데이터가 성공적으로 저장되었습니다.',
                'data': result.data[0] if result.data else None
            })
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500





@app.route('/api/classify', methods=['POST'])
@login_required
def classify_insect():
    """
    2차 분류: 곤충 이미지를 목 수준으로 분류
    
    Returns:
        JSON: 분류 결과
    """
    try:
        # 파일 확인
        if 'image' not in request.files:
            return jsonify({
                'success': False,
                'error': '이미지 파일이 없습니다.'
            }), 400
        
        file = request.files['image']
        
        if file.filename == '':
            return jsonify({
                'success': False,
                'error': '파일이 선택되지 않았습니다.'
            }), 400
        
        if not allowed_file(file.filename):
            return jsonify({
                'success': False,
                'error': '지원하지 않는 파일 형식입니다.'
            }), 400
        
        # 파일 저장
        filename = generate_unique_filename(file.filename)
        file_path = UPLOAD_DIR / filename
        file.save(str(file_path))
        
        # 목 분류 수행
        if order_classifier is None:
            return jsonify({
                'success': False,
                'error': '목 분류 모델이 로드되지 않았습니다.'
            }), 500
        
        classification_result = order_classifier.classify(str(file_path), top_k=5, use_tta=True)
        
        # 결과 반환
        return jsonify({
            'success': True,
            'order': classification_result['order'],
            'confidence': classification_result['confidence'],
            'confidence_formatted': format_confidence(classification_result['confidence']),
            'top_predictions': classification_result['top_k'],
            'image_url': f'/uploads/{filename}'
        })
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/species/<species_name>')
def get_species_info(species_name):
    """
    종 정보 조회
    
    Args:
        species_name: 종 이름
    
    Returns:
        JSON: 종 정보
    """
    try:
        if classifier is None:
            return jsonify({
                'success': False,
                'error': '분류 모델이 로드되지 않았습니다.'
            }), 500
        
        species_info = classifier.get_species_info(species_name)
        
        return jsonify({
            'success': True,
            'species_info': species_info
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500





@app.route('/api/taxonomy_stats')
@login_required
def get_taxonomy_stats():
    """분류군별 통계 조회"""
    try:
        if not supabase:
            return jsonify({'error': 'Supabase 연결 실패'}), 500
        
        result = supabase.table('labeled_images').select('*').execute()
        
        orders = set()
        families = set()
        genera = set()
        species = set()
        order_counts = {}
        
        for item in result.data:
            order = (item.get('order_name') or '').strip()
            family = (item.get('family_name') or '').strip()
            genus = (item.get('genus_name') or '').strip()
            species_name = (item.get('species_name') or '').strip()
            
            if order:
                orders.add(order)
                order_counts[order] = order_counts.get(order, 0) + 1
            if family:
                families.add(f"{order}_{family}")
            if genus:
                genera.add(f"{order}_{family}_{genus}")
            if species_name:
                species.add(f"{order}_{family}_{genus}_{species_name}")
        
        # 전체 목 정렬 (개수 기준 내림차순)
        all_orders = sorted(order_counts.items(), key=lambda x: x[1], reverse=True)
        total_images = len(result.data)
        
        # 퍼센트 계산
        orders_with_percent = []
        for order, count in all_orders:
            percentage = (count / total_images) * 100 if total_images > 0 else 0
            orders_with_percent.append({
                'order': order,
                'count': count,
                'percentage': round(percentage, 1)
            })
        
        return jsonify({
            'success': True,
            'total_images': total_images,
            'orders_count': len(orders),
            'families_count': len(families),
            'genera_count': len(genera),
            'species_count': len(species),
            'all_orders': orders_with_percent
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/training_data')
@login_required
def get_training_data():
    """저장된 학습 데이터 조회 (검색 및 필터 지원)"""
    try:
        if not supabase:
            return jsonify({'error': 'Supabase 연결 실패'}), 500
        
        # 검색 및 필터 파라미터
        search_query = request.args.get('search', '').strip()
        type_filter = request.args.get('type', '').strip()
        page = request.args.get('page', 1, type=int)
        per_page = 10  # 고정 10개
        
        # 페이지네이션 계산
        offset = (page - 1) * per_page
        
        # 기본 쿼리
        query = supabase.table('labeled_images').select('*')
        
        # 타입 필터 적용
        if type_filter:
            query = query.eq('image_type', type_filter)
        
        # 검색 필터 적용 (파일명, 검수자, 분류 정보)
        if search_query:
            # 여러 필드에서 검색 (대소문자 구분 없이)
            query = query.or_(f"filename.ilike.%{search_query}%,reviewer_name.ilike.%{search_query}%,order_name.ilike.%{search_query}%,family_name.ilike.%{search_query}%,genus_name.ilike.%{search_query}%,species_name.ilike.%{search_query}%,scientific_name.ilike.%{search_query}%,korean_name.ilike.%{search_query}%")
        
        # 페이지네이션 적용하여 데이터 조회 (ID 내림차순 - 새로 등록된 순)
        result = query.order('id', desc=True).range(offset, offset + per_page - 1).execute()
        
        # 전체 개수는 별도 쿼리로 조회
        count_query = supabase.table('labeled_images').select('*', count='exact')
        if type_filter:
            count_query = count_query.eq('image_type', type_filter)
        if search_query:
            count_query = count_query.or_(f"filename.ilike.%{search_query}%,reviewer_name.ilike.%{search_query}%,order_name.ilike.%{search_query}%,family_name.ilike.%{search_query}%,genus_name.ilike.%{search_query}%,species_name.ilike.%{search_query}%,scientific_name.ilike.%{search_query}%,korean_name.ilike.%{search_query}%")
        
        count_result = count_query.execute()
        total_count = count_result.count or 0
        
        # pending_file_id가 있는 데이터에 대해 species_folder 정보 추가
        for item in result.data:
            if item.get('pending_file_id'):
                try:
                    pending_result = supabase.table('pending_review_files').select('species_folder, batch_id').eq('id', item['pending_file_id']).execute()
                    if pending_result.data:
                        item['species_folder'] = pending_result.data[0].get('species_folder')
                        item['batch_id'] = pending_result.data[0].get('batch_id', 1)
                        print(f"[DEBUG] 파일 {item['filename']}: species_folder={item['species_folder']}, batch_id={item['batch_id']}")
                except Exception as e:
                    print(f"[DEBUG] pending_file_id {item['pending_file_id']} 조회 오류: {e}")
                    # 오류 시 기본값 사용
                    item['species_folder'] = item['filename'].replace('_00001.jpg', '').replace('_00002.jpg', '').replace('_00003.jpg', '').replace('_00004.jpg', '')
                    item['batch_id'] = 1
        
        return jsonify({
            'success': True,
            'data': result.data,
            'count': len(result.data),
            'total_count': total_count,
            'page': page,
            'per_page': per_page,
            'total_pages': (total_count + per_page - 1) // per_page
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/search')
@login_required
def search_taxonomy():
    """분류학적 자동완성 검색 (캐시 적용)"""
    try:
        if not supabase:
            return jsonify({'error': 'Supabase 연결 실패'}), 500
            
        level = request.args.get('level')  # order, family, genus, species
        query = request.args.get('q', '').strip().lower()
        order = request.args.get('order', '').strip()
        family = request.args.get('family', '').strip()
        genus = request.args.get('genus', '').strip()
        
        # 캐시 키 생성
        cache_key = f"{level}_{order}_{family}_{genus}"
        current_time = time.time()
        
        column_map = {
            'order': 'order_name',
            'family': 'family_name', 
            'genus': 'genus_name',
            'species': 'species_name'
        }
        
        if level not in column_map:
            return jsonify([])
        
        # 검색어가 있으면 직접 DB에서 검색 (종 검색처럼)
        if query:
            db_query = supabase.table('insect_species').select(column_map[level]).ilike(column_map[level], f'%{query}%')
            
            if level == 'family' and order:
                db_query = db_query.eq('order_name', order)
            elif level == 'genus' and family:
                db_query = db_query.eq('family_name', family)
            elif level == 'species' and genus:
                db_query = db_query.eq('genus_name', genus)
            
            result = db_query.limit(50).execute()
            
            # 중복 제거
            items = []
            seen = set()
            for item in result.data:
                value = item.get(column_map[level])
                if value and value not in seen:
                    seen.add(value)
                    items.append(value)
        else:
            # 검색어 없으면 캐시 사용
            if (cache_key in taxonomy_cache and 
                current_time - cache_timestamp.get(cache_key, 0) < CACHE_DURATION):
                items = taxonomy_cache[cache_key]
            else:
                # 기본 목록 조회 (제한된 수량)
                db_query = supabase.table('insect_species').select(column_map[level]).limit(1000)
                
                if level == 'family' and order:
                    db_query = db_query.eq('order_name', order)
                elif level == 'genus' and family:
                    db_query = db_query.eq('family_name', family)
                elif level == 'species' and genus:
                    db_query = db_query.eq('genus_name', genus)
                
                result = db_query.execute()
                
                # 중복 제거
                items = []
                seen = set()
                for item in result.data:
                    value = item.get(column_map[level])
                    if value and value not in seen:
                        seen.add(value)
                        items.append(value)
                
                # 캐시 저장
                taxonomy_cache[cache_key] = items
                cache_timestamp[cache_key] = current_time
        
        return jsonify(sorted(items)[:10])  # 상위 10개만
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/search_korean')
@login_required
def search_korean_name():
    """국명으로 검색"""
    try:
        if not supabase:
            return jsonify({'error': 'Supabase 연결 실패'}), 500
            
        name = request.args.get('name', '').strip()
        if not name:
            return jsonify([])
        
        result = supabase.table('insect_species').select('*').ilike('korean_name', f'%{name}%').limit(5).execute()
        return jsonify(result.data)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/search_scientific')
@login_required
def search_scientific_name():
    """학명으로 검색"""
    try:
        if not supabase:
            return jsonify({'error': 'Supabase 연결 실패'}), 500
            
        name = request.args.get('name', '').strip()
        if not name:
            return jsonify([])
        
        result = supabase.table('insect_species').select('*').ilike('scientific_name', f'%{name}%').limit(5).execute()
        return jsonify(result.data)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/admin/users')
@admin_required
def admin_get_users():
    """관리자: 사용자 목록 조회"""
    try:
        users = auth_manager.get_all_users()
        return jsonify(users)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/admin/users', methods=['POST'])
@admin_required
def admin_create_user():
    """관리자: 사용자 생성"""
    try:
        data = request.get_json()
        user = auth_manager.create_user(
            username=data['username'],
            password=data['password'],
            role=data['role'],
            name=data['name'],
            email=data.get('email')
        )
        if user:
            return jsonify({'success': True, 'user': user})
        else:
            return jsonify({'error': '사용자 생성 실패'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/admin/users/<int:user_id>', methods=['DELETE'])
@admin_required
def admin_delete_user(user_id):
    """관리자: 사용자 삭제"""
    try:
        if not supabase_admin:
            return jsonify({'error': 'Supabase 관리자 연결 실패'}), 500
        
        result = supabase_admin.table('users').delete().eq('id', user_id).execute()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/admin/taxonomy_stats')
@admin_required
def admin_get_taxonomy_stats():
    """관리자: 분류군별 통계 조회"""
    return get_taxonomy_stats()

@app.route('/api/admin/labeled-data')
@admin_required
def admin_get_labeled_data():
    """관리자: 라벨링 데이터 조회"""
    try:
        if not supabase:
            return jsonify({'error': 'Supabase 연결 실패'}), 500
        
        page = request.args.get('page', 1, type=int)
        per_page = 10  # 고정 10개
        offset = (page - 1) * per_page
        
        # 데이터 조회 (ID 내림차순 - 새로 등록된 순)
        result = supabase.table('labeled_images').select('*').order('id', desc=True).range(offset, offset + per_page - 1).execute()
        
        # 전체 개수 조회
        count_result = supabase.table('labeled_images').select('*', count='exact').execute()
        total_count = count_result.count or 0
        
        return jsonify({
            'success': True,
            'data': result.data,
            'total_count': total_count,
            'page': page,
            'per_page': per_page,
            'total_pages': (total_count + per_page - 1) // per_page
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/admin/labeled-data/<int:data_id>')
@admin_required
def admin_get_labeled_data_item(data_id):
    """관리자: 개별 라벨링 데이터 조회"""
    try:
        if not supabase:
            return jsonify({'error': 'Supabase 연결 실패'}), 500
        
        result = supabase.table('labeled_images').select('*').eq('id', data_id).execute()
        if result.data:
            return jsonify(result.data[0])
        else:
            return jsonify({'error': '데이터를 찾을 수 없습니다'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/labeled-data/<int:data_id>', methods=['DELETE'])
@admin_required
def admin_delete_labeled_data(data_id):
    """관리자: 라벨링 데이터 삭제"""
    try:
        if not supabase:
            return jsonify({'error': 'Supabase 연결 실패'}), 500
        
        result = supabase.table('labeled_images').delete().eq('id', data_id).execute()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/pending-files')
@login_required
def get_pending_files():
    """미검수 파일 목록 조회 (우선순위 기반)"""
    try:
        print("\n[DEBUG] pending-files API 호출")
        if not supabase:
            return jsonify({'error': 'Supabase 연결 실패'}), 500
        
        limit = request.args.get('limit', 20, type=int)
        print(f"[DEBUG] limit: {limit}")
        
        # 전체 미검수 파일 수 확인
        total_pending = supabase.table('pending_review_files').select('*', count='exact').eq('status', 'pending').execute()
        print(f"[DEBUG] 전체 미검수 파일 수: {total_pending.count}")
        
        # 1. 전체 목 리스트 조회 (모든 데이터 수집)
        all_orders_set = set()
        page_size = 1000
        offset = 0
        
        while True:
            species_result = supabase.table('insect_species').select('order_name').range(offset, offset + page_size - 1).execute()
            if not species_result.data:
                break
            
            for item in species_result.data:
                if item.get('order_name'):
                    all_orders_set.add(item['order_name'])
            
            if len(species_result.data) < page_size:
                break
            offset += page_size
        
        all_orders = list(all_orders_set)
        print(f"[DEBUG] 전체 목 수: {len(all_orders)}개")
        print(f"[DEBUG] 전체 목 리스트: {sorted(all_orders)}")
        
        # 2. 라벨링된 목별 개수 조회
        labeled_result = supabase.table('labeled_images').select('order_name').execute()
        order_counts = {}
        for item in labeled_result.data:
            order = item.get('order_name')
            if order:
                order_counts[order] = order_counts.get(order, 0) + 1
        print(f"[DEBUG] 라벨링된 목별 개수: {order_counts}")
        
        # 3. 모든 목을 라벨링 수 기준으로 우선순위 정렬
        priority_orders = [(order, order_counts.get(order, 0)) for order in all_orders]
        priority_orders.sort(key=lambda x: x[1])  # 라벨링 수 오름차순
        print(f"[DEBUG] 우선순위 목 (라벨링수 오름차순, 상위 15개): {priority_orders[:15]}")
        print(f"[DEBUG] 라벨링 0개인 목 수: {len([x for x in priority_orders if x[1] == 0])}개")
        
        # 4. 이미 라벨링된 파일 ID와 파일명 목록 조회
        labeled_result = supabase.table('labeled_images').select('pending_file_id, filename').execute()
        labeled_file_ids = set(item.get('pending_file_id') for item in labeled_result.data if item.get('pending_file_id'))
        labeled_filenames = set(item.get('filename') for item in labeled_result.data if item.get('filename') and item.get('filename').strip())
        print(f"[DEBUG] 이미 라벨링된 파일 ID: {len(labeled_file_ids)}개")
        print(f"[DEBUG] 이미 라벨링된 파일명: {len(labeled_filenames)}개")
        print(f"[DEBUG] 라벨링된 파일 ID 샘플: {list(labeled_file_ids)[:10]}")
        print(f"[DEBUG] 라벨링된 파일명 샘플: {list(labeled_filenames)[:10]}")
        
        # 5. 우선순위 순으로 20개를 채울 때까지 파일 수집 (라벨링된 파일 제외)
        selected_files = []
        
        # 중복 방지를 위한 추가 체크
        selected_file_ids = set()
        selected_filenames = set()
        
        for order_name, count in priority_orders:
            if len(selected_files) >= limit:
                break
                
            print(f"[DEBUG] {order_name} 목 시도 (라벨링 {count}개)")
            remaining = limit - len(selected_files)
            result = supabase.table('pending_review_files').select('*').eq('status', 'pending').eq('order_name', order_name).limit(remaining * 2).execute()  # 여유분 확보
            
            # 이미 라벨링된 파일 제외 (ID와 파일명 모두 확인)
            filtered_files = []
            for file in result.data:
                file_id = file.get('id')
                filename = file.get('filename', '').strip()
                
                # ID 기준 제외
                if file_id in labeled_file_ids:
                    print(f"[DEBUG] {order_name} 목에서 ID {file_id} 제외 (이미 라벨링됨)")
                    continue
                
                # 파일명 기준 제외
                if filename and filename in labeled_filenames:
                    print(f"[DEBUG] {order_name} 목에서 파일명 '{filename}' 제외 (이미 라벨링됨)")
                    continue
                
                filtered_files.append(file)
            
            print(f"[DEBUG] {order_name} 목의 미검수 파일: {len(result.data)}개 -> 필터링 후: {len(filtered_files)}개")
            
            if filtered_files:
                # 필요한 만큼만 추가 (중복 방지)
                files_to_add = []
                for file in filtered_files:
                    if len(selected_files) >= limit:
                        break
                    
                    file_id = file.get('id')
                    filename = file.get('filename', '').strip()
                    
                    # 이미 선택된 파일인지 체크
                    if file_id in selected_file_ids or (filename and filename in selected_filenames):
                        print(f"[DEBUG] {order_name} 목에서 중복 방지: ID {file_id}, 파일명 '{filename}'")
                        continue
                    
                    files_to_add.append(file)
                    selected_file_ids.add(file_id)
                    if filename:
                        selected_filenames.add(filename)
                
                selected_files.extend(files_to_add)
                print(f"[DEBUG] {order_name} 목에서 {len(files_to_add)}개 파일 추가 (총 {len(selected_files)}개)")
                added_ids = [file.get('id') for file in files_to_add[:3]]
                print(f"[DEBUG] 추가된 파일 ID 샘플: {added_ids}")
        

        
        # 6. 목 정보 없는 파일로 최종 채우기 (라벨링된 파일 제외)
        if len(selected_files) < limit:
            print("[DEBUG] 목 정보 없는 파일로 최종 채우기")
            remaining = limit - len(selected_files)
            result = supabase.table('pending_review_files').select('*').eq('status', 'pending').is_('order_name', 'null').limit(remaining * 2).execute()
            
            # 이미 라벨링된 파일 제외 (ID와 파일명 모두 확인)
            filtered_files = []
            for file in result.data:
                file_id = file.get('id')
                filename = file.get('filename', '').strip()
                
                # ID 기준 제외
                if file_id in labeled_file_ids:
                    print(f"[DEBUG] 목 정보 없는 파일에서 ID {file_id} 제외 (이미 라벨링됨)")
                    continue
                
                # 파일명 기준 제외
                if filename and filename in labeled_filenames:
                    print(f"[DEBUG] 목 정보 없는 파일에서 파일명 '{filename}' 제외 (이미 라벨링됨)")
                    continue
                
                filtered_files.append(file)
            
            print(f"[DEBUG] 목 정보 없는 미검수 파일: {len(result.data)}개 -> 필터링 후: {len(filtered_files)}개")
            
            if filtered_files:
                # 필요한 만큼만 추가 (중복 방지)
                files_to_add = []
                for file in filtered_files:
                    if len(selected_files) >= limit:
                        break
                    
                    file_id = file.get('id')
                    filename = file.get('filename', '').strip()
                    
                    # 이미 선택된 파일인지 체크
                    if file_id in selected_file_ids or (filename and filename in selected_filenames):
                        print(f"[DEBUG] 목 정보 없는 파일에서 중복 방지: ID {file_id}, 파일명 '{filename}'")
                        continue
                    
                    files_to_add.append(file)
                    selected_file_ids.add(file_id)
                    if filename:
                        selected_filenames.add(filename)
                
                selected_files.extend(files_to_add)
                print(f"[DEBUG] 목 정보 없는 파일에서 {len(files_to_add)}개 추가 (총 {len(selected_files)}개)")
                added_ids = [file.get('id') for file in files_to_add[:3]]
                print(f"[DEBUG] 추가된 파일 ID 샘플: {added_ids}")
        
        print(f"[DEBUG] 최종 선택된 파일 수: {len(selected_files)}개 (라벨링된 파일 ID {len(labeled_file_ids)}개, 파일명 {len(labeled_filenames)}개 제외)")
        if selected_files:
            selected_ids = [file.get('id') for file in selected_files[:5]]
            selected_filenames = [file.get('filename') for file in selected_files[:5]]
            print(f"[DEBUG] 선택된 파일 ID 샘플: {selected_ids}")
            print(f"[DEBUG] 선택된 파일명 샘플: {selected_filenames}")
        return jsonify({
            'success': True,
            'data': selected_files,
            'count': len(selected_files)
        })
    except Exception as e:
        print(f"[DEBUG] 오류: {e}")
        return jsonify({'error': str(e)}), 500





@app.route('/api/pending-files/<int:file_id>/complete', methods=['POST'])
@login_required
def complete_pending_file_review(file_id):
    """미검수 파일 검수 완료 처리"""
    try:
        if not supabase:
            return jsonify({'error': 'Supabase 연결 실패'}), 500
        
        # 파일 상태를 완료로 변경
        supabase.table('pending_review_files').update({
            'status': 'completed',
            'reviewed_at': 'now()'
        }).eq('id', file_id).execute()
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/pending-files/<int:file_id>/skip', methods=['POST'])
@login_required
def skip_pending_file(file_id):
    """미검수 파일 건너뛰기"""
    try:
        if not supabase:
            return jsonify({'error': 'Supabase 연결 실패'}), 500
        
        # 파일 상태를 다시 pending으로 변경
        supabase.table('pending_review_files').update({
            'status': 'pending',
            'assigned_reviewer': None
        }).eq('id', file_id).execute()
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/pending-files/<int:file_id>/exclude', methods=['POST'])
@login_required
def exclude_pending_file(file_id):
    """미검수 파일 라벨링 대상에서 제외"""
    try:
        if not supabase:
            return jsonify({'error': 'Supabase 연결 실패'}), 500
        
        data = request.get_json()
        reason = data.get('reason', '라벨링 대상 제외')
        current_user = auth_manager.get_current_user()
        
        # 파일 상태를 excluded로 변경
        supabase.table('pending_review_files').update({
            'status': 'excluded',
            'assigned_reviewer': current_user['name'],
            'reviewed_at': 'now()'
        }).eq('id', file_id).execute()
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/pending-files/reviewing')
@login_required
def get_reviewing_files():
    """검토 필요 파일 목록 조회"""
    try:
        if not supabase:
            return jsonify({'error': 'Supabase 연결 실패'}), 500
        
        limit = request.args.get('limit', 20, type=int)
        
        # reviewing 상태 파일들만 조회
        result = supabase.table('pending_review_files').select('*').eq('status', 'reviewing').limit(limit).execute()
        
        return jsonify({
            'success': True,
            'data': result.data,
            'count': len(result.data)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/pending-files/<int:file_id>/mark-review', methods=['POST'])
@login_required
def mark_file_for_review(file_id):
    """파일을 검토 필요 상태로 변경"""
    try:
        if not supabase:
            return jsonify({'error': 'Supabase 연결 실패'}), 500
        
        current_user = auth_manager.get_current_user()
        
        # 파일 상태를 reviewing으로 변경
        supabase.table('pending_review_files').update({
            'status': 'reviewing',
            'assigned_reviewer': current_user['name']
        }).eq('id', file_id).execute()
        
        return jsonify({
            'success': True,
            'message': '파일이 검토 필요 상태로 변경되었습니다.'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500





@app.route('/admin/duplicates')
@admin_required
def admin_duplicates_page():
    """중복 관리 페이지"""
    return render_template('admin_duplicates.html')


@app.route('/api/admin/duplicates/check')
@admin_required
def check_duplicates():
    """중복 파일 검사"""
    try:
        from collections import Counter
        
        if not supabase:
            return jsonify({'success': False, 'error': 'Supabase 연결 실패'}), 500
        
        # labeled_images 중복 검사
        result = supabase.table('labeled_images').select('*').execute()
        
        # filename 중복
        filenames = [item.get('filename', '') for item in result.data if item.get('filename')]
        filename_counts = Counter(filenames)
        filename_duplicates = {k: v for k, v in filename_counts.items() if v > 1}
        
        # pending_file_id 중복
        pending_ids = [item.get('pending_file_id') for item in result.data if item.get('pending_file_id')]
        pending_counts = Counter(pending_ids)
        pending_duplicates = {k: v for k, v in pending_counts.items() if v > 1}
        
        # 중복 상세 정보
        duplicate_details = []
        
        for filename, count in filename_duplicates.items():
            dup_result = supabase.table('labeled_images').select('*').eq('filename', filename).execute()
            duplicate_details.append({
                'type': 'filename',
                'key': filename,
                'count': count,
                'records': dup_result.data
            })
        
        for pid, count in pending_duplicates.items():
            dup_result = supabase.table('labeled_images').select('*').eq('pending_file_id', pid).execute()
            duplicate_details.append({
                'type': 'pending_file_id',
                'key': pid,
                'count': count,
                'records': dup_result.data
            })
        
        return jsonify({
            'success': True,
            'summary': {
                'filename_duplicates': len(filename_duplicates),
                'pending_id_duplicates': len(pending_duplicates),
                'total_records': len(result.data)
            },
            'duplicates': duplicate_details
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/admin/duplicates/test')
@admin_required
def test_duplicates_api():
    """중복 API 테스트"""
    return jsonify({
        'success': True,
        'message': 'API 연결 성공',
        'supabase_connected': supabase is not None
    })


@app.route('/api/admin/duplicates/remove', methods=['POST'])
@admin_required
def remove_duplicate():
    """중복 파일 제거"""
    try:
        if not supabase:
            return jsonify({'success': False, 'error': 'Supabase 연결 실패'}), 500
        
        data = request.get_json()
        record_id = data.get('id')
        
        if not record_id:
            return jsonify({'success': False, 'error': 'ID가 필요합니다'}), 400
        
        # 레코드 삭제
        result = supabase.table('labeled_images').delete().eq('id', record_id).execute()
        
        return jsonify({
            'success': True,
            'message': f'ID {record_id} 레코드가 삭제되었습니다.'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/admin/duplicates/clean', methods=['POST'])
@admin_required
def clean_duplicates():
    """중복 파일 자동 정리 (오래된 것 삭제)"""
    try:
        from collections import defaultdict
        
        if not supabase:
            return jsonify({'success': False, 'error': 'Supabase 연결 실패'}), 500
        
        # 모든 labeled_images 데이터 조회
        result = supabase.table('labeled_images').select('*').order('created_at', desc=False).execute()
        
        deleted_count = 0
        
        # 1. pending_file_id 기준 중복 정리
        pending_groups = defaultdict(list)
        for item in result.data:
            if item.get('pending_file_id'):
                pending_groups[item['pending_file_id']].append(item)
        
        for pending_id, items in pending_groups.items():
            if len(items) > 1:
                for item in items[1:]:
                    supabase.table('labeled_images').delete().eq('id', item['id']).execute()
                    deleted_count += 1
        
        # 2. filename 기준 중복 정리 (남은 데이터에서)
        # 다시 조회 (삭제 후 업데이트된 데이터)
        result = supabase.table('labeled_images').select('*').order('created_at', desc=False).execute()
        
        filename_groups = defaultdict(list)
        for item in result.data:
            if item.get('filename'):
                filename_groups[item['filename']].append(item)
        
        for filename, items in filename_groups.items():
            if len(items) > 1:
                for item in items[1:]:
                    supabase.table('labeled_images').delete().eq('id', item['id']).execute()
                    deleted_count += 1
        
        return jsonify({
            'success': True,
            'message': f'{deleted_count}개의 중복 레코드가 삭제되었습니다.'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/storage-image/<int:batch_id>/<path:species_folder>/<filename>')
@login_required
def get_storage_image(batch_id, species_folder, filename):
    """Supabase Storage에서 이미지 제공 (로컬 폴백 지원)"""
    try:
        if not supabase:
            return jsonify({'error': 'Supabase 연결 실패'}), 500
        
        # species_folder에서 파일명 추출 (중복 제거)
        if filename in species_folder:
            # species_folder가 "Tenthredo_fuscoterminata_00004.jpg"이고 filename도 같은 경우
            actual_species = species_folder.replace('_00001.jpg', '').replace('_00002.jpg', '').replace('_00003.jpg', '').replace('_00004.jpg', '')
            storage_path = f"batch_{batch_id}/{actual_species}/{filename}"
        else:
            storage_path = f"batch_{batch_id}/{species_folder}/{filename}"
            
        print(f"[STORAGE] 수정된 요청: {storage_path}")
        
        # Storage에서 이미지 다운로드 시도
        try:
            response = supabase.storage.from_('review-images').download(storage_path)
            
            if response:
                from flask import Response
                import mimetypes
                
                mime_type = mimetypes.guess_type(filename)[0] or 'image/jpeg'
                return Response(response, mimetype=mime_type)
                
        except Exception as storage_error:
            print(f"[STORAGE] 다운로드 오류: {storage_path} -> {storage_error}")
        
        # 로컬 파일로 폴백 (species_folder 정리)
        clean_species = species_folder.replace('_00001.jpg', '').replace('_00002.jpg', '').replace('_00003.jpg', '').replace('_00004.jpg', '')
        local_path = BASE_DIR / "organized_images" / clean_species / filename
        print(f"[STORAGE] 로컬 폴백: {local_path}")
        
        if local_path.exists():
            return send_from_directory(str(local_path.parent), filename)
        
        return jsonify({'error': '이미지를 찾을 수 없습니다'}), 404
            
    except Exception as e:
        print(f"[STORAGE] API 오류: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/debug/test-priority')
@admin_required
def test_priority_algorithm():
    """우선순위 알고리즘 테스트 (실제 할당 없이)"""
    try:
        if not supabase:
            return jsonify({'error': 'Supabase 연결 실패'}), 500
        
        # 라벨링 통계
        labeled_result = supabase.table('labeled_images').select('order_name').execute()
        order_counts = {}
        for item in labeled_result.data:
            order = (item.get('order_name') or '').strip()
            if order:
                order_counts[order] = order_counts.get(order, 0) + 1
        
        # 미검수 파일 분석
        pending_result = supabase.table('pending_review_files').select('*').eq('status', 'pending').limit(50).execute()
        
        files_by_order = {}
        files_without_order = []
        
        for file_data in pending_result.data:
            species_folder = file_data.get('species_folder', '')
            order = None
            
            if species_folder:
                clean_name = species_folder
                for suffix in ['_00001.jpg', '_00002.jpg', '_00003.jpg', '_00004.jpg', '.jpg']:
                    clean_name = clean_name.replace(suffix, '')
                parts = clean_name.split('_')
                
                if len(parts) >= 2:
                    genus = parts[0]
                    species = parts[1]
                    scientific_name = f"{genus} {species}"
                    
                    try:
                        species_result = supabase.table('insect_species').select('order_name').or_(
                            f"scientific_name.ilike.%{scientific_name}%,genus_name.eq.{genus}"
                        ).limit(1).execute()
                        
                        if species_result.data:
                            order = species_result.data[0].get('order_name')
                    except:
                        pass
            
            if order:
                if order not in files_by_order:
                    files_by_order[order] = []
                files_by_order[order].append(file_data)
            else:
                files_without_order.append(file_data)
        
        # 우선순위 계산
        all_orders = set(order_counts.keys()) | set(files_by_order.keys())
        order_priority = []
        
        for order in all_orders:
            labeled_count = order_counts.get(order, 0)
            files = files_by_order.get(order, [])
            if files:
                order_priority.append({
                    'order': order,
                    'labeled_count': labeled_count,
                    'pending_count': len(files),
                    'priority_score': labeled_count  # 낮을수록 우선순위 높음
                })
        
        order_priority.sort(key=lambda x: x['priority_score'])
        
        return jsonify({
            'success': True,
            'analysis': {
                'total_pending': len(pending_result.data),
                'mapped_to_orders': sum(len(files) for files in files_by_order.values()),
                'unmapped_files': len(files_without_order),
                'orders_found': len(files_by_order),
                'priority_ranking': order_priority[:10],  # 상위 10개만
                'recommended_file': order_priority[0] if order_priority else None
            }
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/batches')
@login_required
def get_batches():
    """배치 목록 조회"""
    try:
        if not supabase:
            return jsonify({'error': 'Supabase 연결 실패'}), 500
        
        # 배치별 통계
        result = supabase.table('pending_review_files').select('batch_id, status').execute()
        
        batch_stats = {}
        for item in result.data:
            batch_id = item['batch_id']
            status = item['status']
            
            if batch_id not in batch_stats:
                batch_stats[batch_id] = {'total': 0, 'pending': 0, 'reviewing': 0, 'completed': 0}
            
            batch_stats[batch_id]['total'] += 1
            batch_stats[batch_id][status] += 1
        
        batches = []
        for batch_id, stats in batch_stats.items():
            completion_rate = stats['completed'] / stats['total'] if stats['total'] > 0 else 0
            batches.append({
                'batch_id': batch_id,
                'total_files': stats['total'],
                'completed': stats['completed'],
                'pending': stats['pending'],
                'reviewing': stats['reviewing'],
                'completion_rate': round(completion_rate * 100, 1)
            })
        
        return jsonify(sorted(batches, key=lambda x: x['batch_id']))
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/health')
def health_check():
    """헬스 체크"""
    return jsonify({
        'success': True,
        'platform': PLATFORM,
        'detector_loaded': detector is not None,
        'order_classifier_loaded': order_classifier is not None,
        'classifier_loaded': classifier is not None,
        'supabase_connected': supabase is not None
    })


@app.route('/api/debug/priority-system')
@admin_required
def debug_priority_system():
    """우선순위 시스템 디버깅 API"""
    try:
        if not supabase:
            return jsonify({'error': 'Supabase 연결 실패'}), 500
        
        debug_info = {}
        
        # 1. 테이블 상태 확인
        try:
            pending_count = supabase.table('pending_review_files').select('*', count='exact').execute()
            labeled_count = supabase.table('labeled_images').select('*', count='exact').execute()
            species_count = supabase.table('insect_species').select('*', count='exact').execute()
            
            debug_info['table_status'] = {
                'pending_review_files': pending_count.count,
                'labeled_images': labeled_count.count,
                'insect_species': species_count.count
            }
        except Exception as e:
            debug_info['table_status'] = {'error': str(e)}
        
        # 2. 미검수 파일 상태 분포
        try:
            status_result = supabase.table('pending_review_files').select('status').execute()
            status_counts = {}
            for item in status_result.data:
                status = item.get('status', 'unknown')
                status_counts[status] = status_counts.get(status, 0) + 1
            debug_info['status_distribution'] = status_counts
        except Exception as e:
            debug_info['status_distribution'] = {'error': str(e)}
        
        # 3. species_folder 패턴 샘플
        try:
            sample_files = supabase.table('pending_review_files').select('id, species_folder').eq('status', 'pending').limit(10).execute()
            debug_info['species_folder_samples'] = []
            
            for file_data in sample_files.data:
                species_folder = file_data.get('species_folder', '')
                if species_folder:
                    clean_name = species_folder
                    for suffix in ['_00001.jpg', '_00002.jpg', '_00003.jpg', '_00004.jpg', '.jpg']:
                        clean_name = clean_name.replace(suffix, '')
                    parts = clean_name.split('_')
                    
                    debug_info['species_folder_samples'].append({
                        'id': file_data['id'],
                        'original': species_folder,
                        'cleaned': clean_name,
                        'parts': parts,
                        'genus': parts[0] if len(parts) > 0 else None,
                        'species': parts[1] if len(parts) > 1 else None
                    })
        except Exception as e:
            debug_info['species_folder_samples'] = {'error': str(e)}
        
        # 4. 목 매핑 테스트
        try:
            mapping_test = []
            test_files = supabase.table('pending_review_files').select('species_folder').eq('status', 'pending').limit(5).execute()
            
            for file_data in test_files.data:
                species_folder = file_data.get('species_folder', '')
                if not species_folder:
                    continue
                
                clean_name = species_folder
                for suffix in ['_00001.jpg', '_00002.jpg', '_00003.jpg', '_00004.jpg', '.jpg']:
                    clean_name = clean_name.replace(suffix, '')
                parts = clean_name.split('_')
                
                if len(parts) >= 2:
                    genus = parts[0]
                    species = parts[1]
                    scientific_name = f"{genus} {species}"
                    
                    try:
                        species_result = supabase.table('insect_species').select('order_name').or_(
                            f"scientific_name.ilike.%{scientific_name}%,genus_name.eq.{genus}"
                        ).limit(1).execute()
                        
                        order = species_result.data[0].get('order_name') if species_result.data else None
                        
                        mapping_test.append({
                            'species_folder': species_folder,
                            'scientific_name': scientific_name,
                            'order': order,
                            'success': order is not None
                        })
                    except Exception as mapping_error:
                        mapping_test.append({
                            'species_folder': species_folder,
                            'scientific_name': scientific_name,
                            'error': str(mapping_error),
                            'success': False
                        })
            
            debug_info['mapping_test'] = mapping_test
        except Exception as e:
            debug_info['mapping_test'] = {'error': str(e)}
        
        # 5. 라벨링 통계
        try:
            labeled_result = supabase.table('labeled_images').select('order_name').execute()
            order_counts = {}
            
            for item in labeled_result.data:
                order = (item.get('order_name') or '').strip()
                if order:
                    order_counts[order] = order_counts.get(order, 0) + 1
            
            debug_info['labeling_stats'] = {
                'total_labeled': len(labeled_result.data),
                'orders_with_labels': len(order_counts),
                'order_distribution': dict(sorted(order_counts.items(), key=lambda x: x[1]))
            }
        except Exception as e:
            debug_info['labeling_stats'] = {'error': str(e)}
        
        return jsonify({
            'success': True,
            'debug_info': debug_info,
            'timestamp': time.time()
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500





# 파일 기반 화이트리스트 관리
WHITELIST_FILE = BASE_DIR / 'whitelist.json'

def load_whitelist():
    """whitelist.json 파일에서 화이트리스트 로드"""
    default_data = [
        {'ip_address': '127.0.0.1', 'description': '로컬호스트', 'is_default': True, 'created_at': '2024-01-01T00:00:00Z'},
        {'ip_address': '::1', 'description': 'IPv6 로컬호스트', 'is_default': True, 'created_at': '2024-01-01T00:00:00Z'},
        {'ip_address': '192.168.0.0/16', 'description': '사설 IP 대역', 'is_default': True, 'created_at': '2024-01-01T00:00:00Z'},
        {'ip_address': '10.0.0.0/8', 'description': '사설 IP 대역', 'is_default': True, 'created_at': '2024-01-01T00:00:00Z'},
        {'ip_address': '172.16.0.0/12', 'description': '사설 IP 대역', 'is_default': True, 'created_at': '2024-01-01T00:00:00Z'},
        {'ip_address': '175.193.255.236', 'description': '메인 사용자 IP', 'is_default': False, 'created_at': '2024-01-01T00:00:00Z'},
    ]
    
    try:
        if WHITELIST_FILE.exists():
            with open(WHITELIST_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except:
        pass
    
    # 기본 데이터로 파일 생성
    save_whitelist(default_data)
    return default_data

def save_whitelist(data):
    """whitelist.json 파일에 화이트리스트 저장"""
    try:
        with open(WHITELIST_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"화이트리스트 저장 오류: {e}")

# 화이트리스트 로드
whitelist_data = load_whitelist()

@app.route('/api/admin/whitelist')
@admin_required
def get_whitelist():
    """화이트리스트 조회"""
    try:
        return jsonify(whitelist_data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/admin/whitelist', methods=['POST'])
@admin_required
def add_to_whitelist():
    """화이트리스트에 IP 추가"""
    try:
        data = request.get_json()
        ip_address = data.get('ip_address', '').strip()
        description = data.get('description', '').strip()
        
        if not ip_address:
            return jsonify({'error': 'IP 주소가 필요합니다'}), 400
        
        # IP 주소 유효성 검사
        import ipaddress
        try:
            if '/' in ip_address:
                ipaddress.ip_network(ip_address, strict=False)
            else:
                ipaddress.ip_address(ip_address)
        except ValueError:
            return jsonify({'error': '유효하지 않은 IP 주소 형식입니다'}), 400
        
        # 중복 확인
        for item in whitelist_data:
            if item['ip_address'] == ip_address:
                return jsonify({'error': '이미 등록된 IP 주소입니다'}), 400
        
        # 새 IP 추가
        import datetime
        new_item = {
            'ip_address': ip_address,
            'description': description or '설명 없음',
            'is_default': False,
            'created_at': datetime.datetime.now().isoformat() + 'Z'
        }
        whitelist_data.append(new_item)
        save_whitelist(whitelist_data)  # 파일에 저장
        
        return jsonify({'success': True, 'data': new_item})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/admin/whitelist/<path:ip>', methods=['DELETE'])
@admin_required
def remove_from_whitelist(ip):
    """화이트리스트에서 IP 제거"""
    try:
        global whitelist_data
        
        # 기본 설정 체크
        for item in whitelist_data:
            if item['ip_address'] == ip and item['is_default']:
                return jsonify({'error': '기본 설정은 삭제할 수 없습니다'}), 400
        
        # IP 제거
        whitelist_data[:] = [item for item in whitelist_data if item['ip_address'] != ip]
        save_whitelist(whitelist_data)  # 파일에 저장
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    print("=" * 60)
    print("곤충 탐지 및 분류 데모 시스템")
    print("=" * 60)
    print(f"플랫폼: {PLATFORM}")
    print(f"접속 주소: http://localhost:8000")
    print("=" * 60)
    print("주요 기능:")
    print("1. 이미지 업로드 → 곤충 탐지 (YOLOv8)")
    print("2. 세부 이미지 업로드 → 종 분류 (EfficientNet)")
    print("3. 종 정보 제공 (학명, 일반명, 특징 등)")
    print("=" * 60)
    print(f"모델 상태:")
    print(f"- 탐지 모델: {'✓ 로드됨' if detector else '✗ 미로드'}")
    print(f"- 목 분류 모델: {'✓ 로드됨' if order_classifier else '✗ 미로드'}")
    print(f"- 종 분류 모델: {'✓ 로드됨' if classifier else '✗ 미로드'}")
    print("=" * 60)
    
    app.run(
        host='0.0.0.0',
        port=8000,
        debug=True,
        use_reloader=False
    )

