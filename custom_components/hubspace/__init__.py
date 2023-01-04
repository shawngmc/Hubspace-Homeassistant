"""Hubspace Service Integration"""
from __future__ import annotations

import logging

from .const import DOMAIN
import voluptuous as vol

# Import the device class from the component that you want to support
from homeassistant.helpers import config_validation as cv
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType
from datetime import timedelta

# Import exceptions from the requests module
import requests.exceptions

SCAN_INTERVAL = timedelta(seconds=60)
BASE_INTERVAL = timedelta(seconds=60)

_LOGGER = logging.getLogger(__name__)

CONF_FRIENDLYNAMES: Final = "friendlynames"
CONF_ROOMNAMES: Final = "roomnames"
CONF_DEBUG: Final = "debug"

# Validation of the user's configuration
HUBSPACE_SCHEMA = vol.All(
    vol.Schema(
        {
            vol.Required(CONF_USERNAME): cv.string,
            vol.Required(CONF_PASSWORD): cv.string,
            vol.Required(CONF_DEBUG, default=False): cv.boolean,
            vol.Required(CONF_FRIENDLYNAMES, default=[]): vol.All(cv.ensure_list, [cv.string]),
            vol.Required(CONF_ROOMNAMES, default=[]): vol.All(cv.ensure_list, [cv.string]),
        },
        extra=vol.PREVENT_EXTRA,
    )
)

CONFIG_SCHEMA = vol.Schema(
    {vol.Optional(DOMAIN): HUBSPACE_SCHEMA}, extra=vol.ALLOW_EXTRA
)

def setup(
    hass: HomeAssistant,
    yaml_config: ConfigType,
) -> None:
    """Set up the Hubspace component."""
    if DOMAIN not in yaml_config:
        return False

    hass.data[DOMAIN] = yaml_config[DOMAIN]

    return True
        