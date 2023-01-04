
import asyncio
import logging

import voluptuous as vol

from aiohttp.client_exceptions import ClientConnectionError

from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError

from .const import DOMAIN
from .hubspace import HubSpace

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
    }
)

async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> None:
    """Validate the user input allows us to connect.
    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """
    try:
        hs = HubSpace(data[CONF_USERNAME], data[CONF_PASSWORD])
    except ex:
        raise ex


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Example config flow."""\

    VERSION = 1
    entry: config_entries.ConfigEntry | None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        if user_input is None:
            return self.async_show_form(
                step_id="user", data_schema=STEP_USER_DATA_SCHEMA
            )

        errors = {}

        try:
            await validate_input(self.hass, user_input)
        except:
            errors["base"] = "cannot_connect"

        else:
            await self.async_set_unique_id(
                user_input["username"].lower(), raise_on_progress=False
            )
            self._abort_if_unique_id_configured()
            return self.async_create_entry(title="Hubspace", data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )