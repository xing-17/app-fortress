from __future__ import annotations

from typing import ClassVar

from app.internal.constant.frequencyoption import FrequencyOption
from app.resource.source.abs.dataset import ABSDataset


class JobVacanciesQuarterDataset(ABSDataset):
    """
    ABS Job Vacancies (dataflow JV), partitioned by snapshotdate

    Args:
    ----------
        name (str):
            Dataset name, fixed to "job_vacancies_quarter"
        partitions (list[str]):
            Partition keys of the dataset, fixed to ["snapshotdate"]
        frequency (FrequencyOption):
            Update frequency, fixed to FrequencyOption.QUARTER
        dataflow_id (str):
            ABS dataflow id, fixed to "JV"

    """

    name: ClassVar[str] = "job_vacancies_quarter"
    partitions: ClassVar[list[str]] = ["snapshotdate"]
    frequency: ClassVar[FrequencyOption] = FrequencyOption.QUARTER
    description: ClassVar[str] = (
        "Estimates of job vacancies classified by industry, "
        "sector and state/territory. "
        "Job vacancies data relate to the number of vacancies which exist on the actual survey reference date only, "
        "and not for a monthly or quarterly period. "
    )
    dataflow_id: ClassVar[str] = "JV"
