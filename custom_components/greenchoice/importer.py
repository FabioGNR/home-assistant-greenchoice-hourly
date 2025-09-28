from datetime import date, datetime, timedelta, UTC
from typing import Literal, cast
from .model import ConsumptionData
from .api import GreenchoiceApi
import abc

from homeassistant.core import HomeAssistant
from homeassistant.components.recorder import get_instance
from homeassistant.components.recorder.statistics import (
    async_add_external_statistics,
    get_last_statistics,
    statistics_during_period,
)
from homeassistant.components.recorder.models import (
    StatisticData,
    StatisticMetaData,
    StatisticMeanType,
)
from homeassistant.const import (
    CURRENCY_EURO,
    UnitOfEnergy,
    UnitOfVolume,
)

DOMAIN = "greenchoice"


ConsumptionType = Literal["high"] | Literal["low"] | Literal["total"]


class StatisticImport(abc.ABC):
    def __init__(
        self,
        unique_id: str,
        name: str,
        product_type: str,
        unit: UnitOfEnergy | UnitOfVolume | Literal["€"],
    ):
        self.unique_id = unique_id
        self.name = name
        self.product_type = product_type
        self.unit = unit

    @abc.abstractmethod
    def get_value(self, data: ConsumptionData) -> float:
        pass

    @property
    def statistic_id(self):
        return f"{DOMAIN}:{self.unique_id}"


class ConsumptionImport(StatisticImport):
    def __init__(
        self,
        unique_id: str,
        name: str,
        product_type: str,
        unit: UnitOfEnergy | UnitOfVolume,
        consumption_type: ConsumptionType,
    ):
        super().__init__(unique_id, name, product_type, unit)
        self.consumption_type = consumption_type

    def get_value(self, data: ConsumptionData):
        if self.consumption_type == "low":
            return data.consumption_low
        if self.consumption_type == "high":
            return data.consumption_high
        return data.consumption_total


class CostImport(StatisticImport):
    def __init__(
        self,
        unique_id: str,
        name: str,
        product_type: str,
        consumption_type: ConsumptionType,
    ):
        super().__init__(unique_id, name, product_type, CURRENCY_EURO)
        self.consumption_type = consumption_type

    def get_value(self, data: ConsumptionData):
        if self.consumption_type == "low":
            return data.costs_consumption_low
        if self.consumption_type == "high":
            return data.costs_consumption_high
        return data.costs_total_consumption


STATS: list[StatisticImport] = [
    ConsumptionImport(
        "electricity_consumption_low",
        "Electricity Consumption Low",
        "electricity",
        UnitOfEnergy.KILO_WATT_HOUR,
        "low",
    ),
    ConsumptionImport(
        "electricity_consumption_high",
        "Electricity Consumption High",
        "electricity",
        UnitOfEnergy.KILO_WATT_HOUR,
        "high",
    ),
    ConsumptionImport(
        "electricity_consumption_total",
        "Electricity Consumption Total",
        "electricity",
        UnitOfEnergy.KILO_WATT_HOUR,
        "total",
    ),
    ConsumptionImport(
        "gas_consumption_low",
        "Gas Consumption Low",
        "gas",
        UnitOfVolume.CUBIC_METERS,
        "low",
    ),
    ConsumptionImport(
        "gas_consumption_high",
        "Gas Consumption High",
        "gas",
        UnitOfVolume.CUBIC_METERS,
        "high",
    ),
    ConsumptionImport(
        "gas_consumption_total",
        "Gas Consumption Total",
        "gas",
        UnitOfVolume.CUBIC_METERS,
        "total",
    ),
    CostImport(
        "electricity_cost_total", "Electricity Cost Total", "electricity", "total"
    ),
    CostImport("gas_cost_total", "Gas Cost Total", "gas", "total"),
]


class LastStat:
    def __init__(self, last_stat: datetime | None, _sum: float):
        self.last_stat = last_stat
        self.sum = _sum


class GreenchoiceImporter:
    def __init__(self, hass: HomeAssistant, api: GreenchoiceApi):
        self._api = api
        self._hass = hass

    def import_stat_values(
        self,
        stat: StatisticImport,
        data: dict[datetime, ConsumptionData],
        last_stat: LastStat,
    ):
        metadata = StatisticMetaData(
            mean_type=StatisticMeanType.NONE,
            has_sum=True,
            name=f"Greenchoice {stat.name}",
            source=DOMAIN,
            statistic_id=stat.statistic_id,
            unit_of_measurement=stat.unit,
        )
        statistics: list[StatisticData] = []

        sum = last_stat.sum
        for time, current_data in data.items():
            if last_stat.last_stat is not None and time <= last_stat.last_stat:
                continue
            value = stat.get_value(current_data)
            sum += value
            statistics.append(StatisticData(start=time, state=value, sum=sum))

        async_add_external_statistics(self._hass, metadata, statistics)

    async def get_last_stats(self):
        statistics: dict[StatisticImport, LastStat] = {}
        oldest_stat: datetime | None = None
        for stat in STATS:
            last_stats = await get_instance(self._hass).async_add_executor_job(
                get_last_statistics,
                self._hass,
                1,
                stat.statistic_id,
                True,
                {"sum"},
            )

            if not last_stats:
                last_stats_time = None
                _sum = 0.0
            else:
                last_stats_time = datetime.fromtimestamp(
                    last_stats[stat.statistic_id][0]["start"], UTC
                )
                curr_stat = await get_instance(self._hass).async_add_executor_job(
                    statistics_during_period,
                    self._hass,
                    last_stats_time - timedelta(minutes=30),
                    None,
                    {stat.statistic_id},
                    "hour",
                    None,
                    {"sum"},
                )
                first_stat = curr_stat[stat.statistic_id][0]
                _sum = cast(float, first_stat["sum"])
                last_stats_time = datetime.fromtimestamp(first_stat["start"], UTC)
                if oldest_stat is None or last_stats_time < oldest_stat:
                    oldest_stat = last_stats_time
            statistics[stat] = LastStat(last_stats_time, _sum)
        return statistics, oldest_stat

    async def import_data(self):
        last_stats, first_stat = await self.get_last_stats()

        today = date.today()
        max_days = 21  # start with last 3 weeks
        if first_stat is not None:
            days_since = (today - first_stat.date()).days
            max_days = max(max_days, days_since)
        days = [today - timedelta(days=n) for n in range(max_days, 0, -1)]

        combined_product_consumption: dict[str, dict[datetime, ConsumptionData]] = {}
        for day in days:
            consumption = await self._api.get_hourly_readings(day)
            for entry in consumption.entries:
                product_data = combined_product_consumption.setdefault(
                    entry.product_type, {}
                )
                product_data.update(entry.values)

        for stat in STATS:
            if stat.product_type in combined_product_consumption:
                self.import_stat_values(
                    stat,
                    combined_product_consumption[stat.product_type],
                    last_stats[stat],
                )

    async def clear_data(self):
        ids = [stat.statistic_id for stat in STATS]
        get_instance(self._hass).async_clear_statistics(list(ids))
