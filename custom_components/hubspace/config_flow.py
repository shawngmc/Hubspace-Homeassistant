from homeassistant import config_entries
from .const import DOMAIN
import voluptuous as vol


class ExampleConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Example config flow."""