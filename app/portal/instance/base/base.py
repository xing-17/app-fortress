from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from typing import Protocol

from app.common.plugin import (
    LogPlugin,
    TimePlugin,
)
from app.common.setting.portal import InstanceSetting


class BaseInstanceState(str, Enum):
    """
    实例状态枚举。

    定义实例生命周期中的所有可能状态，支持直接序列化为字符串。

    Attributes:
        UNKNOWN: 未知状态
        PENDING: 待创建
        RUNNING: 运行中
        STARTING: 启动中
        STOPPED: 已停止
        STOPPING: 停止中
        ERROR: 错误状态

    """

    UNKNOWN = "unknown"
    PENDING = "pending"
    RUNNING = "running"
    STARTING = "starting"
    STOPPED = "stopped"
    STOPPING = "stopping"
    ERROR = "error"


class InstanceLike(Protocol):
    """
    实例协议接口。

    定义实例对象必须实现的核心方法，用于类型提示和鸭子类型约束。

    Methods:
        ping: 检测实例网络连通性
        start: 启动实例
        stop: 停止实例
        restart: 重启实例
        run_command: 在实例上执行远程命令

    """

    def ping(self) -> bool: ...
    def start(self) -> None: ...
    def stop(self) -> None: ...
    def restart(self) -> None: ...
    def run_command(
        self,
        command: str,
        timeout: int = 300,
        wait: bool = True,
    ) -> dict: ...


class BaseInstance(
    LogPlugin,
    TimePlugin,
    InstanceLike,
    ABC,
):
    """
    实例抽象基类。

    提供云实例管理的通用框架，实现状态管理、生命周期控制的模板方法。
    子类需实现具体的启动、停止、规格加载及命令执行逻辑。

    Attributes:
        setting: 实例配置对象
        name: 实例名称
        state: 当前状态
        spec: 实例规格信息字典

    Properties:
        is_running: 实例是否处于运行状态
        is_stopped: 实例是否处于停止状态

    Methods:
        load: 加载实例规格和状态
        ping: 检测实例连通性
        get_state: 获取实例当前状态
        start: 启动实例（包含状态管理和错误回滚）
        stop: 停止实例（包含状态管理和错误回滚）
        restart: 重启实例
        run_command: 执行远程命令
        export: 导出实例完整快照

    Examples:
        >>> class MyInstance(BaseInstance):
        ...     def ping(self): return True
        ...     def _start_instance(self): pass
        >>> instance = MyInstance(setting)
        >>> instance.start()
        >>> print(instance.export())

    """

    def __init__(
        self,
        setting: InstanceSetting,
    ):
        self.setting = setting
        self.name = setting.name
        self.state: BaseInstanceState = BaseInstanceState.UNKNOWN
        self.spec: dict = {}
        self._set_log_prefix(f"BaseInstance({self.name})")

    def _set_state(
        self,
        state: BaseInstanceState,
    ) -> None:
        self.state = state

    def _unset_state(self) -> None:
        self.state = BaseInstanceState.UNKNOWN

    @property
    def is_running(self) -> bool:
        return self.state == BaseInstanceState.RUNNING

    @property
    def is_stopped(self) -> bool:
        return self.state == BaseInstanceState.STOPPED

    @abstractmethod
    def load(self) -> None:
        raise NotImplementedError("Load method must be implemented by subclasses.")

    @abstractmethod
    def ping(self) -> bool:
        raise NotImplementedError("Ping method must be implemented by subclasses.")

    @abstractmethod
    def get_state(self) -> BaseInstanceState:
        raise NotImplementedError("Get status method must be implemented by subclasses.")

    @abstractmethod
    def _start_instance(self) -> None:
        raise NotImplementedError("Start method must be implemented by subclasses.")

    @abstractmethod
    def _wait_for_start(self) -> None:
        raise NotImplementedError("Wait for start method must be implemented by subclasses.")

    @abstractmethod
    def _stop_instance(self) -> None:
        raise NotImplementedError("Stop method must be implemented by subclasses.")

    @abstractmethod
    def _wait_for_stop(self) -> None:
        raise NotImplementedError("Wait for stop method must be implemented by subclasses.")

    @abstractmethod
    def _load_specification(self) -> dict:
        raise NotImplementedError("Load specification method must be implemented by subclasses.")

    @abstractmethod
    def run_command(
        self,
        command: str,
        timeout: int = 300,
        wait: bool = True,
    ) -> dict:
        raise NotImplementedError("Call method must be implemented by subclasses.")

    def start(self):
        self._set_state(BaseInstanceState.STARTING)
        self.info(f"start: instance '{self.name}' starting OK.")
        try:
            self._start_instance()
            self._wait_for_start()
            self._set_state(BaseInstanceState.RUNNING)
            self.info(f"start: instance '{self.name}' started OK.")
        except Exception as e:
            self.error(f"start: instance '{self.name}' failed to start: {e}")
            self._unset_state()
            raise

    def stop(self):
        self._set_state(BaseInstanceState.STOPPING)
        self.info(f"stop: instance '{self.name}' stopping OK.")
        try:
            self._stop_instance()
            self._wait_for_stop()
            self._set_state(BaseInstanceState.STOPPED)
            self.info(f"stop: instance '{self.name}' stopped OK.")
        except Exception as e:
            self.error(f"stop: instance '{self.name}' failed to stop: {e}")
            self._unset_state()
            raise

    def restart(self):
        self.stop()
        self.start()

    def get_specification(self) -> dict:
        self.spec = self._load_specification()
        return self.spec

    def export(self) -> dict:
        return {
            "name": self.setting.name,
            "host": self.setting.host,
            "port": self.setting.port,
            "timeout": self.setting.timeout,
            "state": self.state.value,
            "is_running": self.is_running,
            "is_stopped": self.is_stopped,
            "spec": self.spec,
        }
