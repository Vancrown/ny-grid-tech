"""
NYISO Zonal Energy Data Loader using Agentics Framework

This module provides utilities to load and process NYISO market data
from per-zone CSV files such as CAPITL.csv, CENTRL.csv, DUNWOD.csv, etc.

Important note
--------------
To preserve compatibility with the rest of the codebase, we keep the
variable name `region`, even though it now represents an NYISO zone.

Examples:
    region = "CAPITL"
    region = "CENTRL"
    region = "NYC"

We also preserve the logical distinction between:
- actual data
- forecast data

For now, both data_version="actual" and data_version="forecast"
resolve to the same per-zone CSV file.
"""

from pathlib import Path
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

from agentics import AG
from typing import Optional, Dict, Union, Tuple, Literal
import pandas as pd
import numpy as np

from .schemas import (
    EnergyDataRecord,
    MetricStats,
    SummaryStats,
    DateRange,
    BatteryParams,
)


class EnergyDataLoader:
    """
    Load NYISO zonal data from per-zone CSV files.

    Parameters
    ----------
    region : str
        NYISO zone name stored in the existing `region` variable.
        Supported values include:
        CAPITL, CENTRL, DUNWOD, GENESE, H_Q, HUD_VL, LONGIL,
        MHK_VL, MILLWD, NORTH, NPX, NYC, O_H, PJM, WEST.
    data_dir : Union[str, Path] | None
        Directory containing the per-zone CSV files.
        Defaults to <this_file>/data/NYISO_zones.
    data_version : Literal["actual", "forecast"]
        Logical data source requested by the caller.
        For now, both "actual" and "forecast" read the same zone CSV.
    forecast_type : Optional[Literal["LSTM", "NOISE", "RF", "TLLM"]]
        Forecast label used only as metadata when data_version="forecast".
    """

    VALID_REGIONS = {
        "CAPITL",
        "CENTRL",
        "DUNWOD",
        "GENESE",
        "H_Q",
        "HUD_VL",
        "LONGIL",
        "MHK_VL",
        "MILLWD",
        "NORTH",
        "NPX",
        "NYC",
        "O_H",
        "PJM",
        "WEST",
    }

    VALID_FORECAST_TYPES = {"LSTM", "NOISE", "RF", "TLLM"}

    def __init__(
        self,
        region: str,
        data_dir: Union[str, Path, None] = None,
        data_version: Literal["actual", "forecast"] = "actual",
        forecast_type: Optional[Literal["LSTM", "NOISE", "RF", "TLLM"]] = None,
    ):
        """
        Initialize the loader for one NYISO zone, stored in the `region` field.

        Args:
            region: NYISO zone name, used as the existing `region` variable.
            data_dir: Directory containing the per-zone CSV files.
            data_version: Logical source kind ("actual" or "forecast").
            forecast_type: Forecast label when data_version="forecast".
        """
        if data_dir is None:
            self.data_dir = Path(__file__).parent / "data" / "NYISO_zones"
        else:
            self.data_dir = Path(data_dir)

        # Kept as `region` for compatibility, but values are NYISO zones.
        self.region = region.upper()
        self.data_version = data_version.lower()
        self.forecast_type = (
            forecast_type.upper() if forecast_type is not None else None
        )

        self.data: Optional[AG] = None

        # Validate inputs early so configuration errors fail fast.
        self._validate_init()

    def _validate_init(self):
        """Validate NYISO zone name, data version, and forecast settings."""
        if self.region not in self.VALID_REGIONS:
            raise ValueError(
                f"Region '{self.region}' not supported. "
                f"Available NYISO zones: {sorted(self.VALID_REGIONS)}"
            )

        if self.data_version not in {"actual", "forecast"}:
            raise ValueError("data_version must be either 'actual' or 'forecast'.")

        if self.data_version == "forecast":
            if not self.forecast_type:
                raise ValueError(
                    "forecast_type is required when data_version='forecast'."
                )
            if self.forecast_type not in self.VALID_FORECAST_TYPES:
                raise ValueError(
                    f"Unsupported forecast_type '{self.forecast_type}'. "
                    f"Supported: {sorted(self.VALID_FORECAST_TYPES)}"
                )

    def _resolve_filename(self) -> Path:
        """
        Resolve the CSV path for the selected NYISO zone.

        Current behavior
        ----------------
        Both actual and forecast requests point to the same per-zone CSV file.

        Example:
            region='CAPITL' -> <data_dir>/CAPITL.csv
        """
        return self.data_dir / f"{self.region}.csv"

    def load_region_data(self) -> AG:
        """
        Load the selected NYISO zonal CSV using Agentics.

        Returns
        -------
        AG
            Agentics object containing EnergyDataRecord states.

        Raises
        ------
        FileNotFoundError
            If the zone CSV does not exist.
        """
        file_path = self._resolve_filename()
        if not file_path.exists():
            raise FileNotFoundError(f"Region data file not found: {file_path}")

        energy_data = AG.from_csv(file_path, atype=EnergyDataRecord)

        # Stamp provenance onto each record.
        for state in energy_data.states:
            # Keep using `region` for compatibility; value is the NYISO zone.
            if hasattr(state, "region"):
                state.region = self.region

            if hasattr(state, "source_kind"):
                state.source_kind = self.data_version

            if hasattr(state, "forecast_type"):
                state.forecast_type = (
                    self.forecast_type if self.data_version == "forecast" else None
                )

        self.data = energy_data
        return self.data

    async def get_filtered_data(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        price_range: Optional[Tuple[float, float]] = None,
    ) -> AG:
        """
        Filter loaded NYISO zonal data by date range and/or price range.

        Notes
        -----
        This assumes each state has:
        - timestamps
        - prices

        If your CSV/schema uses `lmp` instead of `prices`, either:
        1. rename the CSV column to `prices`, or
        2. map `lmp -> prices` in the schema.
        """
        has_date_filter = bool(start_date or end_date)
        start_day = (
            np.datetime64(pd.to_datetime(start_date).date()) if start_date else None
        )
        end_day = np.datetime64(pd.to_datetime(end_date).date()) if end_date else None

        has_price_filter = bool(price_range)
        if has_price_filter:
            min_price, max_price = price_range

        async def _filter_reduce(states: list):
            if not states:
                return []

            ts_arr = np.array([s.timestamps for s in states], dtype="datetime64[ns]")
            day_arr = ts_arr.astype("datetime64[D]")

            pr_arr = None
            if has_price_filter:
                pr_arr = pd.to_numeric(
                    [getattr(s, "prices", np.nan) for s in states],
                    errors="coerce",
                ).to_numpy()

            mask = np.ones(len(states), dtype=bool)

            if has_date_filter:
                if start_day is not None:
                    mask &= day_arr >= start_day
                if end_day is not None:
                    mask &= day_arr <= end_day

            if has_price_filter:
                mask &= np.isfinite(pr_arr)
                mask &= (pr_arr >= min_price) & (pr_arr <= max_price)

            if mask.all():
                return states
            if not mask.any():
                return []

            idx = np.nonzero(mask)[0]
            return [states[i] for i in idx]

        if self.data is None:
            raise RuntimeError("No data loaded. Call load_region_data() first.")

        filtered_states = await self.data.areduce(_filter_reduce)
        return AG(atype=EnergyDataRecord, states=filtered_states)

    @staticmethod
    async def get_summary_stats_from_ag(
        ag_data: AG, column: Optional[str] = None
    ) -> SummaryStats | Dict:
        """
        Compute summary statistics for loaded NYISO zonal data.

        The returned SummaryStats object continues to use the `region` field,
        but that field now contains the NYISO zone name.
        """
        prices = np.array(
            [s.prices for s in ag_data.states if s.prices is not None],
            dtype=float,
        )
        consumption = np.array(
            [s.consumption for s in ag_data.states if s.consumption is not None],
            dtype=float,
        )
        timestamps = [
            s.timestamps for s in ag_data.states if getattr(s, "timestamps", None)
        ]

        async def summarize(arr: np.ndarray) -> MetricStats:
            if arr.size == 0:
                return MetricStats()

            return MetricStats(
                count=int(arr.size),
                min=float(np.min(arr)),
                max=float(np.max(arr)),
                avg=float(np.mean(arr)),
                median=float(np.median(arr)),
                p25=float(np.percentile(arr, 25)),
                p75=float(np.percentile(arr, 75)),
                std=float(np.std(arr)),
                var=float(np.var(arr)),
            )

        stats_obj = SummaryStats(
            region=ag_data[0].region if len(ag_data.states) else None,
            total_records=len(ag_data.states),
            date_range=DateRange(
                start=min(timestamps) if timestamps else None,
                end=max(timestamps) if timestamps else None,
            ),
            prices=await summarize(prices),
            consumption=await summarize(consumption),
        )

        if column:
            if column not in ["prices", "consumption"]:
                raise ValueError("Column must be 'prices' or 'consumption'.")
            return AG(atype=MetricStats, states=[getattr(stats_obj, column)])

        return AG(atype=SummaryStats, states=[stats_obj])


class BatteryDataLoader:
    """
    Battery parameter helper based on load summary statistics.

    This class is unchanged conceptually: it computes battery sizing from
    load statistics such as p25 and p75.
    """

    def __init__(
        self,
        load_stats: Dict[str, float],
        duration_hours: float = 4.0,
        soc_init=0.5,
        soc_min=0.0,
        soc_max=1.0,
        eta_c=0.95,
        eta_d=0.95,
        soc_target=0.5,
    ):
        """
        Args:
            load_stats: Must include 'p25' and 'p75' values in MW.
            duration_hours: Battery duration in hours.
        """
        if "p25" not in load_stats or "p75" not in load_stats:
            raise ValueError("load_stats must include 'p25' and 'p75' values in MW.")

        self.load_stats = load_stats
        self.duration_hours = duration_hours
        self.soc_init = soc_init
        self.soc_min = soc_min
        self.soc_max = soc_max
        self.eta_c = eta_c
        self.eta_d = eta_d
        self.soc_target = soc_target

    def compute_battery_params(self) -> BatteryParams:
        """
        Compute battery capacity and charge/discharge limits from
        the interquartile range of load statistics.
        """
        p25, p75 = self.load_stats["p25"], self.load_stats["p75"]

        iqr_range_MW = p75 - p25
        capacity_MWh = iqr_range_MW * self.duration_hours
        cmax_MW = capacity_MWh / self.duration_hours
        dmax_MW = cmax_MW

        return BatteryParams(
            capacity_MWh=round(capacity_MWh, 2),
            cmax_MW=round(cmax_MW, 2),
            dmax_MW=round(dmax_MW, 2),
            soc_init=self.soc_init,
            soc_min=self.soc_min,
            soc_max=self.soc_max,
            eta_c=self.eta_c,
            eta_d=self.eta_d,
            soc_target=self.soc_target,
        )

    def summary(self) -> Dict[str, float]:
        """Return the computed battery specification summary."""
        params = self.compute_battery_params()
        return {
            "Capacity (MWh)": params.capacity_MWh,
            "Charge Power (MW)": params.cmax_MW,
            "Discharge Power (MW)": params.dmax_MW,
            "Efficiency (Charge/Discharge)": (params.eta_c, params.eta_d),
            "Duration (hours)": self.duration_hours,
        }