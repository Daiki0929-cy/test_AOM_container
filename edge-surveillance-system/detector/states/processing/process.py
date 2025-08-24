import cv2
import numpy as np
import requests
import os
import json
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
        self.processing_timeout = 0.5  # 500ms timeout
        
    def run(self):
        """人物検出処理実行"""
        logger.info(f"Starting processing state for {self.machine_id}")
        
        # 処理開始（実際には前の状態から画像パスを受け取る）
        start_time = time.time()
        
        while time.time() - start_time < self.processing_timeout:
            try:
                # シミュレーション用の画像処理
                person_detected = self._simulate_person_detection()
                
                if person_detected:
                    # 人物検出時
                    self._send_transition_event('person_detected', {
                        'detection_confidence': 0.85,
                        'timestamp': datetime.now().isoformat(),
                        'person_count': 1
                    })
                    logger.info("Person detected - transitioning to next processing")
                    return
                else:
                    # 人物未検出
                    self._send_transition_event('processing_complete', {
                        'result': 'no_person',
                        'timestamp': datetime.now().isoformat()
                    })
                    logger.info("No person detected - returning to capture")
                    return
                    
            except Exception as e:
                logger.error(f"Processing error: {str(e)}")
                
        # タイムアウト時
        self._send_transition_event('processing_timeout', {
            'timeout_duration': self.processing_timeout,
            'timestamp': datetime.now().isoformat()
        })
        logger.info("Processing timeout - returning to capture")

    def _simulate_person_detection(self):
        """人物検出シミュレーション"""
        # 簡単なシミュレーション（実際にはYOLOやOpenPoseなどを使用）
        return np.random.random() > 0.6  # 40%の確率で人物検出

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