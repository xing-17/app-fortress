from __future__ import annotations

import csv
import io
from datetime import datetime
from typing import Any, ClassVar

import polars as pl
import requests

from app.internal.constant.frequencyoption import FrequencyOption
from app.internal.model.definition.desc import ColumnDesc
from app.resource.source.rba.dataset import RBADataset

_BASE_URL: str = "https://www.rba.gov.au/statistics/tables/csv/j1-{slug}.csv"
_SLUGS: tuple[str, ...] = (
    "headline-inflation",
    "underlying-inflation",
    "gdp-growth",
    "dfd-growth",
    "wpi-growth",
    "unemployment-rate",
    "cash-rate",
    "exchange-rate",
    "net-exports",
    "terms-of-trade",
    "historical---twi",
    "historical---brent-oil-price",
    "star-variables",
)
_SCHEMA: dict[str, Any] = {
    "date": pl.Datetime("us"),
    "series_id": pl.String,
    "value": pl.Float64,
    "description": pl.String,
    "units": pl.String,
    "table": pl.String,
    "frequency": pl.String,
    "series_type": pl.String,
    "source": pl.String,
    "target_quarter": pl.Datetime("us"),
}


class J1MarketEconomicForecastQuarterDataset(RBADataset):
    """
    RBA Market Economic Forecast - Quarterly Collection (table J1), partitioned by snapshotdate

    Args:
    ----------
        name (str):
            Dataset name, fixed to "j1_market_economic_forecast_quarter"
        partitions (list[str]):
            Partition keys of the dataset, fixed to ["snapshotdate"]
        frequency (FrequencyOption):
            Update frequency, fixed to FrequencyOption.QUARTER
        description (str):
            Dataset description, covering content, unit and coverage
        table_no (str):
            RBA statistical table number, fixed to "j1"

    """

    name: ClassVar[str] = "j1_market_economic_forecast_quarter"
    partitions: ClassVar[list[str]] = ["snapshotdate"]
    frequency: ClassVar[FrequencyOption] = FrequencyOption.QUARTER
    description: ClassVar[str] = (
        "Market Economists' Forecasts (RBA J1), quarterly survey, from 2001, original. "
        "Median, mean, low and high forecasts, number of respondents and dispersion, by survey date and target quarter, for: "
        "headline and underlying inflation, real GDP and DFD growth, WPI growth, unemployment rate, cash rate (per cent), "
        "exchange rate (USD), net exports and terms of trade, TWI and Brent oil price, plus long-run inflation expectations. "
        "Forecasts of future values, not outcomes, actuals are in g1, i1 and f1_1."
    )
    table_no: ClassVar[str] = "j1"
    column_descs: ClassVar[list[ColumnDesc]] = [
        *[_c for _c in RBADataset.column_descs if _c.name != "date"],
        ColumnDesc(
            name="date",
            description="Survey date of the forecast.",
        ),
        ColumnDesc(
            name="target_quarter",
            description="Quarter the forecast refers to, as dated in the source CSV. It is null for the long-run and potential-output estimate series.",
        ),
    ]

    # RBA publishes no j1-data.csv
    # rbadata Excel fallback is broken (duplicate series_id)
    # so pull the per-indicator CSVs
    def _request(self) -> pl.DataFrame:
        _frames: list[pl.DataFrame] = [self._read_csv(_slug) for _slug in _SLUGS]
        return pl.concat(_frames)

    def _read_csv(self, slug: str) -> pl.DataFrame:
        _resp = requests.get(
            _BASE_URL.format(slug=slug),
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=30,
        )
        _resp.raise_for_status()
        _rows: list[list[str]] = list(csv.reader(io.StringIO(_resp.content.decode("utf-8-sig"))))

        _meta: dict[str, list[str]] = {}
        _start: int = -1
        for _i, _row in enumerate(_rows):
            if not _row:
                continue
            _meta[_row[0]] = _row
            if _row[0] == "Series ID":
                _start = _i + 1
                break
        if _start < 0:
            raise ValueError(f"'Series ID' row not found in j1-{slug}.csv")

        _ids, _descs, _units = _meta["Series ID"], _meta["Description"], _meta["Units"]
        _freqs, _types = _meta["Frequency"], _meta["Type"]

        # Forecast files lead with survey date, then target quarter (Units == "Date")
        _target_col: int | None = 1 if len(_units) > 1 and _units[1] == "Date" else None
        _first_value_col: int = 2 if _target_col else 1

        _records: list[dict[str, Any]] = []
        for _row in _rows[_start:]:
            if not _row or not _row[0].strip():
                continue
            _date = datetime.strptime(_row[0].strip(), "%d/%m/%Y")
            _target = datetime.strptime(_row[_target_col].strip(), "%d/%m/%Y") if _target_col else None
            for _c in range(_first_value_col, min(len(_row), len(_ids))):
                if not _row[_c].strip():
                    continue

                _records.append(
                    {
                        "date": _date,
                        "series_id": _ids[_c],
                        "value": float(_row[_c]),
                        "description": _descs[_c],
                        "units": _units[_c],
                        "table": "J1",
                        "frequency": _freqs[_c] if _c < len(_freqs) else "",
                        "series_type": _types[_c] if _c < len(_types) else "",
                        "source": "csv",
                        "target_quarter": _target,
                    }
                )
        return pl.DataFrame(_records, schema=_SCHEMA)
