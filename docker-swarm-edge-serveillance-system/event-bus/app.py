from flask import Flask, request, jsonify
import docker
import yaml
import json
from datetime import datetime
import logging
from state_machines import StateMachineManager
from rules import RulesEngine
from container_manager_swarm import SwarmContainerManager  # 変更

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global instances
container_manager = None
rules_engine = None
state_machine_manager = None

def initialize_system():
    """システム初期化"""
    global container_manager, rules_engine, state_machine_manager
    
    container_manager = SwarmContainerManager()  # 変更
    rules_engine = RulesEngine()
    state_machine_manager = StateMachineManager()
    
    # ステートマシンを初期状態で開始
    state_machine_manager.initialize_machines()
    
    # 初期状態のコンテナを起動
    for machine_id in state_machine_manager.get_machine_ids():
        machine = state_machine_manager.get_machine(machine_id)
        initial_state = machine.get_current_state()
        container_manager.start_state_container(
            machine_id, initial_state.name, initial_state.container_image
        )

@app.route('/transition', methods=['POST'])
def process_transition():
    """状態遷移処理"""
    data = request.json
    machine_id = data['machine_id']
    transition_name = data['transition_name']
    event_data = data.get('event_data', {})
    
    try:
        # 現在の状態をログ出力（デバッグ用）
        machine = state_machine_manager.get_machine(machine_id)
        current_state = machine.get_current_state()
        logger.info(f"Attempting transition '{transition_name}' on machine '{machine_id}' from state '{current_state.name}'")
        
        # 利用可能な遷移を確認
        available_transitions = []
        for trans_name, transition in machine.transitions.items():
            if transition.from_state == current_state.name:
                available_transitions.append(trans_name)
        
        logger.info(f"Available transitions from '{current_state.name}': {available_transitions}")
        
        # 遷移が可能かチェック
        if not machine.can_transition(transition_name):
            error_msg = f"Invalid transition '{transition_name}' from state '{current_state.name}'. Available transitions: {available_transitions}"
            logger.error(error_msg)
            return jsonify({
                'status': 'error', 
                'message': error_msg,
                'current_state': current_state.name,
                'available_transitions': available_transitions
            }), 400
        
        # 状態遷移実行
        old_state, new_state = state_machine_manager.execute_transition(
            machine_id, transition_name, event_data
        )
        
        # コンテナ切り替え
        container_manager.transition_container(
            machine_id, old_state, new_state
        )
        
        # ルールに基づく他マシンへのイベント送信
        triggered_events = rules_engine.get_triggered_events(
            machine_id, transition_name, event_data
        )
        
        for target_machine, event in triggered_events:
            send_event_to_machine(target_machine, event)
            
        logger.info(f"Successful transition: {machine_id} {old_state.name} -> {new_state.name}")
            
        return jsonify({
            'status': 'success',
            'machine_id': machine_id,
            'old_state': old_state.name,
            'new_state': new_state.name,
            'triggered_events': len(triggered_events)
        })
        
    except Exception as e:
        logger.error(f"Transition error: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

def send_event_to_machine(target_machine, event):
    """他のステートマシンにイベント送信"""
    try:
        # 対象マシンの適切な遷移を実行
        if state_machine_manager.can_handle_event(target_machine, event):
            transition_name = state_machine_manager.get_transition_for_event(
                target_machine, event
            )
            
            if transition_name:
                old_state, new_state = state_machine_manager.execute_transition(
                    target_machine, transition_name, event['data']
                )
                
                container_manager.transition_container(
                    target_machine, old_state, new_state
                )
                
                logger.info(f"Event sent to {target_machine}: {event['name']}")
        else:
            logger.warning(f"Machine {target_machine} cannot handle event {event['name']}")
                
    except Exception as e:
        logger.error(f"Error sending event to {target_machine}: {str(e)}")

@app.route('/status', methods=['GET'])
def get_status():
    """システム状態取得"""
    status = {}
    for machine_id in state_machine_manager.get_machine_ids():
        machine = state_machine_manager.get_machine(machine_id)
        current_state = machine.get_current_state()
        container_status = container_manager.get_container_status(machine_id)
        
        # 利用可能な遷移も含める
        available_transitions = []
        for trans_name, transition in machine.transitions.items():
            if transition.from_state == current_state.name:
                available_transitions.append({
                    'name': trans_name,
                    'to_state': transition.to_state,
                    'trigger_event': transition.trigger_event
                })
        
        status[machine_id] = {
            'current_state': current_state.name,
            'container_image': current_state.container_image,
            'container_status': container_status,
            'available_transitions': available_transitions
        }
        
    return jsonify(status)

@app.route('/nodes', methods=['GET'])
def get_nodes():
    """エッジノードのリソース状況取得"""
    try:
        nodes = container_manager.get_node_resources()
        return jsonify(nodes)
    except Exception as e:
        logger.error(f"Failed to get nodes: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/swarm', methods=['GET'])
def get_swarm_info():
    """Swarmクラスタ情報取得"""
    try:
        swarm_info = container_manager.get_swarm_info()
        return jsonify(swarm_info)
    except Exception as e:
        logger.error(f"Failed to get swarm info: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """ヘルスチェック"""
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})

if __name__ == '__main__':
    logger.info("🚀 Starting Edge Surveillance Event Bus (Docker Swarm Mode)...")
    initialize_system()
    logger.info("✅ System initialized successfully")
    app.run(host='0.0.0.0', port=5000, debug=False)