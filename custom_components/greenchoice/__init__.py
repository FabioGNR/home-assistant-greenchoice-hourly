"""The Greenchoice integration."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import async_track_time_interval

from .api import GreenchoiceApi
from .const import CONF_AGREEMENT_ID, CONF_CUSTOMER_NUMBER, LOGGER
from .importer import GreenchoiceImporter
from .model import ProfileId

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Greenchoice from a config entry."""

    api = GreenchoiceApi(entry.data[CONF_USERNAME], entry.data[CONF_PASSWORD])
    profile = ProfileId(
        customer_number=entry.data[CONF_CUSTOMER_NUMBER],
        agreement_id=entry.data[CONF_AGREEMENT_ID],
    )
    importer = GreenchoiceImporter(hass=hass, api=api, profile=profile)

    async def _import_values(_: datetime | None = None) -> None:
        """Import values."""
        try:
            LOGGER.debug("Starting scheduled import of statistics...")
            async with api:
                await api.login()
                await importer.import_data()
        except Exception as exception:
            LOGGER.exception("Unknown error %s", exception)

    try:
        async with api:
            await api.login()
            await importer.import_data()
    except Exception as exception:
        LOGGER.exception("Unknown error %s", exception)
        return False

    cancel_scheduled_import = async_track_time_interval(
        hass,
        _import_values,
        timedelta(hours=12),
        cancel_on_shutdown=True,
    )

    entry.async_on_unload(cancel_scheduled_import)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    return True
