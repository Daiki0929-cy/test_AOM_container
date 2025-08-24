import time
import requests
import os
import json
import logging
from datetime import datetime
import threading

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AlarmState:
    def __init__(self):
        self.machine_id = os.getenv('MACHINE_ID', 'surveillance')
        self.state_name = os.getenv('STATE_NAME', 'alarm')
        self.event_bus_url = os.getenv('EVENT_BUS_URL', 'http://localhost:5000')
        self.alarm_active = True
        self.alarm_thread = None
        
    def run(self):
        """アラーム状態実行"""
        logger.critical("🚨 ALARM ACTIVATED - SECURITY BREACH DETECTED! 🚨")
        
        # アラーム音・ライト制御をシミュレーション
        self.alarm_thread = threading.Thread(target=self._run_alarm_signals)
        self.alarm_thread.daemon = True
        self.alarm_thread.start()
        
        # 通知送信
        self._send_notifications()
        
        # 解除イベントを待機（実際の実装では外部からの解除イベントを受信）
        # このシミュレーションでは10秒後に自動解除
        time.sleep(10)
        
        logger.info("Alarm auto-disarm after 10 seconds (simulation)")
        self._disarm_alarm()

    def _run_alarm_signals(self):
        """アラーム信号実行"""
        while self.alarm_active:
            logger.warning("🔊 ALARM SIGNAL ACTIVE 🔴")
            time.sleep(1)

    def _send_notifications(self):
        """緊急通知送信"""
        notifications = [
            "Security breach detected at camera location",
            "Unauthorized person detected in restricted area", 
            "Immediate security response required"
        ]
        
        for notification in notifications:
            logger.critical(f"📱 NOTIFICATION: {notification}")
            # 実際の実装ではメール、SMS、プッシュ通知等を送信

    def _disarm_alarm(self):
        """アラーム解除"""
        self.alarm_active = False
        
        self._send_transition_event('disarm_alarm', {
            'disarmed_by': 'auto_timeout',
            'alarm_duration': 10,
            'timestamp': datetime.now().isoformat()
        })
        
        logger.info("🟢 Alarm disarmed - returning to normal operation")

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
    alarm_state = AlarmState()
    alarm_state.run()