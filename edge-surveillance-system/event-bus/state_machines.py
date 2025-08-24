import yaml
from datetime import datetime
from typing import Dict, List, Optional, Tuple

class State:
    def __init__(self, name: str, container_image: str):
        self.name = name
        self.container_image = container_image
        self.is_active = False
        self.activated_at = None
        
    def activate(self):
        self.is_active = True
        self.activated_at = datetime.now()
        
    def deactivate(self):
        self.is_active = False

class Transition:
    def __init__(self, name: str, from_state: str, to_state: str, trigger_event: str):
        self.name = name
        self.from_state = from_state
        self.to_state = to_state
        self.trigger_event = trigger_event

class StateMachine:
    def __init__(self, machine_id: str, config: dict):
        self.machine_id = machine_id
        self.states = {}
        self.transitions = {}
        self.current_state = None
        
        # 設定から状態を構築
        for state_name, state_config in config['states'].items():
            self.states[state_name] = State(
                name=state_name,
                container_image=state_config['container_image']
            )
        
        # 遷移を構築
        for trans_config in config['transitions']:
            transition = Transition(
                name=trans_config['name'],
                from_state=trans_config['from_state'],
                to_state=trans_config['to_state'],
                trigger_event=trans_config.get('trigger_event', '')
            )
            self.transitions[transition.name] = transition
        
        # 初期状態設定
        initial_state_name = config['initial_state']
        self.current_state = self.states[initial_state_name]
        self.current_state.activate()

    def transition_to(self, transition_name: str, event_data: dict = None) -> Tuple[State, State]:
        """状態遷移実行"""
        if transition_name not in self.transitions:
            raise ValueError(f"Unknown transition: {transition_name}")
            
        transition = self.transitions[transition_name]
        
        if self.current_state.name != transition.from_state:
            raise ValueError(
                f"Invalid transition {transition_name} from {self.current_state.name}"
            )
        
        # 状態切り替え
        old_state = self.current_state
        old_state.deactivate()
        
        new_state = self.states[transition.to_state]
        new_state.activate()
        self.current_state = new_state
        
        return old_state, new_state

    def get_current_state(self) -> State:
        return self.current_state
        
    def can_transition(self, transition_name: str) -> bool:
        """遷移可能かチェック"""
        if transition_name not in self.transitions:
            return False
        transition = self.transitions[transition_name]
        return self.current_state.name == transition.from_state

class StateMachineManager:
    def __init__(self):
        self.machines = {}
        self.load_configurations()
        
    def load_configurations(self):
        """設定ファイルからマシン設定読み込み"""
        # Detector machine
        with open('/config/detector-config.yaml', 'r') as f:
            detector_config = yaml.safe_load(f)
        self.machines['detector'] = StateMachine('detector', detector_config)
        
        # Surveillance machine  
        with open('/config/surveillance-config.yaml', 'r') as f:
            surveillance_config = yaml.safe_load(f)
        self.machines['surveillance'] = StateMachine('surveillance', surveillance_config)

    def initialize_machines(self):
        """マシン初期化"""
        for machine in self.machines.values():
            # 既に初期状態に設定済み
            pass
            
    def execute_transition(self, machine_id: str, transition_name: str, 
                         event_data: dict = None) -> Tuple[State, State]:
        """遷移実行"""
        if machine_id not in self.machines:
            raise ValueError(f"Unknown machine: {machine_id}")
            
        machine = self.machines[machine_id]
        return machine.transition_to(transition_name, event_data)
    
    def get_machine(self, machine_id: str) -> StateMachine:
        return self.machines[machine_id]
        
    def get_machine_ids(self) -> List[str]:
        return list(self.machines.keys())
        
    def can_handle_event(self, machine_id: str, event: dict) -> bool:
        """イベント処理可能かチェック"""
        machine = self.machines[machine_id]
        event_name = event['name']
        
        # 現在の状態から処理可能な遷移を探す
        current_state = machine.get_current_state()
        for transition in machine.transitions.values():
            if (transition.from_state == current_state.name and 
                transition.trigger_event == event_name):
                return True
        return False
        
    def get_transition_for_event(self, machine_id: str, event: dict) -> Optional[str]:
        """イベントに対応する遷移名取得"""
        machine = self.machines[machine_id]
        event_name = event['name']
        current_state = machine.get_current_state()
        
        for transition in machine.transitions.values():
            if (transition.from_state == current_state.name and 
                transition.trigger_event == event_name):
                return transition.name
        return None