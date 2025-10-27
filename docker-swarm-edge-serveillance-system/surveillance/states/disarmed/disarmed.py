import time
import requests
import os
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DisarmedState:
    def __init__(self):
        self.machine_id = os.getenv('MACHINE_ID', 'surveillance')
        self.state_name = os.getenv('STATE_NAME', 'disarmed')
        self.event_bus_url = os.getenv('EVENT_BUS_URL', 'http://localhost:5000')
        
    def run(self):
        """待機状態実行"""
        logger.info(f"🟢 Surveillance system DISARMED - Standby mode active")
        
        # 待機状態で継続実行（実際にはイベント待ち）
        while True:
            try:
                # システム状態レポート（5分間隔）
                logger.info("📊 System status: DISARMED - Monitoring for activation events")
                
                # 実際の実装では外部イベントリスナーを実装
                # ここでは5分間隔での状態確認をシミュレーション
                time.sleep(300)  # 5分
                
            except Exception as e:
                logger.error(f"Error in disarmed state: {str(e)}")
                time.sleep(10)

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
    disarmed_state = DisarmedState()
    disarmed_state.run()