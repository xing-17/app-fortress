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
            "items": [
                {
                    "source": "<source_name>",
                    "dataset": "<dataset_name>",
                    "params": {
                        "<param_key>": "<param_value>"
                    }
                }
            ]
        }

    """
    _payload: list[dict[str, Any]] | None = (payload or {}).get("items", [])

    # Extract the payloads from the event
    _results: list[dict[str, Any]] = []
    for _params in _payload:
        # Get the source and init from event
        _source_name: str = _params.get("source")
        _source: BaseSource | None = GlobalSources.get_source(_source_name)
        if not _source:
            raise ValueError(f"Source `{_source_name}` not found")

        # Get the dataset name and parameters from the payload
        _dataset_name: str = _params.get("dataset")
        _dataset: BaseDataset | None = _source.dataset(name=_dataset_name)
        if _dataset is None:
            raise ValueError(f"Dataset `{_dataset_name}` not found")

        # Run the dataset with the provided parameters and collect the resulting asset files
        _params: dict[str, Any] = _params.get("params", {})
        _files: list[BaseAssetfile] = _dataset.run(params=_params)
        _result: dict[str, Any] = {
            "ok": True,
            "source": _source_name,
            "dataset": _dataset_name,
            "assetfiles": [f.uri for f in _files],
        }
        _results.append(_result)

    return {
        "ok": True,
        "results": _results,
    }
