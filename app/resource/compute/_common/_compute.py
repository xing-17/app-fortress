from __future__ import annotations

import json
from abc import ABC, abstractmethod
from typing import Any, ClassVar

from pydantic import Field, PrivateAttr, model_validator

from app.internal.abstract.domain import IAbstractTaggedDomain
from app.internal.constant.computeruntime import ComputeRuntime
from app.internal.constant.computestatus import ComputeStatus
from app.internal.constant.platform import Platform
from app.internal.util.frn import IFrn
from app.resource._global.stores import GlobalStores
from app.resource.compute._common._run import ComputeRun
from app.resource.store._common._store import BaseStore
from app.resource.store._common._table import BaseTable
from app.resource.store.file.store import FileStore
from app.setting._compute import COMPUTE_NAME_PATTERN, UnionComputeSetting
from app.setting._store import AbstractStoreSetting


class BaseCompute(
    IAbstractTaggedDomain,
    ABC,
):
    """
    Base class for compute resources

    Attributes:
    ----------
        frn (str):
            Compute FRN (Fortress resource identifier)
        table (BaseTable | None):
            Run record table `<name>` in database `_compute` of the store

    Args:
    ----------
        runtime (ComputeRuntime):
            Compute runtime, declared by the subclass
        platform (Platform):
            Compute operating platform, declared by the subclass
        name (str):
            Compute name, only letters, digits and underscores
        description (str):
            Compute description information
        store (BaseStore | AbstractStoreSetting | str | None):
            Store holding the run records, resolved through GlobalStores
        tags (dict[str, str]):
            Compute tags

    Methods:
    ----------
        from_setting(setting: UnionComputeSetting) -> BaseCompute:
            Create a compute instance from a setting
        execute(payload: dict[str, Any] | None = None, raise_on_error: bool = False) -> ComputeRun:
            Run synchronously, record and return the finished run, re-raising a failure if requested
        submit(payload: dict[str, Any] | None = None, raise_on_error: bool = False) -> ComputeRun:
            Start asynchronously, record and return the STARTED run
        refresh(run: ComputeRun | str) -> ComputeRun:
            Poll the runtime and record a newly observed terminal status, poll errors propagate
        lookup(id: str) -> ComputeRun | None:
            Read a recorded run
        list_runs(status: ComputeStatus | None = None, limit: int | None = None) -> list[ComputeRun]:
            List recorded runs, newest first

    """

    # Enforced public class variables
    runtime: ClassVar[ComputeRuntime]
    platform: ClassVar[Platform]

    # Fixed database holding the run records of every compute
    _database_name: ClassVar[str] = "_compute"

    # Enforced instance variables
    # [Inherited] tags: dict[str, str]
    name: str = Field(
        ...,
        description="[Required] Compute name, only letters, digits and underscores",
        pattern=COMPUTE_NAME_PATTERN,
    )
    description: str = Field(
        default="",
        description="[Optional] Compute description information",
    )
    store: BaseStore | AbstractStoreSetting | str | None = Field(
        default=None,
        description="[Optional] Store holding the run records",
    )
    max_run_records: int = Field(
        default=200,
        description="[Optional] Maximum number of run records to keep",
        ge=1,  # Ensure at least one run record is kept
    )

    # Enforced private instance variables
    _table: BaseTable | None = PrivateAttr(default=None)

    @model_validator(mode="after")
    def _derive_store(self) -> "BaseCompute":
        _store: BaseStore = GlobalStores.resolve(
            self.store,
            default=FileStore(name="compute", path="./store/"),
        )
        object.__setattr__(self, "store", _store)
        return self

    @model_validator(mode="after")
    def _derive_table(self) -> "BaseCompute":
        _table: BaseTable = self.store.table(
            database=self._database_name,
            name=self.name,
            max_items=self.max_run_records,
        )
        object.__setattr__(self, "_table", _table)
        return self

    @property
    def table(self) -> BaseTable:
        return self._table

    @classmethod
    @abstractmethod
    def from_setting(
        cls,
        setting: UnionComputeSetting,
    ) -> "BaseCompute": ...

    @property
    def frn(self) -> str:
        return IFrn.resolve(
            [
                "compute",
                f"platform={self.platform}",
                f"runtime={self.runtime}",
                f"name={self.name}",
            ]
        )

    @abstractmethod
    def _execute(
        self,
        payload: dict[str, Any],
    ) -> dict[str, Any]: ...

    @abstractmethod
    def _submit(
        self,
        payload: dict[str, Any],
    ) -> str: ...

    @abstractmethod
    def _poll(
        self,
        run: ComputeRun,
    ) -> ComputeRun: ...

    def execute(
        self,
        payload: dict[str, Any] | None = None,
        raise_on_error: bool = False,
    ) -> ComputeRun:
        _payload: dict[str, Any] = self._ensure_payload(payload)
        _run: ComputeRun = ComputeRun(
            compute=self.name,
            runtime=self.runtime,
            payload=_payload,
        )
        self._write_run(_run)
        try:
            _result: dict[str, Any] = self._execute(_payload)
        except Exception as e:
            _run.fail(f"{type(e).__name__}: {e}")
            self._write_run(_run)
            if raise_on_error:
                raise
            return _run
        _run.complete(_result)
        self._write_run(_run)
        return _run

    def submit(
        self,
        payload: dict[str, Any] | None = None,
        raise_on_error: bool = False,
    ) -> ComputeRun:
        _payload: dict[str, Any] = self._ensure_payload(payload)
        _run: ComputeRun = ComputeRun(
            compute=self.name,
            runtime=self.runtime,
            payload=_payload,
        )
        self._write_run(_run)
        try:
            _external_id: str = self._submit(_payload)
        except Exception as e:
            _run.fail(f"{type(e).__name__}: {e}")
            self._write_run(_run)
            if raise_on_error:
                raise
            return _run
        _run.submit(_external_id)
        self._write_run(_run)
        return _run

    def refresh(
        self,
        run: ComputeRun | str,
    ) -> ComputeRun:
        if isinstance(run, str):
            _run: ComputeRun | None = self.lookup(run)
            if not _run:
                raise ValueError(f"Run '{run}' not found")
        elif isinstance(run, ComputeRun):
            _run = run
        else:
            raise ValueError(f"Run must be ComputeRun or str, got {type(run).__name__}")

        if _run.is_finished:
            return _run
        _run = self._poll(_run)
        self._write_run(_run)
        return _run

    def lookup(
        self,
        id: str,
    ) -> ComputeRun | None:
        _content: Any = self.table.read(key=id, strict=False)
        # if the content is not found, return None
        if not _content:
            return None
        return ComputeRun.from_dict(_content)

    def list_runs(
        self,
        status: ComputeStatus | None = None,
        limit: int | None = None,
    ) -> list[ComputeRun]:
        _runs: list[ComputeRun] = []
        for _run in self._read_runs():
            if status is not None and _run.status != status:
                continue
            _runs.append(_run)

        _runs.sort(
            key=lambda _r: _r.started_at,
            reverse=True,
        )
        if limit is not None and len(_runs) > limit:
            _runs = _runs[:limit]
        return _runs

    def _ensure_payload(
        self,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if payload is None:
            _payload = {}
        elif not isinstance(payload, dict):
            raise ValueError("Payload must be a dictionary")
        else:
            _payload = payload

        _payload = self._ensure_serialisable(_payload)
        return _payload

    def _ensure_serialisable(
        self,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        try:
            _dump: str = json.dumps(payload or {}, ensure_ascii=False)
            _payload = json.loads(_dump)
        except (TypeError, ValueError) as e:
            raise ValueError(f"Payload must be serialisable: {e}")
        return _payload

    def _write_run(
        self,
        run: ComputeRun,
    ) -> None:
        self.table.write(
            key=run.id,
            data=run.export(),
            strict=True,
        )

    def _read_runs(self) -> list[ComputeRun]:
        _contents: dict[str, Any] = self.table.read() or {}
        _results: list[ComputeRun] = []
        for _value in _contents.values():
            _run: ComputeRun = ComputeRun.from_dict(_value)
            _results.append(_run)
        return _results

    def _non_override_tags(self) -> dict[str, str]:
        return {
            "platform": self.platform,
            "runtime": self.runtime,
            "name": self.name,
        }
