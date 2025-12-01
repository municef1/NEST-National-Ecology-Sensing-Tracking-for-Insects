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


class InsectClassifier:
    """곤충 목 분류 클래스 - EfficientNet-B4 사용"""
    
    def __init__(self, model_path=None, classes_path=None, device=None):
        """
        초기화

        Args:
            model_path: 모델 가중치 경로 (.pth 파일)
            classes_path: 클래스 정보 JSON 파일 경로
            device: 사용할 디바이스 ('cuda' or 'cpu')
        """
        self.device = device if device else ('cuda' if torch.cuda.is_available() else 'cpu')
        
        # 기본 경로 설정
        if model_path is None:
            base_dir = Path(__file__).parent
            # order 폴더에서 찾기
            model_path = base_dir / "models" / "order" / "best_classifier.pth"
            if not model_path.exists():
                model_path = base_dir / "models" / "order" / "best_detected_order_classifier.pth"
            if not model_path.exists():
                model_path = base_dir / "models" / "best_classifier.pth"
        
        if classes_path is None:
            base_dir = Path(__file__).parent
            # order 폴더에서 찾기
            classes_path = base_dir / "models" / "order" / "detected_order_classes.json"
            if not classes_path.exists():
                classes_path = base_dir / "models" / "detected_order_classes.json"
        
        self.model_path = Path(model_path)
        self.classes_path = Path(classes_path)
        
        # 클래스 정보 로드
        self.order_to_idx = {}
        self.idx_to_order = {}
        self.load_classes()
        
        # 모델 로드
        self.model = None
        self.load_model()
        
        # 전처리 설정
        self.transform = A.Compose([
            A.Resize(224, 224),
            A.Normalize(mean=(0.485, 0.456, 0.406), std=(0.229, 0.224, 0.225), max_pixel_value=255.0),
            ToTensorV2()
        ])
    
    def load_classes(self):
        """클래스 정보 로드"""
        try:
            if self.classes_path.exists():
                with open(self.classes_path, 'r', encoding='utf-8') as f:
                    self.order_to_idx = json.load(f)
                self.idx_to_order = {v: k for k, v in self.order_to_idx.items()}
                print(f"클래스 정보 로드: {len(self.order_to_idx)}개 목")
            else:
                print(f"경고: 클래스 파일이 없습니다: {self.classes_path}")
                # 기본 클래스 설정
                self.order_to_idx = {"Unknown": 0}
                self.idx_to_order = {0: "Unknown"}
        except Exception as e:
            print(f"클래스 로드 오류: {str(e)}")
            self.order_to_idx = {"Unknown": 0}
            self.idx_to_order = {0: "Unknown"}
    
    def load_model(self):
        """모델 로드"""
        try:
            num_classes = len(self.order_to_idx)
            self.model = timm.create_model('efficientnet_b4', pretrained=True, num_classes=num_classes)
            
            if self.model_path.exists():
                print(f"모델 로드: {self.model_path}")
                self.model.load_state_dict(torch.load(str(self.model_path), map_location=self.device))
            else:
                print(f"경고: 모델 파일이 없습니다: {self.model_path}")
                print("사전 훈련된 EfficientNet-B4를 사용합니다.")
            
            self.model = self.model.to(self.device)
            self.model.eval()
            
        except Exception as e:
            print(f"모델 로드 중 오류: {str(e)}")
            # 기본 모델 사용
            self.model = timm.create_model('efficientnet_b4', pretrained=True, num_classes=len(self.order_to_idx))
            self.model = self.model.to(self.device)
            self.model.eval()
    
    def classify(self, image_path, top_k=5, use_tta=True):
        """
        이미지에서 곤충 목 분류

        Args:
            image_path: 입력 이미지 경로 또는 PIL Image
            top_k: 상위 k개 결과 반환
            use_tta: TTA(Test Time Augmentation) 사용 여부

        Returns:
            dict: 분류 결과
        """
        try:
            # 이미지 로드
            if isinstance(image_path, (str, Path)):
                # 한글 경로 지원
                with open(str(image_path), 'rb') as f:
                    image_data = f.read()
                image_array = np.frombuffer(image_data, np.uint8)
                image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
                image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            elif hasattr(image_path, 'convert'):
                # PIL Image인 경우
                image = np.array(image_path.convert('RGB'))
            else:
                # numpy array인 경우
                image = image_path
            
            if use_tta:
                predictions = self._classify_with_tta(image)
            else:
                predictions = self._classify_single(image)
            
            # Top-K 예측 정렬
            predictions = sorted(predictions, key=lambda x: x['confidence'], reverse=True)[:top_k]
            
            return {
                'order': predictions[0]['order'] if predictions else 'Unknown',
                'confidence': predictions[0]['confidence'] if predictions else 0.0,
                'top_k': predictions
            }
        
        except Exception as e:
            print(f"분류 오류: {e}")
            return {
                'order': 'Unknown',
                'confidence': 0.0,
                'top_k': []
            }
    
    def _classify_single(self, image):
        """단일 이미지 분류"""
        transformed = self.transform(image=image)
        input_tensor = transformed['image'].unsqueeze(0).to(self.device)
        
        with torch.no_grad():
            outputs = self.model(input_tensor)
            probabilities = torch.softmax(outputs, 1)[0]
            
            predictions = []
            for idx, prob in enumerate(probabilities):
                order_name = self.idx_to_order.get(idx, f"Class_{idx}")
                predictions.append({
                    'order': order_name,
                    'confidence': prob.item()
                })
            
            return predictions
    
    def _classify_with_tta(self, image):
        """TTA를 적용한 분류"""
        # TTA 변환 정의
        tta_transforms = [
            A.Compose([A.Resize(224, 224), A.Normalize(mean=(0.485, 0.456, 0.406), std=(0.229, 0.224, 0.225)), ToTensorV2()]),
            A.Compose([A.HorizontalFlip(p=1.0), A.Resize(224, 224), A.Normalize(mean=(0.485, 0.456, 0.406), std=(0.229, 0.224, 0.225)), ToTensorV2()]),
            A.Compose([A.Rotate(limit=15, p=1.0), A.Resize(224, 224), A.Normalize(mean=(0.485, 0.456, 0.406), std=(0.229, 0.224, 0.225)), ToTensorV2()]),
        ]
        
        all_predictions = []
        
        for transform in tta_transforms:
            try:
                transformed = transform(image=image)
                input_tensor = transformed['image'].unsqueeze(0).to(self.device)
                
                with torch.no_grad():
                    outputs = self.model(input_tensor)
                    probabilities = torch.softmax(outputs, 1)[0]
                    all_predictions.append(probabilities.cpu().numpy())
            except:
                continue
        
        if not all_predictions:
            return self._classify_single(image)
        
        # 예측 결과 평균
        avg_predictions = np.mean(all_predictions, axis=0)
        
        predictions = []
        for idx, prob in enumerate(avg_predictions):
            order_name = self.idx_to_order.get(idx, f"Class_{idx}")
            predictions.append({
                'order': order_name,
                'confidence': float(prob)
            })
        
        return predictions
    
    def classify_detections(self, image_path, detections, crop_dir=None):
        """
        탐지된 곤충들을 크롭하여 각각 분류

        Args:
            image_path: 원본 이미지 경로
            detections: 탐지 결과 리스트
            crop_dir: 크롭 이미지 저장 디렉토리

        Returns:
            list: 각 탐지에 대한 분류 결과
        """
        # 원본 이미지 로드
        with open(str(image_path), 'rb') as f:
            image_data = f.read()
        image_array = np.frombuffer(image_data, np.uint8)
        image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        classification_results = []
        
        for idx, det in enumerate(detections):
            # detections가 dict인지 list인지 확인
            if isinstance(det, dict):
                # 정규화된 좌표인 경우 픽셀 좌표로 변환
                if 'bbox' in det:
                    bbox = det['bbox']
                    if isinstance(bbox, dict) and 'x' in bbox:
                        # {x, y, width, height} 형식
                        h, w = image.shape[:2]
                        x1 = int(bbox['x'] * w)
                        y1 = int(bbox['y'] * h)
                        x2 = int((bbox['x'] + bbox['width']) * w)
                        y2 = int((bbox['y'] + bbox['height']) * h)
                    else:
                        # [x1, y1, x2, y2] 형식
                        x1, y1, x2, y2 = map(int, bbox[:4])
                else:
                    # det 자체가 bbox인 경우
                    if 'x' in det:
                        h, w = image.shape[:2]
                        x1 = int(det['x'] * w)
                        y1 = int(det['y'] * h)
                        x2 = int((det['x'] + det['width']) * w)
                        y2 = int((det['y'] + det['height']) * h)
                    else:
                        x1, y1, x2, y2 = map(int, [det.get('x1', 0), det.get('y1', 0), det.get('x2', 100), det.get('y2', 100)])
            else:
                # list 형식인 경우
                if len(det) >= 4:
                    x1, y1, x2, y2 = map(int, det[:4])
                else:
                    continue
            
            # 바운딩 박스 크롭
            cropped = image_rgb[y1:y2, x1:x2]
            
            if cropped.size == 0:
                continue
            
            # 분류 수행
            classification_result = self.classify(cropped, top_k=3, use_tta=True)
            
            # 크롭 이미지 저장 (선택사항)
            crop_path = None
            if crop_dir:
                crop_dir = Path(crop_dir)
                crop_dir.mkdir(parents=True, exist_ok=True)
                crop_path = crop_dir / f"crop_{idx:03d}.jpg"
                cropped_pil = Image.fromarray(cropped)
                cropped_pil.save(str(crop_path))
            
            # 결과 형식을 기존과 호환되도록 변환
            classification = []
            for pred in classification_result['top_k']:
                classification.append({
                    'class': list(self.order_to_idx.keys()).index(pred['order']) if pred['order'] in self.order_to_idx else 0,
                    'class_name': pred['order'],
                    'confidence': pred['confidence']
                })
            
            classification_results.append({
                'detection_idx': idx,
                'bbox': [x1, y1, x2, y2],
                'classification': classification,
                'crop_path': str(crop_path) if crop_path else None
            })
        
        return classification_results