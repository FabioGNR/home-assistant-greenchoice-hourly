from datetime import datetime
from typing import Annotated
from zoneinfo import ZoneInfo

from pydantic import AfterValidator, BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

# Greenchoice datetimes have no timezone, so we assume the times are in timezone of the Netherlands
AwareDateTime = Annotated[
    datetime, AfterValidator(lambda dt: dt.replace(tzinfo=ZoneInfo("Europe/Amsterdam")))
]


class CamelCaseModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel)


class Profile(CamelCaseModel):
    customer_number: int
    agreement_id: int
    street: str
    house_number: int
    energy_supply_status: str


class ElectricityConsumptionData(CamelCaseModel):
    delivery_low_consumption: float | None
    delivery_low_costs: float | None
    delivery_normal_consumption: float | None
    delivery_normal_costs: float | None
    fixed_delivery_costs: float | None
    grid_operator_costs: float | None
    total_fixed_costs: float | None
    total_delivery_costs: float | None
    total_delivery_consumption: float | None
    has_consumption: bool


class GasConsumptionData(CamelCaseModel):
    delivery_consumption: float | None
    delivery_costs: float | None
    fixed_delivery_costs: float | None
    grid_operator_costs: float | None
    has_consumption: bool


class ConsumptionCost(CamelCaseModel):
    consumed_on: AwareDateTime
    electricity: ElectricityConsumptionData | None
    gas: GasConsumptionData | None
    has_consumption: bool


class Consumption(CamelCaseModel):
    interval: str
    start: AwareDateTime
    end: AwareDateTime
    consumption_costs: list[ConsumptionCost]
    has_consumption: bool
