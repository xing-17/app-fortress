from typing import Protocol

from app.bridges.resources.base.servicehealth import ServiceHealth


class ServiceLike(Protocol):
    """
    服务协议（Protocol）接口定义。

    定义了一个标准服务应该实现的核心方法契约，包括启动、停止和健康检查。
    所有实现此协议的服务类将自动满足结构化类型检查（structural typing）。

    Methods:
        start() -> None:
            启动服务。通常用于启动后台工作线程或初始化资源。
            实现应该是幂等的，多次调用不应产生副作用。

        stop() -> None:
            停止服务。通常用于优雅地关闭服务，等待任务完成或清理资源。
            应该阻塞直到服务完全停止。

        health() -> ServiceHealth:
            返回服务的健康状态。提供服务当前运行状态的快照，
            包括工作线程状态、队列状态等关键指标。

    Example:
        >>> def process_service(svc: ServiceLike) -> None:
        ...     svc.start()
        ...     health = svc.health()
        ...     if health.worker_alive:
        ...         print("Service is running")
        ...     svc.stop()
    """

    def start(self) -> None: ...

    def stop(self) -> None: ...

    def health(self) -> ServiceHealth: ...
