from __future__ import annotations

from typing import ClassVar

from app.internal.constant.frequencyoption import FrequencyOption
from app.resource.source.nswvg.dataset import NSWVGDataset
from app.resource.source.nswvg.provision import NSWVGProvisionKind


class WeekPSIDataset(NSWVGDataset):
    """
    NSW VG weekly PSI dataset, partitioned by date

    Shares its schema with `YearPSIDataset`, the date is the Monday the week is published.

    Args:
    ----------
        name (str):
            Dataset name, fixed to "psi_week"
        partitions (list[str]):
            Partition keys of the dataset, fixed to ["date"]
        frequency (FrequencyOption):
            Update frequency, fixed to FrequencyOption.WEEK
        provision_kind (NSWVGProvisionKind):
            Provision kind, fixed to NSWVGProvisionKind.WEEK

    Methods:
    ----------
        run(params: dict | None = None) -> list[BaseAssetfile]:
            `{"mode": "delta"}` (default) loads the provision weeks without assetfile;
            `{"mode": "full"}` loads every provision week.

    """

    name: ClassVar[str] = "psi_week"
    partitions: ClassVar[list[str]] = ["date"]
    description: ClassVar[str] = "Dataset for NSW VG weekly PSI."
    frequency: ClassVar[FrequencyOption] = FrequencyOption.WEEK
    provision_kind: ClassVar[NSWVGProvisionKind] = NSWVGProvisionKind.WEEK
