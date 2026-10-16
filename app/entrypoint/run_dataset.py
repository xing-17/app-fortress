from __future__ import annotations

from typing import Any

from app.resource._global.sources import GlobalSources
from app.resource.asset._common._assetfile import BaseAssetfile
from app.resource.source._common._dataset import BaseDataset
from app.resource.source._common._source import BaseSource


def handler(
    payload: dict[str, Any] | None = None,
    context: Any | None = None,
) -> dict[str, Any]:
    """
    Payload schema:

    Example:
    ----------
        payload = {
            "source": "<source_name>",
            "dataset": "<dataset_name>",
            "params": { ... }
        }

    """
    _event: dict[str, Any] | None = payload or {}

    # Get the source and init from event
    _source_name: str = _event.get("source")
    _source: BaseSource | None = GlobalSources.get_source(_source_name)
    if not _source:
        raise ValueError(f"Source `{_source_name}` not found")

    # Get the dataset name and parameters from the event
    _dataset_name: str = _event.get("dataset")
    _dataset: BaseDataset | None = _source.dataset(name=_dataset_name)
    if _dataset is None:
        raise ValueError(f"Dataset `{_dataset_name}` not found")

    _params: dict[str, Any] = _event.get("params", {})
    _files: list[BaseAssetfile] = _dataset.run(params=_params)
    _result: dict[str, Any] = {
        "ok": True,
        "source": _source_name,
        "dataset": _dataset_name,
        "assetfiles": [f.uri for f in _files],
    }
    return {
        "ok": True,
        "results": [_result],
    }
