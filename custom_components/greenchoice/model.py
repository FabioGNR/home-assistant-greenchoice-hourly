from datetime import datetime, date

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class CamelCaseModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel)


class ConsumptionData(CamelCaseModel):
    consumption_high: float
    consumption_low: float
    consumption_total: float
    costs_total_consumption: float
    costs_consumption_high: float
    costs_consumption_low: float
    costs_fixed: float
    costs_total: float


class ProductConsumption(CamelCaseModel):
    product_type: str
    unit_type: str
    values: dict[datetime, ConsumptionData]


class Consumption(CamelCaseModel):
    class Request(BaseModel):
        request_url: str = (
            """/api/consumption?interval={interval}&start={start}&end={end}"""
        )

        interval: str
        start: date
        end: date

        def build_url(self) -> str:
            return self.request_url.format(
                interval=self.interval,
                start=self.start,
                end=self.end,
            )

    interval: str
    start: datetime
    end: datetime
    entries: list[ProductConsumption]
