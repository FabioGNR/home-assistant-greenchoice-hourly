import abc
from enum import Enum
import logging
from datetime import UTC, date, datetime, timedelta
from typing import Literal, cast

from homeassistant.components.recorder import get_instance
from homeassistant.components.recorder.models import (
    StatisticData,
    StatisticMeanType,
    StatisticMetaData,
)
from homeassistant.components.recorder.statistics import (
    async_add_external_statistics,
    get_last_statistics,
)
from homeassistant.const import (
    CURRENCY_EURO,
    UnitOfEnergy,
    UnitOfVolume,
)
from homeassistant.core import HomeAssistant
from homeassistant.util.unit_conversion import EnergyConverter, VolumeConverter

from .api import GreenchoiceApi
from .model import ConsumptionCost, ProfileId

DOMAIN = "greenchoice"
LOGGER = logging.getLogger(__name__)


ConsumptionType = Literal["normal"] | Literal["low"] | Literal["total"]


class ProductType(str, Enum):
    electricity = "electricity"
    gas = "gas"


class StatisticImport(abc.ABC):
    def __init__(
        self,
        unique_id: str,
        name: str,
        product_type: str,
        unit_class: str | None,
        unit: UnitOfEnergy | UnitOfVolume | Literal["€"],
    ):
        self.unique_id = unique_id
        self.name = name
        self.product_type = product_type
        self.unit_class = unit_class
        self.unit = unit

    @abc.abstractmethod
    def get_value(self, data: ConsumptionCost) -> float | None:
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
        unit_class: str | None,
        unit: UnitOfEnergy | UnitOfVolume,
        consumption_type: ConsumptionType,
    ):
        super().__init__(unique_id, name, product_type, unit_class, unit)
        self.consumption_type = consumption_type


class PowerConsumptionImport(ConsumptionImport):
    def __init__(
        self,
        unique_id: str,
        name: str,
        product_type: str,
        consumption_type: ConsumptionType,
    ):
        super().__init__(
            unique_id,
            name,
            product_type,
            EnergyConverter.UNIT_CLASS,
            UnitOfEnergy.KILO_WATT_HOUR,
            consumption_type,
        )

    def get_value(self, data: ConsumptionCost) -> float | None:
        if data.electricity is None or not data.electricity.has_consumption:
            return None
        if self.consumption_type == "low":
            return data.electricity.delivery_low_consumption
        elif self.consumption_type == "normal":
            return data.electricity.delivery_normal_consumption
        return data.electricity.total_delivery_consumption


class GasConsumptionImport(StatisticImport):
    def __init__(
        self,
        unique_id: str,
        name: str,
        product_type: ProductType,
    ):
        super().__init__(
            unique_id,
            name,
            product_type,
            VolumeConverter.UNIT_CLASS,
            UnitOfVolume.CUBIC_METERS,
        )

    def get_value(self, data: ConsumptionCost) -> float | None:
        if data.gas is None or not data.gas.has_consumption:
            return None
        return data.gas.delivery_consumption


class CostImport(StatisticImport):
    def __init__(
        self,
        unique_id: str,
        name: str,
        product_type: str,
        consumption_type: ConsumptionType,
    ):
        super().__init__(unique_id, name, product_type, None, CURRENCY_EURO)
        self.consumption_type = consumption_type

    def get_value(self, data: ConsumptionCost) -> float | None:
        if self.product_type == ProductType.electricity:
            if self.consumption_type == "low":
                return data.electricity and data.electricity.delivery_low_costs
            if self.consumption_type == "normal":
                return data.electricity and data.electricity.delivery_normal_costs
            return data.electricity and data.electricity.total_delivery_costs
        elif self.product_type == ProductType.gas:
            return data.gas and data.gas.delivery_consumption
        raise NotImplementedError()


STATS: list[StatisticImport] = [
    PowerConsumptionImport(
        "electricity_consumption_low",
        "Electricity Consumption Low",
        ProductType.electricity,
        "low",
    ),
    PowerConsumptionImport(
        "electricity_consumption_high",
        "Electricity Consumption Normal",
        ProductType.electricity,
        "normal",
    ),
    PowerConsumptionImport(
        "electricity_consumption_total",
        "Electricity Consumption Total",
        ProductType.electricity,
        "total",
    ),
    GasConsumptionImport(
        "gas_consumption_total",
        "Gas Consumption",
        ProductType.gas,
    ),
    CostImport(
        "electricity_cost_total",
        "Electricity Cost Total",
        ProductType.electricity,
        "total",
    ),
    CostImport("gas_cost_total", "Gas Cost Total", ProductType.gas, "total"),
]


class LastStat:
    def __init__(self, last_stat: datetime | None, _sum: float):
        self.last_stat = last_stat
        self.sum = _sum


class GreenchoiceImporter:
    def __init__(self, hass: HomeAssistant, api: GreenchoiceApi, profile: ProfileId):
        self._api = api
        self._hass = hass
        self._profile = profile

    def import_stat_values(
        self,
        stat: StatisticImport,
        data: list[ConsumptionCost],
        last_stat: LastStat,
    ):
        metadata = StatisticMetaData(
            mean_type=StatisticMeanType.NONE,
            has_sum=True,
            name=f"Greenchoice {stat.name}",
            source=DOMAIN,
            statistic_id=stat.statistic_id,
            unit_class=stat.unit_class,
            unit_of_measurement=stat.unit,
        )
        statistics: list[StatisticData] = []

        sum = last_stat.sum
        for current_data in data:
            if (
                last_stat.last_stat is not None
                and current_data.consumed_on <= last_stat.last_stat
            ):
                continue
            value = stat.get_value(current_data)
            if value:
                sum += value
                statistics.append(
                    StatisticData(start=current_data.consumed_on, state=value, sum=sum)
                )

        if any(statistics):
            LOGGER.debug("Adding %d statistics for %s", len(statistics), stat.name)
            async_add_external_statistics(self._hass, metadata, statistics)
        else:
            LOGGER.debug("No new statistics for %s", stat.name)

    async def get_last_stats(self):
        statistics: dict[StatisticImport, LastStat] = {}
        oldest_stat: datetime | None = None
        for stat in STATS:
            last_stats = (
                await get_instance(self._hass).async_add_executor_job(
                    get_last_statistics,
                    self._hass,
                    1,
                    stat.statistic_id,
                    True,
                    {"sum"},
                )
            ).get(stat.statistic_id, [])
            last_stat = last_stats[0] if last_stats else None

            if not last_stat or "start" not in last_stat or "sum" not in last_stat:
                last_stats_time = None
                _sum = 0.0
            else:
                last_stats_time = datetime.fromtimestamp(last_stat["start"], UTC)
                _sum = cast(float, last_stat["sum"])
                if oldest_stat is None or last_stats_time < oldest_stat:
                    oldest_stat = last_stats_time
            statistics[stat] = LastStat(last_stats_time, _sum)
        LOGGER.debug("Oldest statistic is: %s", oldest_stat)

        return statistics, oldest_stat

    async def import_data(self):
        last_stats, first_stat = await self.get_last_stats()

        today = date.today()
        max_days = 21  # start with last 3 weeks
        if first_stat is not None:
            days_since = (today - first_stat.date()).days
            max_days = min(max_days, days_since)
        days = [today - timedelta(days=n) for n in range(max_days, 0, -1)]

        LOGGER.debug("Importing data for days: %s", days)

        all_consumption: list[ConsumptionCost] = []
        for day in days:
            consumption = await self._api.get_hourly_readings(self._profile, day)
            if consumption.has_consumption:
                for entry in consumption.consumption_costs:
                    if entry.has_consumption:
                        all_consumption.append(entry)

        for stat in STATS:
            self.import_stat_values(
                stat,
                all_consumption,
                last_stats[stat],
            )

    async def clear_data(self):
        ids = [stat.statistic_id for stat in STATS]
        get_instance(self._hass).async_clear_statistics(list(ids))
