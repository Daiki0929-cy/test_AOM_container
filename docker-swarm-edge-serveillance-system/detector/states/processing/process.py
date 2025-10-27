import cv2
import numpy as np
from ultralytics import YOLO
import requests
import os
import time
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ProcessingState:
    def __init__(self):
        self.machine_id = os.getenv('MACHINE_ID', 'detector')
        self.state_name = os.getenv('STATE_NAME', 'processing')
        self.event_bus_url = os.getenv('EVENT_BUS_URL', 'http://localhost:5000')
        self.processing_timeout = 0.5
        self.confidence_threshold = 0.5
        
        # YOLOv8-nanoモデルの初期化
        model_path = os.getenv('MODEL_PATH', 'yolov8n.pt')
        self.model = YOLO(model_path)
        logger.info("YOLOv8 model loaded successfully")
        
    def run(self):
        """人物検出処理実行"""
        logger.info(f"Starting processing state for {self.machine_id}")
        
        # 画像の取得（実際には前の状態から受け取る）
        image_path = os.getenv('IMAGE_PATH', '/tmp/captured_image.jpg')
        
        if not os.path.exists(image_path):
            logger.error(f"Image not found: {image_path}")
            self._send_transition_event('processing_error', {
                'error': 'image_not_found',
                'timestamp': datetime.now().isoformat()
            })
            return
        
        start_time = time.time()
        
        try:
            # 人物検出実行
            detection_result = self._detect_person(image_path)
            
            processing_time = time.time() - start_time
            
            if processing_time > self.processing_timeout:
                self._send_transition_event('processing_timeout', {
                    'timeout_duration': processing_time,
                    'timestamp': datetime.now().isoformat()
                })
                logger.warning(f"Processing timeout: {processing_time:.3f}s")
                return
            
            if detection_result['person_detected']:
                # 人物検出時
                self._send_transition_event('person_detected', {
                    'detection_confidence': detection_result['max_confidence'],
                    'timestamp': datetime.now().isoformat(),
                    'person_count': detection_result['person_count'],
                    'processing_time': processing_time,
                    'bounding_boxes': detection_result['bounding_boxes']
                })
                logger.info(f"Person detected (count: {detection_result['person_count']}, "
                          f"confidence: {detection_result['max_confidence']:.2f})")
            else:
                # 人物未検出
                self._send_transition_event('processing_complete', {
                    'result': 'no_person',
                    'timestamp': datetime.now().isoformat(),
                    'processing_time': processing_time
                })
                logger.info("No person detected")
                
        except Exception as e:
            logger.error(f"Processing error: {str(e)}")
            self._send_transition_event('processing_error', {
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            })

    def _detect_person(self, image_path: str) -> dict:
        """YOLOv8による人物検出"""
        # 画像読み込み
        image = cv2.imread(image_path)
        
        # 推論実行（person class = 0）
        results = self.model(image, classes=[0], conf=self.confidence_threshold, verbose=False)
        
        person_count = 0
        max_confidence = 0.0
        bounding_boxes = []
        
        # 検出結果の解析
        for result in results:
            boxes = result.boxes
            person_count = len(boxes)
            
            for box in boxes:
                confidence = float(box.conf[0])
                max_confidence = max(max_confidence, confidence)
                
                # バウンディングボックスの座標
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                bounding_boxes.append({
                    'x1': int(x1),
                    'y1': int(y1),
                    'x2': int(x2),
                    'y2': int(y2),
                    'confidence': confidence
                })
        
        return {
            'person_detected': person_count > 0,
            'person_count': person_count,
            'max_confidence': max_confidence,
            'bounding_boxes': bounding_boxes
        }

    def _send_transition_event(self, transition_name: str, event_data: dict):
        """イベントバスに遷移イベント送信"""
        try:
            payload = {
                'machine_id': self.machine_id,
                'transition_name': transition_name,
                'event_data': event_data
            }
            
            response = requests.post(
                f"{self.event_bus_url}/transition",
                json=payload,
                timeout=5
            )
            
            if response.status_code == 200:
                logger.info(f"Transition event sent: {transition_name}")
            else:
                logger.error(f"Failed to send transition event: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Error sending transition event: {str(e)}")

if __name__ == '__main__':
    processing_state = ProcessingState()
    processing_state.run()