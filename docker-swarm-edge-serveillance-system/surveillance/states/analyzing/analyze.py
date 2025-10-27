import time
import requests
import os
import json
import numpy as np
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AnalyzingState:
    def __init__(self):
        self.machine_id = os.getenv('MACHINE_ID', 'surveillance')
        self.state_name = os.getenv('STATE_NAME', 'analyzing')
        self.event_bus_url = os.getenv('EVENT_BUS_URL', 'http://localhost:5000')
        self.analysis_duration = 2.0  # 2秒の分析時間
        
    def run(self):
        """脅威分析処理実行"""
        logger.info(f"Starting threat analysis for {self.machine_id}")
        
        # 分析処理シミュレーション
        time.sleep(self.analysis_duration)
        
        try:
            # 脅威分析実行
            threat_detected = self._simulate_threat_analysis()
            
            if threat_detected:
                # 脅威検出時
                self._send_transition_event('threat_detected', {
                    'threat_level': 'HIGH',
                    'threat_type': 'unknown_person',
                    'confidence': 0.92,
                    'timestamp': datetime.now().isoformat()
                })
                logger.warning("THREAT DETECTED - Activating alarm!")
            else:
                # 脅威なし
                self._send_transition_event('no_threat', {
                    'result': 'authorized_person',
                    'confidence': 0.88,
                    'timestamp': datetime.now().isoformat()
                })
                logger.info("No threat detected - returning to disarmed state")
                
        except Exception as e:
            logger.error(f"Analysis error: {str(e)}")
            # エラー時は安全のため脅威として扱う
            self._send_transition_event('threat_detected', {
                'threat_level': 'UNKNOWN',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            })

    def _simulate_threat_analysis(self):
        """脅威分析シミュレーション"""
        # 顔認証、行動分析等をシミュレーション
        # 実際の実装では機械学習モデルを使用
        
        # 30%の確率で脅威と判定
        return np.random.random() > 0.7

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
    analyzing_state = AnalyzingState()
    analyzing_state.run()