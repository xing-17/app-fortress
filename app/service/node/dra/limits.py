from __future__ import annotations

from pydantic import ConfigDict, Field

from app.internal.abstract.domain import IAbstractDomain


class DRALimits(IAbstractDomain):
    """
    Resource limits of one DRA session

    Attributes:
    ----------
        timeout_seconds (float):
            Wall-clock limit of one query, the query is interrupted when exceeded, default is 120
        max_rows (int):
            Row cap of one result, extra rows are dropped and the result is marked truncated, default is 10_000
        max_result_mb (float):
            Size cap of one result in MB, extra rows are dropped and the result is marked truncated, default is 128
        memory_limit_mb (int):
            Memory limit of the engine, only covers buffer-managed operators, default is 1024
        threads (int):
            Worker threads of the engine, default is 2

    """

    model_config = ConfigDict(frozen=True)

    timeout_seconds: float = Field(
        default=120.0,
        description="Wall-clock limit of one query, default is 120",
        gt=0,
    )
    max_rows: int = Field(
        default=10_000,
        ge=1,
        description="Row cap of one result, extra rows are dropped and the result is marked truncated, default is 10_000",
    )
    max_result_mb: float = Field(
        default=128.0,
        gt=0,
        description="Size cap of one result in MB, extra rows are dropped and the result is marked truncated, default is 128",
    )
    memory_limit_mb: int = Field(
        default=1024,
        ge=16,
        description="Memory limit of the engine, only covers buffer-managed operators, default is 1024",
    )
    threads: int = Field(default=2, ge=1, description="Worker threads of the engine, default is 2")
