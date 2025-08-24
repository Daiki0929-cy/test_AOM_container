import docker
import logging
import time
from typing import Dict, Optional

logger = logging.getLogger(__name__)

class ContainerManager:
    def __init__(self):
        self.client = docker.from_env()
        self.active_containers = {}  # {machine_id: container_id}
        
    def start_state_container(self, machine_id: str, state_name: str, 
                            container_image: str) -> str:
        """状態用コンテナ起動"""
        try:
            container_name = f"{machine_id}-{state_name}"
            
            # 既存コンテナがあれば強制停止
            self._force_stop_existing_containers(machine_id)
            
            # 新しいコンテナ起動
            container = self.client.containers.run(
                image=container_image,
                name=container_name,
                detach=True,
                environment={
                    'MACHINE_ID': machine_id,
                    'STATE_NAME': state_name,
                    'EVENT_BUS_URL': 'http://event-bus:5000'
                },
                network='edge-surveillance-network',
                restart_policy={"Name": "no"}  # 自動再起動を無効化
            )
            
            self.active_containers[machine_id] = container.id
            logger.info(f"Started container {container_name} ({container.id[:12]})")
            
            return container.id
            
        except Exception as e:
            logger.error(f"Failed to start container for {machine_id}-{state_name}: {str(e)}")
            raise

    def transition_container(self, machine_id: str, old_state, new_state):
        """状態遷移時のコンテナ切り替え"""
        try:
            # 古いコンテナ強制停止
            self._force_stop_existing_containers(machine_id)
            
            # 少し待機してからコンテナ起動
            time.sleep(0.5)
            
            # 新しいコンテナ起動
            self.start_state_container(
                machine_id, new_state.name, new_state.container_image
            )
            
            logger.info(f"Transitioned {machine_id}: {old_state.name} -> {new_state.name}")
            
        except Exception as e:
            logger.error(f"Container transition failed for {machine_id}: {str(e)}")
            raise

    def _force_stop_existing_containers(self, machine_id: str):
        """既存のコンテナを強制停止（すべてのパターンで）"""
        try:
            # 1. アクティブコンテナリストから停止
            if machine_id in self.active_containers:
                container_id = self.active_containers[machine_id]
                self._stop_container_by_id(container_id)
                del self.active_containers[machine_id]
            
            # 2. 名前パターンマッチで停止（念のため）
            containers = self.client.containers.list(all=True)
            for container in containers:
                if container.name.startswith(f"{machine_id}-"):
                    logger.info(f"Force stopping container by name pattern: {container.name}")
                    self._stop_container_by_id(container.id)
            
        except Exception as e:
            logger.warning(f"Error during force stop for {machine_id}: {str(e)}")

    def _stop_container_by_id(self, container_id: str):
        """コンテナIDで停止"""
        try:
            container = self.client.containers.get(container_id)
            
            if container.status == 'running':
                logger.info(f"Stopping running container {container_id[:12]}")
                container.stop(timeout=5)  # より短いタイムアウト
            
            # コンテナ削除
            if container.status in ['exited', 'created', 'stopped']:
                container.remove(force=True)
                logger.info(f"Removed container {container_id[:12]}")
                
        except docker.errors.NotFound:
            logger.info(f"Container {container_id[:12]} not found (already removed)")
        except Exception as e:
            logger.warning(f"Failed to stop container {container_id[:12]}: {str(e)}")
            # 強制削除を試行
            try:
                container = self.client.containers.get(container_id)
                container.remove(force=True)
                logger.info(f"Force removed container {container_id[:12]}")
            except:
                pass

    def get_container_status(self, machine_id: str) -> dict:
        """コンテナ状態取得"""
        if machine_id not in self.active_containers:
            return {'status': 'not_running'}
            
        container_id = self.active_containers[machine_id]
        try:
            container = self.client.containers.get(container_id)
            return {
                'status': container.status,
                'container_id': container_id[:12],
                'image': container.image.tags[0] if container.image.tags else 'unknown',
                'name': container.name
            }
        except docker.errors.NotFound:
            # コンテナが見つからない場合はリストから削除
            del self.active_containers[machine_id]
            return {'status': 'not_found'}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
            
    def cleanup_all_containers(self, machine_id: str = None):
        """全コンテナクリーンアップ（デバッグ用）"""
        try:
            if machine_id:
                pattern = f"{machine_id}-"
            else:
                pattern = "detector-"  # または適切なプレフィックス
                
            containers = self.client.containers.list(all=True)
            for container in containers:
                if container.name.startswith(pattern):
                    logger.info(f"Cleaning up container: {container.name}")
                    container.remove(force=True)
                    
        except Exception as e:
            logger.error(f"Cleanup error: {str(e)}")