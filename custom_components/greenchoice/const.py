"""Constants for the Greenchoice integration."""

from logging import getLogger
from typing import Final

DOMAIN = "greenchoice"
LOGGER = getLogger(__package__)
SSO_URL = "https://sso.greenchoice.nl"
BASE_URL = "https://mijn.greenchoice.nl"
CONF_CUSTOMER_NUMBER: Final = "customer_number"
CONF_AGREEMENT_ID: Final = "agreement_id"
