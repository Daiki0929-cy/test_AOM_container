import docker
import logging
import time
from typing import Dict, Optional, List

logger = logging.getLogger(__name__)

class SwarmContainerManager:
    def __init__(self):
        """Docker Swarm管理クライアント初期化"""
        self.client = docker.from_env()
        self.active_services = {}  # {machine_id: service_id}
        
        # Swarmモード確認
        try:
            swarm_info = self.client.info()
            if not swarm_info.get('Swarm', {}).get('NodeID'):
                raise RuntimeError("Docker is not in Swarm mode. Run 'docker swarm init' first.")
            logger.info("Connected to Docker Swarm cluster")
        except Exception as e:
            logger.error(f"Failed to connect to Docker Swarm: {str(e)}")
            raise
    
    def start_state_container(self, machine_id: str, state_name: str, 
                            container_image: str) -> str:
        """状態用コンテナをSwarmサービスとしてデプロイ"""
        try:
            service_name = f"{machine_id}-{state_name}"
            
            # 既存サービス削除
            self._force_stop_existing_services(machine_id)
            
            # サービス作成
            service = self._create_service(
                service_name, machine_id, state_name, container_image
            )
            
            self.active_services[machine_id] = service.id
            logger.info(f"Created Swarm service {service_name} ({service.id[:12]})")
            
            # サービス起動待機
            self._wait_for_service_ready(service_name)
            
            return service.id
            
        except Exception as e:
            logger.error(f"Failed to create service for {machine_id}-{state_name}: {str(e)}")
            raise
    
    def _create_service(self, service_name: str, machine_id: str,
                       state_name: str, container_image: str):
        """Swarmサービス作成"""
        
        # コンテナ設定
        container_spec = docker.types.ContainerSpec(
            image=container_image,
            env={
                'MACHINE_ID': machine_id,
                'STATE_NAME': state_name,
                'EVENT_BUS_URL': 'http://event-bus:5000'
            }
        )
        
        # タスクテンプレート
        task_template = docker.types.TaskTemplate(
            container_spec=container_spec,
            restart_policy=docker.types.RestartPolicy(condition='none'),  # 状態遷移時は再起動しない
            placement=docker.types.Placement(
                constraints=['node.labels.role==edge']  # エッジノードのみ
            ),
            resources=docker.types.Resources(
                cpu_limit=500000000,      # 0.5 CPU (nano cpus)
                mem_limit=512 * 1024 * 1024,  # 512MB
                cpu_reservation=100000000,  # 0.1 CPU
                mem_reservation=128 * 1024 * 1024  # 128MB
            )
        )
        
        # エンドポイント設定
        endpoint_spec = docker.types.EndpointSpec(
            mode='vip'
        )
        
        # サービス作成
        service = self.client.services.create(
            image=container_image,
            name=service_name,
            task_template=task_template,
            endpoint_spec=endpoint_spec,
            networks=['edge-surveillance-network'],
            labels={
                'machine-id': machine_id,
                'state': state_name,
                'app': 'edge-surveillance'
            }
        )
        
        return service
    
    def transition_container(self, machine_id: str, old_state, new_state):
        """状態遷移時のコンテナ切り替え"""
        try:
            # 古いサービス削除
            self._force_stop_existing_services(machine_id)
            
            time.sleep(1)
            
            # 新しいサービス作成
            self.start_state_container(
                machine_id, new_state.name, new_state.container_image
            )
            
            logger.info(f"Transitioned {machine_id}: {old_state.name} -> {new_state.name}")
            
        except Exception as e:
            logger.error(f"Service transition failed for {machine_id}: {str(e)}")
            raise
    
    def _force_stop_existing_services(self, machine_id: str):
        """既存サービス削除"""
        try:
            # アクティブサービスリストから削除
            if machine_id in self.active_services:
                service_id = self.active_services[machine_id]
                self._delete_service_by_id(service_id)
                del self.active_services[machine_id]
            
            # ラベルセレクタで該当サービス検索・削除
            services = self.client.services.list(
                filters={'label': f'machine-id={machine_id}'}
            )
            
            for service in services:
                logger.info(f"Force stopping service: {service.name}")
                self._delete_service_by_id(service.id)
                
        except Exception as e:
            logger.warning(f"Error during force stop for {machine_id}: {str(e)}")
    
    def _delete_service_by_id(self, service_id: str):
        """サービスIDでサービス削除"""
        try:
            service = self.client.services.get(service_id)
            service.remove()
            logger.info(f"Removed service {service_id[:12]}")
        except docker.errors.NotFound:
            logger.info(f"Service {service_id[:12]} not found (already removed)")
        except Exception as e:
            logger.warning(f"Failed to remove service {service_id[:12]}: {str(e)}")
    
    def _wait_for_service_ready(self, service_name: str, timeout=60):
        """サービス準備完了待機"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                service = self.client.services.get(service_name)
                tasks = service.tasks()
                
                # 実行中のタスクがあるか確認
                running_tasks = [t for t in tasks if t['Status']['State'] == 'running']
                
                if running_tasks:
                    logger.info(f"Service {service_name} is ready with {len(running_tasks)} running task(s)")
                    return True
                    
            except docker.errors.NotFound:
                pass
            except Exception as e:
                logger.warning(f"Error checking service status: {str(e)}")
            
            time.sleep(2)
        
        logger.warning(f"Service {service_name} not ready after {timeout}s")
        return False
    
    def get_container_status(self, machine_id: str) -> dict:
        """コンテナ状態取得"""
        if machine_id not in self.active_services:
            return {'status': 'not_running'}
        
        service_id = self.active_services[machine_id]
        
        try:
            service = self.client.services.get(service_id)
            tasks = service.tasks()
            
            # タスク情報収集
            task_info = []
            for task in tasks:
                node_id = task.get('NodeID', 'unknown')
                node_name = self._get_node_name(node_id)
                
                task_info.append({
                    'id': task['ID'][:12],
                    'state': task['Status']['State'],
                    'node': node_name,
                    'desired_state': task['DesiredState']
                })
            
            # 実行中のタスク数
            running_count = sum(1 for t in tasks if t['Status']['State'] == 'running')
            
            return {
                'status': 'running' if running_count > 0 else 'pending',
                'service_name': service.name,
                'service_id': service.id[:12],
                'replicas': len(tasks),
                'running_replicas': running_count,
                'tasks': task_info
            }
            
        except docker.errors.NotFound:
            del self.active_services[machine_id]
            return {'status': 'not_found'}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
    
    def _get_node_name(self, node_id: str) -> str:
        """ノードIDからノード名取得"""
        try:
            node = self.client.nodes.get(node_id)
            return node.attrs['Description']['Hostname']
        except:
            return node_id[:12]
    
    def get_node_resources(self) -> Dict[str, dict]:
        """各ノードのリソース使用状況取得"""
        nodes = {}
        
        try:
            node_list = self.client.nodes.list(
                filters={'node.label.role': 'edge'}
            )
            
            for node in node_list:
                node_name = node.attrs['Description']['Hostname']
                node_id = node.id
                
                # リソース情報
                resources = node.attrs['Description']['Resources']
                status = node.attrs['Status']
                spec = node.attrs['Spec']
                
                # 現在のタスク数を取得
                tasks = self.client.tasks.list(
                    filters={'node': node_id, 'desired-state': 'running'}
                )
                
                nodes[node_name] = {
                    'node_id': node_id[:12],
                    'status': status['State'],
                    'availability': spec.get('Availability', 'unknown'),
                    'nano_cpus': resources.get('NanoCPUs', 0),
                    'memory_bytes': resources.get('MemoryBytes', 0),
                    'running_tasks': len(tasks),
                    'labels': spec.get('Labels', {})
                }
            
        except Exception as e:
            logger.error(f"Failed to get node resources: {str(e)}")
        
        return nodes
    
    def cleanup_all_services(self, machine_id: str = None):
        """全サービスクリーンアップ"""
        try:
            if machine_id:
                filters = {'label': f'machine-id={machine_id}'}
            else:
                filters = {'label': 'app=edge-surveillance'}
            
            services = self.client.services.list(filters=filters)
            
            for service in services:
                logger.info(f"Cleaning up service: {service.name}")
                service.remove()
                
        except Exception as e:
            logger.error(f"Cleanup error: {str(e)}")
    
    def scale_service(self, machine_id: str, replicas: int):
        """サービスのレプリカ数変更（通常は1だが、負荷分散時に使用可能）"""
        if machine_id not in self.active_services:
            raise ValueError(f"No active service for {machine_id}")
        
        service_id = self.active_services[machine_id]
        
        try:
            service = self.client.services.get(service_id)
            service.update(mode={'Replicated': {'Replicas': replicas}})
            logger.info(f"Scaled service {service.name} to {replicas} replicas")
        except Exception as e:
            logger.error(f"Failed to scale service: {str(e)}")
            raise
    
    def get_swarm_info(self) -> dict:
        """Swarmクラスタ情報取得"""
        try:
            info = self.client.info()
            swarm_info = info.get('Swarm', {})
            
            return {
                'node_id': swarm_info.get('NodeID', 'unknown')[:12],
                'node_addr': swarm_info.get('NodeAddr', 'unknown'),
                'local_node_state': swarm_info.get('LocalNodeState', 'unknown'),
                'control_available': swarm_info.get('ControlAvailable', False),
                'managers': swarm_info.get('Managers', 0),
                'nodes': swarm_info.get('Nodes', 0)
            }
        except Exception as e:
            logger.error(f"Failed to get swarm info: {str(e)}")
            return {'error': str(e)}