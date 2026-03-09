"""Config flow for Greenchoice integration."""

from __future__ import annotations

from typing import Any

from .error import GreenchoiceError

from .const import CONF_CUSTOMER_NUMBER, CONF_AGREEMENT_ID
from .api import GreenchoiceApi
from .model import Profile
import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_USERNAME, CONF_PASSWORD
from homeassistant.helpers.selector import selector

from .const import DOMAIN, LOGGER


class GreenchoiceConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Greenchoice."""

    def __init__(self) -> None:
        """Initialize."""
        self._username: str | None = None
        self._profiles: list[Profile] | None = None

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            self._username = user_input[CONF_USERNAME]
            self._password = user_input[CONF_PASSWORD]
            assert self._username is not None
            assert self._password is not None

            client = GreenchoiceApi(self._username, self._password)
            try:
                async with client:
                    await client.login()
                    self._profiles = await client.get_profiles()
            except GreenchoiceError as exception:
                LOGGER.error("Authentication error %s", exception)
                errors["base"] = "invalid_auth"
            except Exception as exception:
                LOGGER.error("Unknown error %s", exception)
                errors["base"] = "unknown"
            else:
                return await self.async_step_profile(user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_USERNAME): str,
                    vol.Required(CONF_PASSWORD): str,
                }
            ),
            errors=errors,
        )

    async def async_step_profile(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}

        if user_input is not None and self._profiles:
            profile = user_input.get("profile", None)
            if profile:
                customer_number = next(
                    (p for p in self._profiles if p.agreement_id == profile),
                ).customer_number
                return await self._create_config_entry(
                    username=self._username,
                    password=self._password,
                    customer_number=customer_number,
                    agreement_id=profile,
                )
        if self._profiles is None:
            return self.async_abort(reason="No profiles available")
        eligible_profiles = [
            p for p in self._profiles if p.energy_supply_status == "Active"
        ]
        if len(eligible_profiles) == 1:
            return await self.async_step_profile(
                {**(user_input or {}), "profile": eligible_profiles[0].agreement_id}
            )

        return self.async_show_form(
            step_id="profile",
            data_schema=vol.Schema(
                {
                    vol.Required("profile"): selector(
                        {
                            "select": {
                                "options": [
                                    {
                                        "label": f"{p.street} {p.house_number}",
                                        "value": p.agreement_id,
                                    }
                                    for p in eligible_profiles
                                ]
                            }
                        }
                    ),
                }
            ),
            errors=errors,
        )

    async def _create_config_entry(
        self,
        username: str,
        password: str,
        customer_number: int,
        agreement_id: int,
    ) -> ConfigFlowResult:
        """Store username and password."""
        return self.async_create_entry(
            title="Greenchoice",
            data={
                CONF_USERNAME: username,
                CONF_PASSWORD: password,
                CONF_CUSTOMER_NUMBER: customer_number,
                CONF_AGREEMENT_ID: agreement_id,
            },
        )
