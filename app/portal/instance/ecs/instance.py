from __future__ import annotations

import socket

from alibabacloud_ecs20140526 import models as EcsModels
from alibabacloud_tea_util import models as UtilModels

from app.common.setting.portal import EcsInstanceSetting
from app.portal.instance.base.base import BaseInstance, BaseInstanceState
from app.portal.instance.ecs.client import _EcsClient

# ──────────────────────────────────────────────────────────────────────────────

# ECS 实例状态直接继承
EcsInstanceState = BaseInstanceState


# ECS 实例类
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
                timeout=self.setting.timeout,
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

    def _start_instance(
        self,
        wait: bool = True,
    ) -> None:
        try:
            self._client._client.start_instance_with_options(
                request=EcsModels.StartInstanceRequest(instance_id=self._client.get_instance_id()),
                runtime=UtilModels.RuntimeOptions(autoretry=True),
            )
            self.debug("start_instance: started OK.")
        except Exception as e:
            raise RuntimeError(f"Fail to start instance '{self.name}': {e}")

        self._wait_for_start()
        return self._client.get_instance()

    def _wait_for_start(self) -> None:
        state_str: str = BaseInstanceState.RUNNING.value
        self._client.wait_instance(state=state_str)

    def _stop_instance(self) -> None:
        try:
            self._client.stop_instance(
                wait=True,
            )
            self.debug("stop_instance: stopped OK.")
        except Exception as e:
            raise RuntimeError(f"Fail to stop instance '{self.name}': {e}")

        self._wait_for_stop()
        return self._client.get_instance()

    def _wait_for_stop(self) -> None:
        state_str: str = BaseInstanceState.STOPPED.value
        self._client.wait_instance(state=state_str)

    def _load_specification(self) -> dict:
        instance_info = self._client.get_instance()
        return instance_info

    def run_command(
        self,
        command: str,
        timeout: int = 300,
        wait: bool = True,
    ) -> dict:
        result = self._client._start_command(
            command=command,
            timeout=timeout,
        )
        command_id = result.get("CommandId")
        invoke_id = result.get("InvokeId")
        if wait:
            self._client._wait_command(
                command_id=command_id,
                invoke_id=invoke_id,
                timeout=timeout,
            )
            result = self._client._get_command_result(
                command_id=command_id,
                invoke_id=invoke_id,
            )
        return result
