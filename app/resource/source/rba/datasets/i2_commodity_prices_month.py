from __future__ import annotations

from typing import ClassVar

from app.internal.constant.frequencyoption import FrequencyOption
from app.resource.source.rba.dataset import RBADataset


class I2CommodityPricesMonthDataset(RBADataset):
    """
    RBA Commodity Prices (table I2) - Monthly, partitioned by snapshotdate

    Args:
    ----------
        name (str):
            Dataset name, fixed to "i2_commodity_prices_month"
        partitions (list[str]):
            Partition keys of the dataset, fixed to ["snapshotdate"]
        frequency (FrequencyOption):
            Update frequency, fixed to FrequencyOption.MONTH
        description (str):
            Dataset description, covering content, unit and coverage
        table_no (str):
            RBA statistical table number, fixed to "i2"

    """

    name: ClassVar[str] = "i2_commodity_prices_month"
    partitions: ClassVar[list[str]] = ["snapshotdate"]
    frequency: ClassVar[FrequencyOption] = FrequencyOption.MONTH
    description: ClassVar[str] = (
        "Commodity Prices (RBA I2), monthly, from Jul 1982, index (2024/25 = 100), original. "
        "Index of Australian commodity export prices: all items, rural, non-rural, base metals and bulk commodities "
        "(export price based, and spot price based from 2009), "
        "each in three currencies: A$, US$ and SDR. "
        "Price indices, not $ per tonne prices."
    )
    table_no: ClassVar[str] = "i2"
