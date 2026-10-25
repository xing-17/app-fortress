from __future__ import annotations

from typing import ClassVar

from app.internal.constant.frequencyoption import FrequencyOption
from app.resource.source.abs.dataset import ABSDataset


class JobVacanciesDataset(ABSDataset):
    """
    ABS Job Vacancies (dataflow JV), partitioned by snapshotdate

    Args:
    ----------
        name (str):
            Dataset name, fixed to "job_vacancies"
        partitions (list[str]):
            Partition keys of the dataset, fixed to ["snapshotdate"]
        frequency (FrequencyOption):
            Update frequency, fixed to FrequencyOption.QUARTER
        dataflow_id (str):
            ABS dataflow id, fixed to "JV"

    """

    name: ClassVar[str] = "job_vacancies"
    partitions: ClassVar[list[str]] = ["snapshotdate"]
    frequency: ClassVar[FrequencyOption] = FrequencyOption.QUARTER
    description: ClassVar[str] = (
        "Dataset for ABS Job Vacancies, results of the quarterly Job Vacancies Survey containing estimates of job vacancies classified by industry, sector and state/territory."
    )
    dataflow_id: ClassVar[str] = "JV"
