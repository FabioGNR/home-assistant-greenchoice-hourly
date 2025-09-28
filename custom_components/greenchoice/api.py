from datetime import date, timedelta
from types import TracebackType

import aiohttp
from pydantic import ValidationError

from .const import BASE_URL
from .error import GreenchoiceError
from .auth import setup_auth
from .model import Consumption


class GreenchoiceApi:
    def __init__(self, username: str, password: str) -> None:
        self._username = username
        self._password = password
        self._session: aiohttp.ClientSession | None = None

    async def __aenter__(self):
        self._session = aiohttp.ClientSession()
        await self._session.__aenter__()

    async def __aexit__(
        self,
        exc_t: type[BaseException] | None,
        exc_v: BaseException | None,
        exc_tb: TracebackType | None,
    ):
        assert self._session is not None
        await self._session.__aexit__(exc_t, exc_v, exc_tb)
        self._session = None

    async def login(self):
        await setup_auth(self._session, self._username, self._password)

    async def get_hourly_readings(self, day: date) -> Consumption:
        try:
            start = day
            end = day + timedelta(days=1)
            consumption_response = await self._session.get(
                f"{BASE_URL}/api/consumption",
                params={"interval": "hour", "start": str(start), "end": str(end)},
            )

            consumption_response.raise_for_status()

            consumption_body = await consumption_response.text()
            return Consumption.model_validate_json(consumption_body)
        except aiohttp.ClientError as ex:
            raise GreenchoiceError from ex
        except ValidationError as ex:
            raise GreenchoiceError from ex
