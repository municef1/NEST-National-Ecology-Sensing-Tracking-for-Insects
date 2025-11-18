import torch
import torch.nn as nn
import timm
import json
import cv2
import numpy as np
import albumentations as A
from albumentations.pytorch.transforms import ToTensorV2

class OrderClassifier:
    def __init__(self, model_path, classes_path='detected_order_classes.json'):
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        
        # 클래스 정보 로드
        with open(classes_path, 'r', encoding='utf-8') as f:
            self.order_to_idx = json.load(f)
        self.idx_to_order = {v: k for k, v in self.order_to_idx.items()}
        
        # 모델 로드
        self.model = timm.create_model('efficientnet_b4', pretrained=True, num_classes=len(self.order_to_idx))
        self.model.load_state_dict(torch.load(model_path, map_location=self.device))
        self.model = self.model.to(self.device)
        self.model.eval()
        
        # 전처리
        self.transform = A.Compose([
            A.Resize(224, 224),
            A.Normalize(mean=(0.485, 0.456, 0.406), std=(0.229, 0.224, 0.225), max_pixel_value=255.0),
            ToTensorV2()
        ])
        
        print(f"목 분류 모델 로드 완료: {len(self.order_to_idx)}개 클래스")
    
    def classify(self, image_path, top_k=5, use_tta=True):
        """이미지를 목 단위로 분류 (TTA 지원)"""
        try:
            # 이미지 로드 (한글 경로 지원)
            with open(image_path, 'rb') as f:
                image_data = f.read()
            image_array = np.frombuffer(image_data, np.uint8)
            image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            
            if use_tta:
                # TTA 적용 분류
                predictions = self._classify_with_tta(image)
            else:
                # 기본 분류
                predictions = self._classify_single(image)
            
            # Top-K 예측 정렬
            predictions = sorted(predictions, key=lambda x: x['confidence'], reverse=True)[:top_k]
            
            return {
                'order': predictions[0]['order'],
                'confidence': predictions[0]['confidence'],
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
                order_name = self.idx_to_order[idx]
                predictions.append({
                    'order': order_name,
                    'confidence': prob.item()
                })
            
            return predictions
    
    def _classify_with_tta(self, image):
        """
TTA를 적용한 분류 (회전, 뒤집기, 스케일 변환)
        """
        import albumentations as A
        
        # TTA 변환 정의
        tta_transforms = [
            A.Compose([A.Resize(224, 224), A.Normalize(mean=(0.485, 0.456, 0.406), std=(0.229, 0.224, 0.225)), ToTensorV2()]),  # 원본
            A.Compose([A.HorizontalFlip(p=1.0), A.Resize(224, 224), A.Normalize(mean=(0.485, 0.456, 0.406), std=(0.229, 0.224, 0.225)), ToTensorV2()]),  # 수평 뒤집기
            A.Compose([A.Rotate(limit=15, p=1.0), A.Resize(224, 224), A.Normalize(mean=(0.485, 0.456, 0.406), std=(0.229, 0.224, 0.225)), ToTensorV2()]),  # 회전
            A.Compose([A.RandomScale(scale_limit=0.1, p=1.0), A.Resize(224, 224), A.Normalize(mean=(0.485, 0.456, 0.406), std=(0.229, 0.224, 0.225)), ToTensorV2()]),  # 스케일
        ]
        
        all_predictions = []
        
        # 각 변환에 대해 추론
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
            order_name = self.idx_to_order[idx]
            predictions.append({
                'order': order_name,
                'confidence': float(prob)
            })
        
        return predictions