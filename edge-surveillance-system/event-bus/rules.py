import yaml
import logging
from typing import List, Dict, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)

class TransitionRule:
    def __init__(self, rule_config: dict):
        self.source_machine = rule_config['source_machine']
        self.source_transition = rule_config['source_transition']
        self.target_machine = rule_config['target_machine']
        self.target_event = rule_config['target_event']
        self.conditions = rule_config.get('conditions', {})

class RulesEngine:
    def __init__(self):
        self.rules = []
        self.load_rules()
        
    def load_rules(self):
        """ルール設定ファイル読み込み"""
        try:
            with open('/config/transition-rules.yaml', 'r') as f:
                rules_config = yaml.safe_load(f)
                
            for rule_config in rules_config['rules']:
                self.rules.append(TransitionRule(rule_config))
                
            logger.info(f"Loaded {len(self.rules)} transition rules")
            
        except Exception as e:
            logger.error(f"Failed to load rules: {str(e)}")
            # デフォルトルールを設定
            self._load_default_rules()

    def _load_default_rules(self):
        """デフォルトルール設定"""
        default_rules = [
            {
                'source_machine': 'detector',
                'source_transition': 'person_detected',
                'target_machine': 'surveillance',
                'target_event': 'foundPersons',
                'conditions': {}
            }
        ]
        
        for rule_config in default_rules:
            self.rules.append(TransitionRule(rule_config))
            
        logger.info(f"Loaded {len(self.rules)} default rules")

    def get_triggered_events(self, machine_id: str, transition_name: str, 
                           event_data: dict) -> List[Tuple[str, dict]]:
        """遷移によってトリガーされるイベント取得"""
        triggered_events = []
        
        for rule in self.rules:
            if (rule.source_machine == machine_id and 
                rule.source_transition == transition_name):
                
                # 条件チェック
                if self._check_conditions(rule.conditions, event_data):
                    event = {
                        'name': rule.target_event,
                        'data': event_data,
                        'timestamp': datetime.now().isoformat(),
                        'source_machine': machine_id,
                        'source_transition': transition_name
                    }
                    triggered_events.append((rule.target_machine, event))
                    logger.info(f"Rule triggered: {rule.source_machine}.{rule.source_transition} -> {rule.target_machine}.{rule.target_event}")
                    
        return triggered_events
        
    def _check_conditions(self, conditions: dict, event_data: dict) -> bool:
        """条件チェック"""
        if not conditions:
            return True
            
        for key, expected_value in conditions.items():
            if key not in event_data:
                return False
                
            actual_value = event_data[key]
            
            # 比較演算子をサポート
            if isinstance(expected_value, str) and expected_value.startswith('>'):
                threshold = float(expected_value[1:])
                if not (isinstance(actual_value, (int, float)) and actual_value > threshold):
                    return False
            elif isinstance(expected_value, str) and expected_value.startswith('<'):
                threshold = float(expected_value[1:])
                if not (isinstance(actual_value, (int, float)) and actual_value < threshold):
                    return False
            elif actual_value != expected_value:
                return False
                
        return True