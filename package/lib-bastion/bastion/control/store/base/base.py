from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from bastion.control.run.run import IRunLike
    from bastion.domain.run import RunModel


@runtime_checkable
class IStoreLike(Protocol):
    # store attributes
    name: str

    def __enter__(self) -> IStoreLike: ...

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: Any | None,
    ) -> None: ...

    def init(self) -> None: ...

    def save_run(
        self,
        run: IRunLike | RunModel,
    ) -> None: ...

    def get_run(
        self,
        run_id: str,
    ) -> IRunLike | None: ...

    def list_runs(
        self,
        compute_name: str | None = None,
        since: datetime | None = None,
        until: datetime | None = None,
        limit: int | None = None,
    ) -> list[IRunLike]: ...

    def delete_run(
        self,
        run_id: str,
    ) -> None: ...
