from __future__ import annotations

import re
import threading
from datetime import datetime
from enum import StrEnum
from typing import ClassVar

from pydantic import Field, PrivateAttr, model_validator

from app.internal.abstract.domain import IAbstractDomain
from app.internal.logstream import LogStream
from app.resource._client.web.client import WebClient
from app.resource._client.web.headers import WebHeaders
from app.resource.accessory.jitter.jitter import Jitter
from app.resource.accessory.retry.retry import Retry
from app.resource.store._common._table import BaseTable

INDEX_URL: str = "https://valuation.property.nsw.gov.au/embed/propertySalesInformation/"
WEEK_FILE_HREF: re.Pattern = re.compile(r'href="(?P<url>https://[^"]*/__psi/weekly/(?P<key>\d+)\.zip)"')
YEAR_FILE_HREF: re.Pattern = re.compile(r'href="(?P<url>https://[^"]*/__psi/yearly/(?P<key>\d+)\.zip)"')
CRITICAL_ERROR_EXPRS: list[str] = [
    "Request blocked by challenge*",
    "400 Client Error*",
    "401 Client Error*",
    "403 Client Error*",
    "404 Client Error*",
]


class NSWVGPSIFileKind(StrEnum):
    WEEK = "week"
    YEAR = "year"


class NSWVGPSIFile(IAbstractDomain):
    key: str = Field(
        ...,
        description="The key of the NSWVG PSI file",
    )
    url: str = Field(
        ...,
        description="The URL of the NSWVG PSI file",
    )
    kind: NSWVGPSIFileKind = Field(
        ...,
        description="The kind of the NSWVG PSI file",
    )
    partitions: dict[str, str] | None = Field(
        default=None,
        description="The partitions derived from the key of the NSWVG PSI file",
    )

    @model_validator(mode="after")
    def _derive_partitions(self) -> NSWVGPSIFile:
        if not self.partitions:
            if self.kind == NSWVGPSIFileKind.WEEK:
                _dt: datetime = datetime.strptime(self.key, "%Y%m%d")
                _p = {"date": _dt.strftime("%Y-%m-%d")}
            else:
                _p = {"year": self.key}
            object.__setattr__(self, "partitions", _p)
        return self


class NSWVGIndex(IAbstractDomain):
    """
    Index of remote NSW VG PSI files, scraped from the public index page.

    Kept out of `datasets/` on purpose, it is not an ETL dataset and must not be auto-discovered.

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
    url: ClassVar[str] = INDEX_URL
    href_week_patterns: ClassVar[re.Pattern] = WEEK_FILE_HREF
    href_year_patterns: ClassVar[re.Pattern] = YEAR_FILE_HREF
    critical_error_exprs: ClassVar[list[str]] = CRITICAL_ERROR_EXPRS

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

    def _fetch_index_page(self) -> str:
        client: WebClient = WebClient()
        headers: dict = WebHeaders.build(
            updates={
                "Referer": "https://valuation.property.nsw.gov.au/embed/propertySalesInformation",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "cross-site",
                "Sec-Fetch-User": "?1",
                "Upgrade-Insecure-Requests": "1",
            },
        )
        _retry: Retry = self.retry.clone(logstream=self.log_stream)
        _jitter: Jitter = self.jitter.clone(logstream=self.log_stream)
        _index_page: str | None = None
        try:
            for _attempt in _retry.attempts():
                with _attempt:
                    _jitter.run()
                    _response = client.request(
                        method="GET",
                        url=self.url,
                        headers=headers,
                        params=None,
                        stream=False,
                        timeout=self.timeout_seconds,
                    )
                    _index_page: str = _response.text
        finally:
            client.close()
        if _index_page is None:
            raise RuntimeError("Failed to fetch NSW VG index page.")
        return _index_page

    def _parse_files(
        self,
        index_page: str,
    ) -> list[NSWVGPSIFile]:
        _index_page: str = index_page
        _files: list[NSWVGPSIFile] = []
        for match in self.href_week_patterns.finditer(_index_page):
            _key: str = match.group("key")
            _url: str = match.group("url")
            _file: NSWVGPSIFile = NSWVGPSIFile(
                key=_key,
                url=_url,
                kind=NSWVGPSIFileKind.WEEK,
            )
            _files.append(_file)
        for match in self.href_year_patterns.finditer(_index_page):
            _key: str = match.group("key")
            _url: str = match.group("url")
            _file: NSWVGPSIFile = NSWVGPSIFile(
                key=_key,
                url=_url,
                kind=NSWVGPSIFileKind.YEAR,
            )
            _files.append(_file)
        return _files

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

            _index_page: str = self._fetch_index_page()
            _files: list[NSWVGPSIFile] = self._parse_files(_index_page)
            self.table.write(
                key=self.cache_key,
                data=[_file.export() for _file in _files],
                strict=False,
            )
            return _files
