import time
import requests
import cv2
import numpy as np
import os
import json
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CaptureState:
    def __init__(self):
        self.machine_id = os.getenv('MACHINE_ID', 'detector')
        self.state_name = os.getenv('STATE_NAME', 'capturing')
        self.event_bus_url = os.getenv('EVENT_BUS_URL', 'http://localhost:5000')
        self.capture_interval = 0.5  # 500ms
        
    def run(self):
        """画像キャプチャ処理実行"""
        logger.info(f"Starting capture state for {self.machine_id}")
        
        while True:
            try:
                # シミュレーション用の画像生成（実際にはカメラから取得）
                image = self._simulate_camera_capture()
                
                # 画像保存
                timestamp = datetime.now().isoformat()
                image_path = f"/tmp/captured_image_{timestamp.replace(':', '-')}.jpg"
                cv2.imwrite(image_path, image)
                
                # 状態遷移イベント送信
                self._send_transition_event('image_captured', {
                    'image_path': image_path,
                    'timestamp': timestamp,
                    'image_size': image.shape
                })
                
                logger.info(f"Image captured and saved: {image_path}")
                
                # 次の遷移を待つ（processing状態への遷移後に再開）
                time.sleep(self.capture_interval)
                
            except Exception as e:
                logger.error(f"Capture error: {str(e)}")
                time.sleep(1)

    def _simulate_camera_capture(self):
        """カメラキャプチャシミュレーション"""
        # 640x480のランダム画像生成（実際の実装ではカメラAPIを使用）
        height, width = 480, 640
        image = np.random.randint(0, 255, (height, width, 3), dtype=np.uint8)
        
        # 時々人を模した矩形を描画（人物検出テスト用）
        if np.random.random() > 0.7:  # 30%の確率で人物あり
            cv2.rectangle(image, (200, 150), (400, 350), (0, 255, 0), 2)
            
        return image

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
    capture_state = CaptureState()
    capture_state.run()