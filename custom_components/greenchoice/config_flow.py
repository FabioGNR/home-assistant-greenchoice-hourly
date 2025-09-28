"""Config flow for Elvia integration."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from .error import GreenchoiceError

from .api import GreenchoiceApi
import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_USERNAME, CONF_PASSWORD

from .const import DOMAIN, LOGGER


class GreenchoiceConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Greenchoice."""

    def __init__(self) -> None:
        """Initialize."""
        self._username: str | None = None
        self._metering_point_ids: list[str] | None = None

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
                    await client.get_hourly_readings(date.today() - timedelta(days=4))
            except GreenchoiceError as exception:
                LOGGER.error("Authentication error %s", exception)
                errors["base"] = "invalid_auth"
            except Exception as exception:
                LOGGER.error("Unknown error %s", exception)
                errors["base"] = "unknown"
            else:
                return await self._create_config_entry(
                    username=self._username, password=self._password
                )

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

    async def _create_config_entry(
        self,
        username: str,
        password: str,
    ) -> ConfigFlowResult:
        """Store username and password."""
        return self.async_create_entry(
            title="Greenchoice",
            data={
                CONF_USERNAME: username,
                CONF_PASSWORD: password,
            },
        )
