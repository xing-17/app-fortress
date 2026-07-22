import socket

from app.common.setting.portal import EcsInstanceSetting
from app.portal.instance.base.base import BaseInstance, BaseInstanceState
from app.portal.instance.ecs.client import _EcsClient

EcsInstanceState = BaseInstanceState


class EcsInstance(BaseInstance):
    def __init__(
        self,
        setting: EcsInstanceSetting,
    ):
        super().__init__(setting=setting)
        self.region_id = setting.region
        self._set_log_prefix(f"EcsInstance({self.name})")

        self._client = _EcsClient(
            instance_name=setting.name,
            region_id=setting.region,
            access_key_id=setting.access_key_id,
            access_key_secret=setting.access_key_secret,
        )
        self.load()

    def load(self) -> None:
        self.spec = self._load_specification()
        self.state = self.get_state()

    def ping(self) -> bool:
        try:
            with socket.create_connection(
                address=(self.setting.host, self.setting.port),
                timeout=self.timeout,
            ):
                return True
        except socket.timeout, socket.error, OSError:
            return False
        except Exception as e:
            self.error(f"ping: instance '{self.name}' fail: {e}")
            return False

    def get_state(self) -> EcsInstanceState:
        state_str = self._client._resolve_instance_state()
        if state_str is None:
            return EcsInstanceState.UNKNOWN
        try:
            return EcsInstanceState(state_str.lower())
        except ValueError:
            return EcsInstanceState.UNKNOWN

    def _start_instance(self) -> None:
        self._client.start_instance(wait=True)

    def _wait_for_start(self) -> None:
        # Wait already done in _start_instance
        pass

    def _stop_instance(self) -> None:
        self._client.stop_instance(wait=True)

    def _wait_for_stop(self) -> None:
        # Wait already done in _stop_instance
        pass

    def _load_specification(self) -> dict:
        instance_info = self._client.get_instance()
        return instance_info

    def run_command(
        self,
        command: str,
        timeout: int = 300,
        wait: bool = True,
    ) -> dict:
        result = self._client.run_command(
            command=command,
            timeout=timeout,
            wait=wait,
        )
        return result
