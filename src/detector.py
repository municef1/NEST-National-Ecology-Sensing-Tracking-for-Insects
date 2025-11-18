"""
곤충 탐지 추론 모듈

학습된 YOLOv8 모델을 사용하여 이미지에서 곤충을 탐지합니다.
"""

import os
import platform
from pathlib import Path
import cv2
import numpy as np
from ultralytics import YOLO

PLATFORM = platform.system()


class InsectDetector:
    """곤충 탐지 클래스"""
    
    def __init__(self, model_path=None, conf_threshold=0.25, iou_threshold=0.45):
        """
        초기화
        
        Args:
            model_path: 모델 가중치 경로
            conf_threshold: 신뢰도 임계값
            iou_threshold: NMS IoU 임계값
        """
        self.conf_threshold = conf_threshold
        self.iou_threshold = iou_threshold
        
        # 기본 모델 경로 설정
        if model_path is None:
            base_dir = Path(__file__).parent.parent
            model_path = base_dir / "models" / "detection" / "best_detector.pt"
        
        self.model_path = Path(model_path)
        
        # 모델 로드
        self.model = None
        self.load_model()
    
    def load_model(self):
        """모델 로드"""
        if not self.model_path.exists():
            print(f"경고: 모델 파일이 존재하지 않습니다: {self.model_path}")
            print("기본 YOLOv8n 모델을 사용합니다.")
            self.model = YOLO('yolov8n.pt')
        else:
            print(f"모델 로드: {self.model_path}")
            self.model = YOLO(str(self.model_path))
    
    def detect(self, image_path, save_path=None, use_tta=False):
        """
        이미지에서 곤충 탐지
        
        Args:
            image_path: 입력 이미지 경로
            save_path: 결과 저장 경로 (None이면 저장 안 함)
        
        Returns:
            dict: 탐지 결과
                - detections: 탐지된 객체 리스트
                - image: 바운딩 박스가 그려진 이미지 (numpy array)
                - image_path: 저장된 이미지 경로
        """
        # 이미지 로드
        image = cv2.imread(str(image_path))
        if image is None:
            raise ValueError(f"이미지를 로드할 수 없습니다: {image_path}")
        
        # 기본 추론 (TTA 제거)
        results = self.model.predict(
            source=image,
            conf=self.conf_threshold,
            iou=self.iou_threshold,
            verbose=False
        )
        count = len(results[0].boxes.xyxy) if results[0].boxes is not None else 0
        print(f"탐지: {count}개")
        
        # 결과 파싱
        detections = []
        result = results[0]
        
        if result.boxes is not None and len(result.boxes) > 0:
            boxes = result.boxes.xyxy.cpu().numpy()  # [x1, y1, x2, y2]
            confidences = result.boxes.conf.cpu().numpy()
            classes = result.boxes.cls.cpu().numpy()
            
            for box, conf, cls in zip(boxes, confidences, classes):
                detections.append({
                    'bbox': box.tolist(),
                    'confidence': float(conf),
                    'class': int(cls),
                    'class_name': 'insect'
                })
        
        # 바운딩 박스 그리기 (이미지 크기에 적응)
        annotated_image = image.copy()
        h, w = image.shape[:2]
        
        # 이미지 크기에 따른 스케일 계산
        scale = min(h, w) / 640  # 640을 기준으로 스케일링
        box_thickness = max(1, int(3 * scale))
        font_scale = max(0.3, 0.6 * scale)
        font_thickness = max(1, int(2 * scale))
        
        if detections:
            for det in detections:
                box = det['bbox']
                conf = det['confidence']
                x1, y1, x2, y2 = map(int, box)
                
                # 적응적 박스 그리기
                cv2.rectangle(annotated_image, (x1, y1), (x2, y2), (0, 255, 0), box_thickness)
                
                # 적응적 텍스트
                label = f'{conf:.1%}'
                label_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, font_scale, font_thickness)[0]
                padding = max(5, int(10 * scale))
                cv2.rectangle(annotated_image, (x1, y1-label_size[1]-padding*2), (x1+label_size[0]+padding, y1), (0, 255, 0), -1)
                cv2.putText(annotated_image, label, (x1+padding//2, y1-padding), cv2.FONT_HERSHEY_SIMPLEX, font_scale, (0, 0, 0), font_thickness)
        
        # 결과 저장
        saved_path = None
        if save_path is not None:
            save_path = Path(save_path)
            save_path.parent.mkdir(parents=True, exist_ok=True)
            cv2.imwrite(str(save_path), annotated_image)
            saved_path = str(save_path)
        
        return {
            'detections': detections,
            'image': annotated_image,
            'image_path': saved_path,
            'count': len(detections)
        }
    
    def crop_detections(self, image_path, detections, output_dir):
        """
        탐지된 객체를 크롭하여 저장
        
        Args:
            image_path: 원본 이미지 경로
            detections: 탐지 결과 리스트
            output_dir: 크롭 이미지 저장 디렉토리
        
        Returns:
            list: 크롭된 이미지 경로 리스트
        """
        image = cv2.imread(str(image_path))
        if image is None:
            raise ValueError(f"이미지를 로드할 수 없습니다: {image_path}")
        
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        cropped_paths = []
        
        for idx, det in enumerate(detections):
            bbox = det['bbox']
            x1, y1, x2, y2 = map(int, bbox)
            
            # 바운딩 박스 크롭
            cropped = image[y1:y2, x1:x2]
            
            # 저장
            crop_path = output_dir / f"crop_{idx:03d}.jpg"
            cv2.imwrite(str(crop_path), cropped)
            cropped_paths.append(str(crop_path))
        
        return cropped_paths
    
    def _predict_with_tta(self, image):
        """
        슬라이딩 윈도우 TTA - 이미지를 패치로 나눠서 탐지
        """
        h, w = image.shape[:2]
        all_boxes = []
        all_confs = []
        all_classes = []
        
        # 1. 원본 전체 이미지 (반드시 보존)
        original_result = self.model.predict(source=image, conf=self.conf_threshold, iou=self.iou_threshold, verbose=False)[0]
        if original_result.boxes is not None:
            all_boxes.extend(original_result.boxes.xyxy.cpu().numpy())
            all_confs.extend(original_result.boxes.conf.cpu().numpy())
            all_classes.extend(original_result.boxes.cls.cpu().numpy())
        
        # 2. 슬라이딩 윈도우 (제한된 겹침)
        patch_size = min(h, w) // 2
        stride = patch_size // 2  # 50% 겹침만
        
        # 패치 수 제한 (4개만)
        patch_count = 0
        max_patches = 4
        
        for y in range(0, h - patch_size + 1, stride):
            for x in range(0, w - patch_size + 1, stride):
                if patch_count >= max_patches:
                    break
                    
                patch = image[y:y+patch_size, x:x+patch_size]
                
                # 낮은 threshold로 패치에서 추가 탐지
                patch_result = self.model.predict(source=patch, conf=self.conf_threshold*0.8, iou=self.iou_threshold, verbose=False)[0]
                
                if patch_result.boxes is not None:
                    for box, conf, cls in zip(patch_result.boxes.xyxy.cpu().numpy(), 
                                            patch_result.boxes.conf.cpu().numpy(), 
                                            patch_result.boxes.cls.cpu().numpy()):
                        # 좌표를 원본 이미지 기준으로 변환
                        adjusted_box = box.copy()
                        adjusted_box[0] += x
                        adjusted_box[1] += y
                        adjusted_box[2] += x
                        adjusted_box[3] += y
                        
                        # 이미지 범위 내 확인
                        if (adjusted_box[0] >= 0 and adjusted_box[1] >= 0 and 
                            adjusted_box[2] <= w and adjusted_box[3] <= h):
                            all_boxes.append(adjusted_box)
                            all_confs.append(conf)
                            all_classes.append(cls)
                
                patch_count += 1
            
            if patch_count >= max_patches:
                break
        
        # NMS로 중복 제거 후 새로운 결과 생성
        if all_boxes:
            import torch
            from torchvision.ops import nms
            
            boxes_tensor = torch.from_numpy(np.array(all_boxes, dtype=np.float32))
            scores_tensor = torch.from_numpy(np.array(all_confs, dtype=np.float32))
            
            # 원본 IoU threshold 사용
            keep = nms(boxes_tensor, scores_tensor, self.iou_threshold)
            
            if len(keep) > 0:
                final_boxes = boxes_tensor[keep]
                final_confs = scores_tensor[keep]
                final_classes = torch.from_numpy(np.array(all_classes, dtype=np.int64))[keep]
                
                # 새로운 결과 객체 생성
                class TTAResult:
                    def __init__(self, boxes, confs, classes):
                        self.boxes = TTABoxes(boxes, confs, classes)
                    
                    def plot(self):
                        # TTA 결과에 대해서도 적응적 바운딩 박스 그리기
                        img = image.copy()
                        h, w = image.shape[:2]
                        
                        # 이미지 크기에 따른 스케일 계산
                        scale = min(h, w) / 640
                        box_thickness = max(1, int(3 * scale))
                        font_scale = max(0.3, 0.6 * scale)
                        font_thickness = max(1, int(2 * scale))
                        
                        if self.boxes and len(self.boxes) > 0:
                            for box, conf in zip(self.boxes.xyxy, self.boxes.conf):
                                x1, y1, x2, y2 = map(int, box)
                                
                                # 적응적 박스 그리기
                                cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), box_thickness)
                                
                                # 적응적 텍스트
                                label = f'{conf:.1%}'
                                label_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, font_scale, font_thickness)[0]
                                padding = max(5, int(10 * scale))
                                cv2.rectangle(img, (x1, y1-label_size[1]-padding*2), (x1+label_size[0]+padding, y1), (0, 255, 0), -1)
                                cv2.putText(img, label, (x1+padding//2, y1-padding), cv2.FONT_HERSHEY_SIMPLEX, font_scale, (0, 0, 0), font_thickness)
                        return img
                
                class TTABoxes:
                    def __init__(self, boxes, confs, classes):
                        self.xyxy = boxes
                        self.conf = confs
                        self.cls = classes
                    
                    def __len__(self):
                        return len(self.xyxy)
                
                return [TTAResult(final_boxes, final_confs, final_classes)]
        
        # 원본 결과가 없으면 빈 결과 반환
        return [original_result]


def test_detector():
    """탐지기 테스트"""
    print("=" * 60)
    print("곤충 탐지기 테스트")
    print("=" * 60)
    
    detector = InsectDetector()
    
    # 테스트 이미지 경로 (실제 사용 시 수정 필요)
    test_image = Path(__file__).parent.parent / "uploads" / "test.jpg"
    
    if not test_image.exists():
        print(f"테스트 이미지가 없습니다: {test_image}")
        print("실제 이미지를 업로드하여 테스트하세요.")
        return
    
    # 탐지 수행
    result_dir = Path(__file__).parent.parent / "results"
    result_path = result_dir / "detected.jpg"
    
    results = detector.detect(test_image, save_path=result_path)
    
    print(f"\n탐지 결과:")
    print(f"- 탐지된 객체 수: {results['count']}")
    print(f"- 결과 이미지: {results['image_path']}")
    
    for idx, det in enumerate(results['detections']):
        print(f"\n객체 {idx + 1}:")
        print(f"  - 바운딩 박스: {det['bbox']}")
        print(f"  - 신뢰도: {det['confidence']:.4f}")
        print(f"  - 클래스: {det['class_name']}")


if __name__ == '__main__':
    test_detector()

