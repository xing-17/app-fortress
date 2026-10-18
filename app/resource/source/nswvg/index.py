from __future__ import annotations

import threading
from typing import ClassVar

from pydantic import Field, PrivateAttr

from app.internal.abstract.domain import IAbstractDomain
from app.internal.logstream import LogStream
from app.resource.accessory.jitter.jitter import Jitter
from app.resource.accessory.retry.retry import Retry
from app.resource.source.nswvg.remote import (
    CRITICAL_ERROR_EXPRS,
    NSWVGIndexPage,
    NSWVGPSIFile,
)
from app.resource.store._common._table import BaseTable


class NSWVGIndex(IAbstractDomain):
    """
    Index of remote NSW VG PSI files, scraped from the public index page.

    Kept out of `datasets/` on purpose
    it is not an ETL dataset and must not be auto-discovered.

    """

    # Class-level policy; always `clone()` before use, Retry keeps per-run state.
    retry: ClassVar[Retry] = Retry(
        max_retries=3,
        interval=30,
        backoff_rate=2.0,
        critical_error_exprs=CRITICAL_ERROR_EXPRS,
    )
    jitter: ClassVar[Jitter] = Jitter(
        min_seconds=1,
        max_seconds=5,
    )
    database: ClassVar[str] = "_remote"
    table_name: ClassVar[str] = "remote_files"
    ttl_hours: ClassVar[float] = 24.0
    cache_key: ClassVar[str] = "remote_files"

    # Not serialized: the dataset embedding this index exports itself via model_dump.
    table: BaseTable = Field(
        ...,
        description="Cache table for the remote file list, provided by the source.",
        exclude=True,
    )
    timeout_seconds: float = Field(
        ...,
        description="Timeout in seconds for fetching the index page, provided by the source.",
        gt=0,
    )
    log_stream: LogStream = Field(
        ...,
        description="Log stream shared by the source.",
        exclude=True,
    )

    _lock: threading.RLock = PrivateAttr(default_factory=threading.RLock)

    def list_files(
        self,
        force: bool = False,
    ) -> list[NSWVGPSIFile]:
        with self._lock:
            if not force:
                self.table.expire()
                _cached: list[dict] | None = self.table.read(
                    key=self.cache_key,
                    strict=False,
                )
                if _cached is not None:
                    return [NSWVGPSIFile.from_dict(_item) for _item in _cached]

            _page: NSWVGIndexPage = NSWVGIndexPage()
            _retry: Retry = self.retry.clone(logstream=self.log_stream)
            _jitter: Jitter = self.jitter.clone(logstream=self.log_stream)
            _text: str | None = None
            try:
                for _attempt in _retry.attempts():
                    with _attempt:
                        _jitter.run()
                        _text = _page.fetch(timeout_seconds=self.timeout_seconds)
            finally:
                _page.client.close()

            if _text is None:
                raise RuntimeError("Failed to fetch NSW VG index page.")

            _files: list[NSWVGPSIFile] = _page.list_remote_files(page_text=_text)
            self.table.write(
                key=self.cache_key,
                data=[_file.export() for _file in _files],
                strict=False,
            )
            return _files
