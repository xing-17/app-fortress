from __future__ import annotations

import time

from alibabacloud_ecs20140526 import models as EcsModels
from alibabacloud_ecs20140526.client import Client as EcsClient
from alibabacloud_ecs20140526.models import (
    DescribeInvocationResultsResponse,
    RunCommandResponse,
)
from alibabacloud_tea_openapi import models as OpenApiModels
from alibabacloud_tea_util import models as UtilModels
from darabonba.model import DaraModel

from app.common.plugin import (
    LogPlugin,
    TimePlugin,
)
from app.portal.instance.base.base import (
    BaseInstanceState,
)


class _EcsClient(
    LogPlugin,
    TimePlugin,
):
    # - Pending: being created.
    # - Running: running.
    # - Starting: being started.
    # - Stopping: being stopped.
    # - Stopped: stopped.

    def __init__(
        self,
        instance_name: str,
        region_id: str,
        access_key_id: str,
        access_key_secret: str,
    ):
        self.instance_name = instance_name
        self.region_id = region_id
        self.config = OpenApiModels.Config(
            access_key_id=access_key_id, access_key_secret=access_key_secret, region_id=region_id
        )
        self._client = EcsClient(self.config)
        self._set_log_prefix(f"_EcsClient({self.instance_name})")

    def get_instance(self) -> dict:
        try:
            response = self._client.describe_instances_with_options(
                request=EcsModels.DescribeInstancesRequest(
                    instance_name=self.instance_name,
                    region_id=self.region_id,
                ),
                runtime=UtilModels.RuntimeOptions(autoretry=True),
            )
            instances = response.body.instances.instance
            result: DaraModel = instances[0]
            return result.to_map()
        except Exception as e:
            raise RuntimeError(f"Fail to get instance '{self.instance_name}': {e}")

    def _resolve_instance_state(
        self,
        payload: dict | None = None,
    ) -> str | None:
        if not payload:
            payload = self.get_instance()
        return payload.get("Status")

    def _resolve_instance_id(
        self,
        payload: dict | None = None,
    ) -> str | None:
        if not payload:
            payload = self.get_instance()
        return payload.get("InstanceId")

    def get_instance_id(self) -> str | None:
        return self._resolve_instance_id()

    def get_instance_state(self) -> str | None:
        return self._resolve_instance_state()

    def start_instance(
        self,
        wait: bool = False,
    ) -> dict:
        try:
            self._client.start_instance_with_options(
                request=EcsModels.StartInstanceRequest(instance_id=self.get_instance_id()),
                runtime=UtilModels.RuntimeOptions(autoretry=True),
            )
            self.debug("start_instance: started OK.")
        except Exception as e:
            raise RuntimeError(f"Fail to start instance '{self.instance_name}': {e}")

        if wait:
            self.wait_instance(BaseInstanceState.RUNNING)
        return self.get_instance()

    def stop_instance(
        self,
        wait: bool = False,
    ) -> dict:
        try:
            self._client.stop_instance_with_options(
                request=EcsModels.StopInstanceRequest(
                    instance_id=self.get_instance_id(),
                    stopped_mode="StopCharging",
                ),
                runtime=UtilModels.RuntimeOptions(autoretry=True),
            )
            self.debug("stop_instance: stopped OK.")
        except Exception as e:
            raise RuntimeError(f"Fail to stop instance '{self.instance_name}': {e}")

        if wait:
            self.wait_instance(BaseInstanceState.STOPPED)
        return self.get_instance()

    def wait_instance(
        self,
        state: str,
        timeout: int = 300,
        interval: int = 5,
    ) -> None:
        _state = state.lower()

        # Wait for the instance to reach the desired state
        _name = self.instance_name
        start_time = time.time()
        for _curindex in range(timeout // interval):
            _curstate = self._resolve_instance_state().lower()
            if not _curstate:
                raise RuntimeError(f"Fail to get 'state' from '{_name}'.")
            if _curstate == _state:
                self.debug(f"wait_instance: '{_name}' -> '{_state}' OK.")
                return
            if time.time() - start_time > timeout:
                self.error(f"wait_instance: timeout wait '{_name}' -> '{_state}'. ")
                self.error(f"wait_instance: current state = '{_curstate}'. ")
                raise TimeoutError(f"Timeout waiting for instance '{_name}'.")

            self.debug(f"wait_instance: '{_name}' waiting [{_curindex}] ({_curstate} / {_state}).")
            time.sleep(interval)

    def run_command(
        self,
        command: str,
        timeout: int = 300,
        wait: bool = True,
    ) -> dict:
        result = self._start_command(
            command=command,
            timeout=timeout,
        )
        command_id = result.get("CommandId")
        invoke_id = result.get("InvokeId")
        if wait:
            self._wait_command(
                command_id=command_id,
                invoke_id=invoke_id,
                timeout=timeout,
            )
            result = self._get_command_result(
                command_id=command_id,
                invoke_id=invoke_id,
            )
        return result

    def _start_command(
        self,
        command: str,
        timeout: int = 300,
    ) -> dict:
        try:
            response: RunCommandResponse = self._client.run_command_with_options(
                tmp_req=EcsModels.RunCommandRequest(
                    instance_id=[self.get_instance_id()],
                    command_content=command,
                    timed=True,
                    timeout=timeout,
                    region_id=self.region_id,
                    type="RunShellScript",
                ),
                runtime=UtilModels.RuntimeOptions(autoretry=True),
            )
            self.debug("run_command: OK.")
            return response.body.to_map()
        except Exception as e:
            self.error(f"run_command: fail {e}")
            self.error(f"run_command: command = {command}")
            self.error(f"run_command: instance_name = {self.instance_name}")
            self.error(f"run_command: instance_id = {self.get_instance_id()}")
            raise RuntimeError(f"Fail to run command '{command}': {e}")

    def _get_command_result(
        self,
        command_id: str,
        invoke_id: str,
    ) -> dict:
        try:
            response: DescribeInvocationResultsResponse = self._client.describe_invocation_results_with_options(
                request=EcsModels.DescribeInvocationResultsRequest(
                    command_id=command_id,
                    invoke_id=invoke_id,
                    region_id=self.region_id,
                ),
                runtime=UtilModels.RuntimeOptions(autoretry=True),
            )
            self.debug("_get_command_result: OK.")
            return response.body.to_map()
        except Exception as e:
            self.error(f"_get_command_result: fail {e}")
            self.error(f"_get_command_result: command_id = {command_id}")
            self.error(f"_get_command_result: instance_name = {self.instance_name}")
            self.error(f"_get_command_result: instance_id = {self.get_instance_id()}")
            raise RuntimeError(f"Fail to get command result '{command_id}': {e}")

    def _check_command_finished(
        self,
        command_id: str,
        invoke_id: str,
    ) -> bool:
        result = self._get_command_result(
            command_id=command_id,
            invoke_id=invoke_id,
        )
        _inv_results: dict = result.get("Invocation", {}).get("InvocationResults", {})
        _inv_result: list[dict] = _inv_results.get("InvocationResult", [])
        for _inv in _inv_result:
            _status: str = _inv.get("InvokeRecordStatus")
            if _status.lower() != "Finished".lower():
                return False
        return True

    def _wait_command(
        self,
        command_id: str,
        invoke_id: str,
        timeout: int = 300,
        interval: int = 5,
    ) -> None:
        _name = self.instance_name
        start_time = time.time()
        for _curindex in range(timeout // interval):
            if self._check_command_finished(
                command_id=command_id,
                invoke_id=invoke_id,
            ):
                self.debug(f"_wait_command: '{_name}' '{command_id}/{invoke_id}' finished OK.")
                return
            if time.time() - start_time > timeout:
                self.error(f"_wait_command: '{_name}' '{command_id}/{invoke_id}' timeout.")
                raise TimeoutError(f"Timeout waiting for command '{command_id}' on instance '{_name}'.")

            self.debug(f"_wait_command: '{_name}' waiting [{_curindex}] ({command_id}/{invoke_id}).")
            time.sleep(interval)
