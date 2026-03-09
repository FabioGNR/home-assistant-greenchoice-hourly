from datetime import datetime

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


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
    consumed_on: datetime
    electricity: ElectricityConsumptionData | None
    gas: GasConsumptionData | None
    has_consumption: bool


class Consumption(CamelCaseModel):
    interval: str
    start: datetime
    end: datetime
    consumption_costs: list[ConsumptionCost]
    has_consumption: bool
