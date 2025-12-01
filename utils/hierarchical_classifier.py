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
import pandas as pd
class HierarchicalClassifier:
    """계층적 곤충 분류 시스템 (목 -> 과 -> 속 -> 종)"""
    
    def __init__(self, models_dir=None, device=None, csv_path='utils/data/insect_species_final.csv'):
        self.device = device if device else ('cuda' if torch.cuda.is_available() else 'cpu')
        
        if models_dir is None:
            models_dir = Path(__file__).parent / "models"
        
        self.models_dir = Path(models_dir)
        self.classifiers = {}
        
        self.transform = A.Compose([
            A.Resize(224, 224),
            A.Normalize(mean=(0.485, 0.456, 0.406), std=(0.229, 0.224, 0.225), max_pixel_value=255.0),
            ToTensorV2()
        ])
        
        # CSV 계층 정보 로드
        self.hierarchy_df = None
        csv_file = Path(csv_path)
        if csv_file.exists():
            try:
                self.hierarchy_df = pd.read_csv(csv_file, encoding='utf-8')
                print(f"✓ 계층 정보 로드: {len(self.hierarchy_df)}개 종")
            except Exception as e:
                print(f"⚠ CSV 로드 실패: {e}")
        
        self.load_classifiers()
    
    def load_classifiers(self):
        """초기화 시에는 아무것도 로드하지 않음 (지연 로딩)"""
        print("계층적 분류기 준비 완료 (지연 로딩 모드)")
    
    def _load_single_classifier(self, model_path, classes_path):
        try:
            with open(classes_path, 'r', encoding='utf-8') as f:
                class_to_idx = json.load(f)
            idx_to_class = {v: k for k, v in class_to_idx.items()}
            
            num_classes = len(class_to_idx)
            model = timm.create_model('resnet50', pretrained=False, num_classes=num_classes)
            
            state_dict = torch.load(str(model_path), map_location=self.device)
            model.load_state_dict(state_dict, strict=False)
            model = model.to(self.device)
            model.eval()
            
            return {'model': model, 'class_to_idx': class_to_idx, 'idx_to_class': idx_to_class}
        except Exception as e:
            print(f"분류기 로드 오류 ({model_path}): {str(e)}")
            return None
    
    def classify_hierarchical(self, image, order_name, top_k=3):
        result = {
            'order': order_name,
            'family': None,
            'genus': None,
            'species': None,
            'confidence_scores': {}
        }
        
        order_key = order_name.replace('목', '').lower()
        print(f"\n🔍 계층적 분류 시작: order={order_name}, order_key={order_key}")
        
        # 과 분류
        print(f"🔍 과 분류 시도: order_key={order_key}")
        family_classifier = self._find_classifier(order_key, 'family')
        if family_classifier:
            print(f"✓ 과 분류기 찾음: {family_classifier}")
            family_result = self._classify_single(image, family_classifier, top_k)
            # 사용 후 메모리 해제
            self._unload_classifier(family_classifier)
            
            if family_result:
                result['family'] = family_result[0]['name']
                result['confidence_scores']['family'] = family_result[0]['confidence']
                print(f"✓ 과 분류 완료: {result['family']} ({result['confidence_scores']['family']*100:.1f}%)")
                
                # 속 분류
                family_key = result['family'].replace('과', '').lower()
                print(f"🔍 속 분류 시도: family_key={family_key}")
                genus_classifier = self._find_classifier(family_key, 'genus')
                if genus_classifier:
                    print(f"✓ 속 분류기 찾음: {genus_classifier}")
                    genus_result = self._classify_single(image, genus_classifier, top_k)
                    self._unload_classifier(genus_classifier)
                    
                    if genus_result:
                        result['genus'] = genus_result[0]['name']
                        result['confidence_scores']['genus'] = genus_result[0]['confidence']
                        print(f"✓ 속 분류 완료: {result['genus']} ({result['confidence_scores']['genus']*100:.1f}%)")
                        
                        # 종 분류
                        genus_key = result['genus'].lower()
                        # 속명에서 "속" 제거 (예: "말벌속" -> "말벌")
                        genus_key = genus_key.replace('속', '').strip()
                        print(f"🔍 종 분류 시도: genus_key={genus_key}")
                        species_classifier = self._find_classifier(genus_key, 'species')
                        if species_classifier:
                            print(f"✓ 종 분류기 찾음: {species_classifier}")
                            species_result = self._classify_single(image, species_classifier, top_k)
                            self._unload_classifier(species_classifier)
                            
                            if species_result:
                                result['species'] = species_result[0]['name']
                                result['confidence_scores']['species'] = species_result[0]['confidence']
                                result['species_candidates'] = species_result
                                print(f"✓ 종 분류 완료: {result['species']} ({result['confidence_scores']['species']*100:.1f}%)")
                        else:
                            print(f"⚠ 종 분류기를 찾을 수 없습니다 (genus_key: {genus_key})")
                else:
                    print(f"⚠ 속 분류기를 찾을 수 없습니다 (family_key: {family_key})")
            else:
                print(f"⚠ 과 분류 결과가 없습니다")
        else:
            print(f"⚠ 과 분류기를 찾을 수 없습니다 (order_key: {order_key})")
        
        # 분류 결과 요약 출력
        if result['species']:
            print(f"✓ 계층적 분류 완료: {result['order']} > {result['family']} > {result['genus']} > {result['species']}")
        elif result['genus']:
            print(f"✓ 계층적 분류 완료: {result['order']} > {result['family']} > {result['genus']}")
        elif result['family']:
            print(f"✓ 계층적 분류 완료: {result['order']} > {result['family']}")
        else:
            print(f"✓ 계층적 분류 완료: {result['order']} (하위 분류 없음)")
        
        return result
    
    def _unload_classifier(self, classifier_key):
        """사용한 분류기 메모리 해제"""
        if classifier_key in self.classifiers:
            del self.classifiers[classifier_key]
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            print(f"🗑️  {classifier_key} 메모리 해제")
    
    def _find_classifier(self, key, level):
        """CSV 계층 정보를 참고하여 분류기를 찾고 로드"""
        # 이미 로드된 분류기 검색
        for classifier_name in self.classifiers:
            if key in classifier_name.lower() and level in classifier_name:
                return classifier_name
        
        level_dir = self.models_dir / level
        if not level_dir.exists():
            return None
        
        # 정확한 매칭: best_벌_family (O), best_대벌레_family (X)
        pattern = f"best_{key}_{level}_classifier"
        
        for model_file in level_dir.glob("best_*_classifier.pth"):
            if pattern in model_file.stem:
                json_name = model_file.stem.replace("best_", "").replace("_classifier", "") + "_classes.json"
                json_file = level_dir / json_name
                
                if json_file.exists():
                    classifier_key = model_file.stem
                    print(f"📥 {level} 분류기 로드: {model_file.name}")
                    self.classifiers[classifier_key] = self._load_single_classifier(model_file, json_file)
                    return classifier_key
        
        return None
    
    def _classify_single(self, image, classifier_key, top_k=3):
        if classifier_key not in self.classifiers:
            return None
        
        classifier = self.classifiers[classifier_key]
        if classifier is None:
            return None
        
        try:
            transformed = self.transform(image=image)
            input_tensor = transformed['image'].unsqueeze(0).to(self.device)
            
            with torch.no_grad():
                outputs = classifier['model'](input_tensor)
                probabilities = torch.softmax(outputs, 1)[0]
                top_probs, top_indices = torch.topk(probabilities, min(top_k, len(probabilities)))
            
            results = []
            for prob, idx in zip(top_probs, top_indices):
                class_name = classifier['idx_to_class'].get(idx.item(), f"Class_{idx.item()}")
                results.append({'name': class_name, 'confidence': prob.item()})
            
            return results
        except Exception as e:
            print(f"분류 오류 ({classifier_key}): {str(e)}")
            return None
    
    def classify_detections(self, image_path, detections, order_results, crop_dir=None):
        with open(str(image_path), 'rb') as f:
            image_data = f.read()
        image_array = np.frombuffer(image_data, np.uint8)
        image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        classification_results = []
        
        for idx, det in enumerate(detections):
            if isinstance(det, dict):
                bbox = det.get('bbox', det)
            else:
                bbox = det
            
            x1, y1, x2, y2 = map(int, bbox)
            cropped = image_rgb[y1:y2, x1:x2]
            
            if cropped.size == 0:
                continue
            
            order_name = "Unknown"
            if idx < len(order_results) and order_results[idx].get('classification'):
                order_classification = order_results[idx]['classification']
                if order_classification:
                    order_name = order_classification[0]['class_name']
            
            hierarchical_result = self.classify_hierarchical(cropped, order_name)
            
            crop_path = None
            if crop_dir:
                crop_dir = Path(crop_dir)
                crop_dir.mkdir(parents=True, exist_ok=True)
                crop_path = crop_dir / f"crop_{idx:03d}.jpg"
                Image.fromarray(cropped).save(str(crop_path))
            
            classification = []
            classification.append({
                'class': 0,
                'class_name': order_name,
                'confidence': order_results[idx]['classification'][0]['confidence'] if idx < len(order_results) and order_results[idx].get('classification') else 0.0,
                'level': 'order'
            })
            
            if hierarchical_result['family']:
                classification.append({
                    'class': 1,
                    'class_name': hierarchical_result['family'],
                    'confidence': hierarchical_result['confidence_scores'].get('family', 0.0),
                    'level': 'family'
                })
            
            if hierarchical_result['genus']:
                classification.append({
                    'class': 2,
                    'class_name': hierarchical_result['genus'],
                    'confidence': hierarchical_result['confidence_scores'].get('genus', 0.0),
                    'level': 'genus'
                })
            
            if hierarchical_result['species']:
                classification.append({
                    'class': 3,
                    'class_name': hierarchical_result['species'],
                    'confidence': hierarchical_result['confidence_scores'].get('species', 0.0),
                    'level': 'species'
                })
                
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
