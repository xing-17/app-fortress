from __future__ import annotations

import json
import threading
from concurrent.futures import Future, ThreadPoolExecutor
from typing import Any, ClassVar

from pydantic import Field, PrivateAttr, model_validator

from app.internal.constant.computeruntime import ComputeRuntime
from app.internal.constant.platform import Platform
from app.internal.util.frn import IFrn
from app.internal.util.id import IID
from app.resource._client.fc.client import FCClient
from app.resource._global.identities import GlobalIdentities
from app.resource.compute._common._compute import BaseCompute
from app.resource.compute._common._run import ComputeRun
from app.resource.identity._common._identity import BaseIdentity
from app.resource.identity.aliyun import AliyunIdentity
from app.setting._compute import FCComputeSetting
from app.setting._identity import AbstractIdentitySetting


class FCCompute(BaseCompute):
    """
    阿里云函数计算(FC 3.0)计算资源，通过 InvokeFunction 调用已部署的函数。

    函数内部应运行与本地相同的 Fortress 代码，并自行重建所需资源，payload 以 JSON 作为请求体，
    函数返回值必须是 JSON 对象(dict)，与 PyEntrypointCompute 的入口约定一致。

    FC 调用始终是同步的，`execute` 在当前线程等待结果，`submit` 把同样的调用交给本地线程池。
    提交的 run 只由提交它的实例追踪，重启后 refresh 会将其标记为 FAILED，云端函数可能仍在运行。
    退出进程时会等待未完成的调用。

    Attributes:
    ----------
        runtime (ComputeRuntime):
            运行时类型，固定为ComputeRuntime.FC
        platform (Platform):
            平台类型，固定为Platform.ALIYUN
        client (FCClient):
            按 region/identity/in_vpc 缓存的 FC 客户端
        frn (str):
            Compute FRN

    Args:
    ----------
        name (str):
            计算资源名称
        function_name (str):
            FC 函数名称
        region (str):
            FC 函数所在区域
        qualifier (str):
            函数版本或别名，默认LATEST
        in_vpc (bool):
            是否在VPC内访问FC，默认False
        timeout_seconds (float):
            调用的读取超时秒数，默认600
        max_workers (int):
            submit 的本地最大并发调用数，默认8
        identity (AliyunIdentity | AbstractIdentitySetting | str | None):
            阿里云身份，默认AliyunIdentity.default()
        description (str):
            描述信息
        store (BaseStore | AbstractStoreSetting | str | None):
            记录运行结果的Store
        tags (dict[str, str]):
            标签

    Methods:
    ----------
        from_setting(cls, setting: FCComputeSetting) -> FCCompute:
            根据FCComputeSetting对象创建FCCompute实例。
        execute(payload: dict[str, Any] | None = None, raise_on_error: bool = False) -> ComputeRun:
            同步调用函数，响应体按JSON对象写入run.result；函数抛错记为FAILED，raise_on_error时重新抛出。
        submit(payload: dict[str, Any] | None = None, raise_on_error: bool = False) -> ComputeRun:
            在本地线程池中调用函数并立即返回run，run.external_id为本地追踪用的token。
        refresh(run: ComputeRun | str) -> ComputeRun:
            调用结束后将run更新为COMPLETED或FAILED，结果为函数返回的JSON对象。
        export() -> dict[str, Any]:
            导出为字典，identity只保留名称。

    Example:
    ----------
        >>> compute = FCCompute(name="fc_fetch", function_name="fortress-run", region="cn-hangzhou")
        >>> run = compute.submit({"source": "tushare_prod", "dataset": "tradedates"})
        >>> compute.refresh(run).status

    """

    # Enforced public class variables
    runtime: ClassVar[ComputeRuntime] = ComputeRuntime.FC
    platform: ClassVar[Platform] = Platform.ALIYUN

    # Enforced instance variables
    # [Inherited] name: str
    # [Inherited] description: str
    # [Inherited] tags: dict[str, str]
    function_name: str = Field(
        ...,
        description="[Required] FC 函数名称",
        min_length=1,
    )
    region: str = Field(
        ...,
        description="[Required] FC 函数所在区域",
    )
    qualifier: str = Field(
        default="LATEST",
        description="[Optional] 函数版本或别名",
    )
    in_vpc: bool = Field(
        default=False,
        description="[Optional] 是否在VPC内访问FC",
    )
    timeout_seconds: float = Field(
        default=600,
        description="[Optional] 调用的读取超时秒数",
        gt=0,
    )
    max_workers: int = Field(
        default=8,
        description="[Optional] submit 的本地最大并发调用数",
        ge=1,
    )
    identity: AliyunIdentity | AbstractIdentitySetting | str | None = Field(
        default=None,
        description="[Optional] 阿里云身份用于调用函数",
    )

    # Enforced private instance variables
    _pool: ThreadPoolExecutor | None = PrivateAttr(default=None)
    _futures: dict[str, Future[dict[str, Any]]] = PrivateAttr(default_factory=dict)
    _lock: threading.RLock = PrivateAttr(default_factory=threading.RLock)

    @model_validator(mode="after")
    def _derive_identity(self) -> "FCCompute":
        _identity: BaseIdentity = GlobalIdentities.resolve(
            value=self.identity,
            default=AliyunIdentity.default(),
            platform=Platform.ALIYUN,
        )
        object.__setattr__(self, "identity", _identity)
        return self

    @classmethod
    def from_setting(
        cls,
        setting: FCComputeSetting,
    ) -> FCCompute:
        return cls(
            name=setting.name,
            function_name=setting.function_name,
            region=setting.region,
            qualifier=setting.qualifier,
            in_vpc=setting.in_vpc,
            timeout_seconds=setting.timeout_seconds,
            max_workers=setting.max_workers,
            identity=setting.identity,
            description=setting.description,
            store=setting.store,
            log_stream=setting.log,
            max_run_records=setting.max_run_records,
            tags=setting.tags,
        )

    @property
    def client(self) -> FCClient:
        return FCClient.get_client(
            region=self.region,
            identity=self.identity,
            in_vpc=self.in_vpc,
        )

    @property
    def frn(self) -> str:
        return IFrn.resolve(
            [
                "compute",
                f"platform={self.platform}",
                f"runtime={self.runtime}",
                f"region={self.region}",
                f"function={self.function_name}",
                f"name={self.name}",
            ]
        )

    def _execute(
        self,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        _content: str = json.dumps(payload, ensure_ascii=False)
        _bytes: bytes = _content.encode("utf-8")
        _name: str = self.function_name
        _res: dict[str, Any] = self.client.invoke(
            function_name=_name,
            payload=_bytes,
            qualifier=self.qualifier,
            timeout_seconds=self.timeout_seconds,
        )
        _reserr: str | None = _res.get("error")
        if _reserr:
            raise RuntimeError(f"FC function '{_name}' failed: {_reserr}")
        _body: dict[str, Any] = _res.get("body", {})
        return _body

    def _submit(
        self,
        payload: dict[str, Any],
    ) -> str:
        _token: str = IID.generate_id(prefix="fc", length=32)
        with self._lock:
            if self._pool is None:
                self._pool = ThreadPoolExecutor(
                    max_workers=self.max_workers,
                    thread_name_prefix=f"fc_{self.name}",
                )
            self._futures[_token] = self._pool.submit(self._execute, payload)
        return _token

    def refresh(
        self,
        run: ComputeRun | str,
    ) -> ComputeRun:
        # poll and record under one lock,
        # so concurrent refreshes cannot record conflicting outcomes
        with self._lock:
            return super().refresh(run)

    def _poll(
        self,
        run: ComputeRun,
    ) -> ComputeRun:
        _external_id: str = run.external_id
        _future: Future[dict[str, Any]] | None = self._futures.get(_external_id)
        if _future is None:
            _stored: ComputeRun | None = self.lookup(run.id)
            if _stored is not None and _stored.is_finished:
                return _stored
            # not submitted by this instance
            # or lost across a restart
            run.fail(error="Invocation not found")
            return run

        # the future is done, retrieve the result
        if not _future.done():
            return run

        # remove the future from the pool
        self._futures.pop(_external_id, None)
        try:
            run.complete(result=_future.result())
        except Exception as e:
            run.fail(error=f"{type(e).__name__}: {e}")
        return run
