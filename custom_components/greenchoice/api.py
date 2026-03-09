from dataclasses import dataclass
from datetime import date, timedelta
from types import TracebackType

import aiohttp
from pydantic import ValidationError

from .const import BASE_URL
from .error import GreenchoiceError
from .auth import setup_auth
from .model import Consumption, Profile


@dataclass
class ProfileId:
    customer_number: int
    agreement_id: int

    @staticmethod
    def from_profile(profile: Profile):
        return ProfileId(
            customer_number=profile.customer_number, agreement_id=profile.agreement_id
        )


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
        if self._session is None:
            raise RuntimeError("API must be used from `with` statement")
        await setup_auth(self._session, self._username, self._password)

    async def get_profiles(self) -> list[Profile]:
        if self._session is None:
            raise RuntimeError("API must be used from `with` statement")
        try:
            profile_response = await self._session.get(f"{BASE_URL}/api/v2/profiles")
            profile_response.raise_for_status()
            profiles_body = await profile_response.json()
            return [Profile.model_validate(p) for p in profiles_body]
        except aiohttp.ClientError as ex:
            raise GreenchoiceError from ex
        except ValidationError as ex:
            raise GreenchoiceError from ex

    async def get_hourly_readings(self, profile: ProfileId, day: date) -> Consumption:
        if self._session is None:
            raise RuntimeError("API must be used from `with` statement")
        try:
            start = day
            end = day + timedelta(days=1)
            consumption_response = await self._session.get(
                f"{BASE_URL}/api/v2/customers/{profile.customer_number}/agreements/{profile.agreement_id}/consumptions",
                params={"interval": "hour", "start": str(start), "end": str(end)},
            )

            consumption_response.raise_for_status()

            consumption_body = await consumption_response.text()
            return Consumption.model_validate_json(consumption_body)
        except aiohttp.ClientError as ex:
            raise GreenchoiceError from ex
        except ValidationError as ex:
            raise GreenchoiceError from ex
