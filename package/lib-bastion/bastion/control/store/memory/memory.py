from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from bastion.control.run.run import Run
from bastion.control.store.base.base import IStoreLike

if TYPE_CHECKING:
    from bastion.control.run.run import IRunLike
    from bastion.domain.run import RunModel


class MemoryStore(IStoreLike):
    def __init__(
        self,
        name: str = "default",
    ) -> None:
        self.name: str = name
        self._runs: dict[str, RunModel] = {}

    def init(self) -> None:
        # No ops for memory
        pass

    def __enter__(self) -> MemoryStore:
        return self

    def __exit__(self, *_) -> None:
        # No action needed for memory store on exit
        pass

    def save_run(
        self,
        run: IRunLike | RunModel,
    ) -> None:
        domain = run.domain if isinstance(run, Run) else run
        self._runs[domain.id] = domain.model_copy(deep=True)

    def get_run(
        self,
        run_id: str,
    ) -> IRunLike | None:
        _model: RunModel | None = self._runs.get(run_id)
        if _model is None:
            return None
        else:
            return Run.from_domain(_model)

    def list_runs(
        self,
        compute_name: str | None = None,
        since: datetime | None = None,
        until: datetime | None = None,
        limit: int | None = None,
    ) -> list[IRunLike]:
        # Build a list of runs that match the given filters
        _all_runs: list[IRunLike] = []
        for domain in self._runs.values():
            if compute_name is not None and domain.compute_name != compute_name:
                continue
            if since and domain.created_at < since:
                continue
            if until and domain.created_at > until:
                continue
            _all_runs.append(Run.from_domain(domain))

        # Slice the list if limit is specified
        if limit is not None:
            _all_runs = _all_runs[:limit]
        return _all_runs

    def delete_run(
        self,
        run_id: str,
    ) -> None:
        if run_id in self._runs:
            del self._runs[run_id]
