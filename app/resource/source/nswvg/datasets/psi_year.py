from __future__ import annotations

from typing import ClassVar

from app.internal.constant.frequencyoption import FrequencyOption
from app.resource.source.nswvg.dataset import NSWVGDataset
from app.resource.source.nswvg.provision import NSWVGProvisionKind


class YearPSIDataset(NSWVGDataset):
    """
    NSW VG yearly PSI dataset, partitioned by year

    Args:
    ----------
        name (str):
            Dataset name, fixed to "psi_year"
        partitions (list[str]):
            Partition keys of the dataset, fixed to ["year"]
        frequency (FrequencyOption):
            Update frequency, fixed to FrequencyOption.YEAR
        provision_kind (NSWVGProvisionKind):
            Provision kind, fixed to NSWVGProvisionKind.YEAR

    Methods:
    ----------
        run(params: dict | None = None) -> list[BaseAssetfile]:
            `{"mode": "delta"}` (default) loads the provision years without assetfile;
            `{"mode": "full"}` loads every provision year.

    """

    name: ClassVar[str] = "psi_year"
    partitions: ClassVar[list[str]] = ["year"]
    description: ClassVar[str] = "Dataset for NSW VG yearly property sales information."
    frequency: ClassVar[FrequencyOption] = FrequencyOption.YEAR
    provision_kind: ClassVar[NSWVGProvisionKind] = NSWVGProvisionKind.YEAR
