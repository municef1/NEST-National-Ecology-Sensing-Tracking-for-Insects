import torch
import torch.nn as nn
import timm
import json
import cv2
import numpy as np
import albumentations as A
from albumentations.pytorch.transforms import ToTensorV2
from pathlib import Path
from PIL import Image


class HierarchicalClassifier:
    """계층적 곤충 분류 시스템 (목 -> 과 -> 속 -> 종)"""
    
    def __init__(self, models_dir=None, device=None):
        """
        초기화
        
        Args:
            models_dir: 모델 파일들이 저장된 디렉토리
            device: 사용할 디바이스 ('cuda' or 'cpu')
        """
        self.device = device if device else ('cuda' if torch.cuda.is_available() else 'cpu')
        
        if models_dir is None:
            models_dir = Path(__file__).parent / "models"
        
        self.models_dir = Path(models_dir)
        
        # 분류기 정의 (목 -> 과 -> 속 -> 종)
        self.classifiers = {}
        self.class_mappings = {}
        
        # 전처리 설정
        self.transform = A.Compose([
            A.Resize(224, 224),
            A.Normalize(mean=(0.485, 0.456, 0.406), std=(0.229, 0.224, 0.225), max_pixel_value=255.0),
            ToTensorV2()
        ])
        
        # 모델 인벤토리 로드
        self.load_model_inventory()
        
        # 분류기 로드
        self.load_classifiers()
    
    def load_model_inventory(self):
        """모델 인벤토리 로드"""
        inventory_path = self.models_dir / "model_inventory.json"
        
        if inventory_path.exists():
            with open(inventory_path, 'r', encoding='utf-8') as f:
                self.inventory = json.load(f)
            print("✓ 모델 인벤토리 로드 완료")
        else:
            print("⚠️ 모델 인벤토리가 없습니다. 기본 구조를 사용합니다.")
            self.inventory = {"order": {}, "family": {}, "genus": {}, "species": {}}
    
    def load_classifiers(self):
        """모든 계층적 분류기 로드"""
        print("계층적 분류기 로드 중...")
        
        # 각 레벨별로 분류기 로드
        for level in ["order", "family", "genus", "species"]:
            level_dir = self.models_dir / level
            
            if not level_dir.exists():
                continue
            
            for model_name, model_info in self.inventory.get(level, {}).items():
                if not model_info.get("available", False):
                    continue
                
                model_path = level_dir / model_info["model_file"]
                classes_path = level_dir / model_info["classes_file"] if model_info["classes_file"] else None
                
                if model_path.exists() and classes_path and classes_path.exists():
                    classifier = self._load_single_classifier(model_path, classes_path, level)
                    if classifier:
                        self.classifiers[model_name] = classifier
                        print(f"✓ {level} 분류기 로드: {model_name}")
    
    def _load_single_classifier(self, model_path, classes_path, level):
        """단일 분류기 로드"""
        try:
            # 클래스 정보 로드
            with open(classes_path, 'r', encoding='utf-8') as f:
                class_to_idx = json.load(f)
            idx_to_class = {v: k for k, v in class_to_idx.items()}
            
            # 모델 선택: 목 분류기는 EfficientNet-B4, 나머지는 ResNet50
            num_classes = len(class_to_idx)
            
            if level == 'order':
                # 목 분류기: EfficientNet-B4
                model = timm.create_model('efficientnet_b4', pretrained=False, num_classes=num_classes)
            else:
                # 과/속/종 분류기: ResNet50
                model = timm.create_model('resnet50', pretrained=False, num_classes=num_classes)
            
            # 모델 가중치 로드
            try:
                state_dict = torch.load(str(model_path), map_location=self.device)
                model.load_state_dict(state_dict, strict=False)
            except Exception as load_error:
                print(f"모델 로드 시도 실패: {load_error}")
                return None
            
            model = model.to(self.device)
            model.eval()
            
            return {
                'model': model,
                'class_to_idx': class_to_idx,
                'idx_to_class': idx_to_class,
                'level': level
            }
        except Exception as e:
            print(f"분류기 로드 오류 ({model_path}): {str(e)}")
            return None
    
    def classify_hierarchical(self, image, order_name, top_k=3):
        """
        계층적 분류 수행
        
        Args:
            image: 입력 이미지 (numpy array)
            order_name: 목 이름
            top_k: 각 단계별 상위 k개 결과
            
        Returns:
            dict: 계층적 분류 결과
        """
        result = {
            'order': order_name,
            'family': None,
            'genus': None,
            'species': None,
            'confidence_scores': {}
        }
        
        # 동적으로 사용 가능한 분류기 찾기
        available_classifiers = self._find_available_classifiers(order_name)
        
        # 과 분류
        if available_classifiers.get('family'):
            family_result = self._classify_single(image, available_classifiers['family'], top_k)
            if family_result:
                result['family'] = family_result[0]['name']
                result['confidence_scores']['family'] = family_result[0]['confidence']
                
                # 속 분류
                family_name = result['family']
                genus_classifier = self._find_genus_classifier(family_name)
                if genus_classifier:
                    genus_result = self._classify_single(image, genus_classifier, top_k)
                    if genus_result:
                        result['genus'] = genus_result[0]['name']
                        result['confidence_scores']['genus'] = genus_result[0]['confidence']
                        
                        # 종 분류
                        genus_name = result['genus']
                        species_classifier = self._find_species_classifier(genus_name)
                        if species_classifier:
                            species_result = self._classify_single(image, species_classifier, top_k)
                            if species_result:
                                result['species'] = species_result[0]['name']
                                result['confidence_scores']['species'] = species_result[0]['confidence']
                                result['species_candidates'] = species_result
        
        return result
    
    def _find_available_classifiers(self, order_name):
        """주어진 목에 대해 사용 가능한 분류기들 찾기"""
        available = {}
        
        # 과 분류기 찾기
        for classifier_name in self.classifiers:
            if 'family' in classifier_name and order_name.replace('목', '') in classifier_name:
                available['family'] = classifier_name
                break
        
        return available
    
    def _find_genus_classifier(self, family_name):
        """주어진 과에 대한 속 분류기 찾기"""
        for classifier_name in self.classifiers:
            if 'genus' in classifier_name and family_name.replace('과', '') in classifier_name:
                return classifier_name
        return None
    
    def _find_species_classifier(self, genus_name):
        """주어진 속에 대한 종 분류기 찾기"""
        for classifier_name in self.classifiers:
            if 'species' in classifier_name and genus_name.lower() in classifier_name.lower():
                return classifier_name
        return None
    
    def _classify_single(self, image, classifier_key, top_k=3):
        """단일 분류기로 분류 수행"""
        if classifier_key not in self.classifiers:
            return None
        
        classifier = self.classifiers[classifier_key]
        if classifier is None:
            return None
        
        try:
            # 이미지 전처리
            transformed = self.transform(image=image)
            input_tensor = transformed['image'].unsqueeze(0).to(self.device)
            
            # 추론
            with torch.no_grad():
                outputs = classifier['model'](input_tensor)
                probabilities = torch.softmax(outputs, 1)[0]
                top_probs, top_indices = torch.topk(probabilities, min(top_k, len(probabilities)))
            
            # 결과 파싱
            results = []
            for prob, idx in zip(top_probs, top_indices):
                class_name = classifier['idx_to_class'].get(idx.item(), f"Class_{idx.item()}")
                results.append({
                    'name': class_name,
                    'confidence': prob.item()
                })
            
            return results
        
        except Exception as e:
            print(f"분류 오류 ({classifier_key}): {str(e)}")
            return None
    
    def classify_detections(self, image_path, detections, order_results, crop_dir=None):
        """
        탐지된 곤충들을 계층적으로 분류
        
        Args:
            image_path: 원본 이미지 경로
            detections: 탐지 결과 리스트
            order_results: 목 분류 결과 리스트
            crop_dir: 크롭 이미지 저장 디렉토리
            
        Returns:
            list: 각 탐지에 대한 계층적 분류 결과
        """
        # 원본 이미지 로드
        with open(str(image_path), 'rb') as f:
            image_data = f.read()
        image_array = np.frombuffer(image_data, np.uint8)
        image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        classification_results = []
        
        for idx, det in enumerate(detections):
            # 바운딩 박스 정보 추출
            if isinstance(det, dict):
                bbox = det.get('bbox', det)
            else:
                bbox = det
            
            x1, y1, x2, y2 = map(int, bbox)
            
            # 바운딩 박스 크롭
            cropped = image_rgb[y1:y2, x1:x2]
            
            if cropped.size == 0:
                continue
            
            # 목 분류 결과에서 해당 인덱스의 결과 가져오기
            order_name = "Unknown"
            if idx < len(order_results) and order_results[idx].get('classification'):
                order_classification = order_results[idx]['classification']
                if order_classification:
                    order_name = order_classification[0]['class_name']
                    print(f"목 분류 결과 #{idx}: {order_name} (신뢰도: {order_classification[0].get('confidence', 0.0):.3f})")
            
            # 계층적 분류 수행
            hierarchical_result = self.classify_hierarchical(cropped, order_name)
            
            # 크롭 이미지 저장 (선택사항)
            crop_path = None
            if crop_dir:
                crop_dir = Path(crop_dir)
                crop_dir.mkdir(parents=True, exist_ok=True)
                crop_path = crop_dir / f"crop_{idx:03d}.jpg"
                cropped_pil = Image.fromarray(cropped)
                cropped_pil.save(str(crop_path))
            
            # 기존 형식과 호환되도록 결과 변환
            classification = []
            
            # 목 정보 추가
            classification.append({
                'class': 0,
                'class_name': order_name,
                'confidence': order_results[idx]['classification'][0]['confidence'] if idx < len(order_results) and order_results[idx].get('classification') else 0.0,
                'level': 'order'
            })
            
            # 과 정보 추가
            if hierarchical_result['family']:
                classification.append({
                    'class': 1,
                    'class_name': hierarchical_result['family'],
                    'confidence': hierarchical_result['confidence_scores'].get('family', 0.0),
                    'level': 'family'
                })
            
            # 속 정보 추가
            if hierarchical_result['genus']:
                classification.append({
                    'class': 2,
                    'class_name': hierarchical_result['genus'],
                    'confidence': hierarchical_result['confidence_scores'].get('genus', 0.0),
                    'level': 'genus'
                })
            
            # 종 정보 추가
            if hierarchical_result['species']:
                classification.append({
                    'class': 3,
                    'class_name': hierarchical_result['species'],
                    'confidence': hierarchical_result['confidence_scores'].get('species', 0.0),
                    'level': 'species'
                })
                
                # 추가 후보 종들
                if 'species_candidates' in hierarchical_result:
                    for i, candidate in enumerate(hierarchical_result['species_candidates'][1:], 1):
                        classification.append({
                            'class': 3 + i,
                            'class_name': f"{candidate['name']} (후보 #{i+1})",
                            'confidence': candidate['confidence'],
                            'level': 'species_candidate'
                        })
            
            classification_results.append({
                'detection_idx': idx,
                'bbox': bbox,
                'classification': classification,
                'hierarchical_result': hierarchical_result,
                'crop_path': str(crop_path) if crop_path else None
            })
        
        return classification_results
