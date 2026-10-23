from __future__ import annotations

from pydantic import ConfigDict, Field

from app.internal.abstract.domain import IAbstractDomain


class MachineSnapshot(IAbstractDomain):
    """
    One reading of the host machine, immutable

    Network counters are totals since boot, the reader takes the difference between two
    snapshots to get a rate. The `proc_*` and `net_*` fields are None when that part could
    not be read.

    Attributes:
    ----------
        timestamp (float): Epoch seconds the reading was taken
        cpu_percent (float): CPU usage of the machine
        mem_percent (float): Memory usage of the machine
        mem_used_mb (int): Memory in use in MB
        mem_total_mb (int): Memory installed in MB
        swap_percent (float): Swap usage
        disk_percent (float): Usage of the root disk
        disk_used_mb (int): Root disk in use in MB
        disk_total_mb (int): Root disk size in MB
        proc_mem_mb (int | None): Resident memory of this process in MB
        proc_mem_percent (float | None): Share of the machine memory held by this process
        proc_cpu_percent (float | None): CPU usage of this process, 100 is one full core
        proc_workers (int | None): Threads of this process
        net_sent_mb (int | None): Bytes sent since boot, in MB
        net_recv_mb (int | None): Bytes received since boot, in MB

    """

    model_config = ConfigDict(frozen=True)

    timestamp: float = Field(
        ...,
        description="Epoch seconds the reading was taken",
    )
    cpu_percent: float = Field(
        ...,
        description="CPU usage of the machine",
    )
    mem_percent: float = Field(
        ...,
        description="Memory usage of the machine",
    )
    mem_used_mb: int = Field(
        ...,
        description="Memory in use in MB",
    )
    mem_total_mb: int = Field(
        ...,
        description="Memory installed in MB",
    )
    swap_percent: float = Field(
        ...,
        description="Swap usage",
    )
    disk_percent: float = Field(
        ...,
        description="Usage of the root disk",
    )
    disk_used_mb: int = Field(
        ...,
        description="Root disk in use in MB",
    )
    disk_total_mb: int = Field(
        ...,
        description="Root disk size in MB",
    )
    proc_mem_mb: int | None = Field(
        None,
        description="Resident memory of this process in MB",
    )
    proc_mem_percent: float | None = Field(
        None,
        description="Share of the machine memory held by this process",
    )
    proc_cpu_percent: float | None = Field(
        None,
        description="CPU usage of this process, 100 is one full core",
    )
    proc_workers: int | None = Field(
        None,
        description="Threads of this process",
    )
    net_sent_mb: int | None = Field(
        None,
        description="Bytes sent since boot, in MB",
    )
    net_recv_mb: int | None = Field(
        None,
        description="Bytes received since boot, in MB",
    )
