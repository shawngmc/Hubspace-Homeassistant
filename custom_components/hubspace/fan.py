"""Platform for fan integration."""
from __future__ import annotations
import re
from enum import Enum

import logging

from .hubspace import HubSpace
import voluptuous as vol

# Import the device class from the component that you want to support
from homeassistant.helpers import config_validation as cv, entity_platform, service
from homeassistant.components.fan import (PLATFORM_SCHEMA, FanEntity, FanEntityFeature)
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from datetime import timedelta

# Import exceptions from the requests module
import requests.exceptions

class FanSpeed(Enum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    MAX = 4
    def getPercentage(self):
        return self.value * 25
    def toHubspaceSpeedString(self):
        return f"fan-speed-{self.getPercentage().zfill(3)}"
    def fromHubspaceSpeedString(speedstring):
        percentage_digits = re.search("(\d{3})$", speedstring).group(0)
        percentage = int(percentage_digits)
        val = percentage / 25
        return FanSpeed(val)
        

SCAN_INTERVAL = timedelta(seconds=60)
BASE_INTERVAL = timedelta(seconds=60)

_LOGGER = logging.getLogger(__name__)

class HubspaceFan(FanEntity):
    """Representation of an Awesome Fan."""
    
    def __init__(self, hs, friendlyname, debug, childId = None, model = None, deviceId = None, deviceClass = None) -> None:
        """Initialize an AwesomeFan."""
        
        _LOGGER.debug("Fan Name: " )
        _LOGGER.debug(friendlyname)
        _LOGGER.debug(f"Friendly Name: {friendlyname}")
        _LOGGER.debug(f" Child ID: {childId}")
        _LOGGER.debug(f" Model: {model}")
        _LOGGER.debug(f" Device ID: {deviceId}")
        _LOGGER.debug(f" Device Class: {deviceClass}")
        self._name = friendlyname

        if None in (childId, model, deviceId, deviceClass):
            self._name = friendlyname + "_fan" 
        
        _LOGGER.debug(f" Entity Name: {self._name}")

        self._attr_supported_features = FanEntityFeature.PRESET_MODE
        self._debug = debug
        self._state = 'off'
        self._childId = childId
        self._model = model
        self._attr_preset_modes = list(FanSpeed.__members__)
        self._attr_speed_count = len(self._attr_preset_modes)
        self._hs = hs
        self._deviceId = deviceId
        self._debugInfo = None
        
        if None in (childId, model, deviceId, deviceClass):
            [self._childId, self._model, self._deviceId, deviceClass] = self._hs.getChildId(friendlyname)
        self.update()
    
    @property
    def name(self) -> str:
        """Return the display name of this fan."""
        return self._name
    
    @property
    def unique_id(self) -> str:
        """Return the display name of this fan."""
        return self._childId

    @property
    def is_on(self) -> bool | None:
        """Return true if fan is on."""
        return self._state == 'on'

    def turn_on(self, **kwargs: Any) -> None:
        self._hs.setStateInstance(self._childId,'power','fan-power','on')
        self.update()

#     @property
#     def extra_state_attributes(self):
#         """Return the state attributes."""
#         attr = {}
#         attr["model"]= self._model
#         if self._name.endswith("_fan"):
#             attr["deviceId"] = self._deviceId + "_fan"
#         else:
#             attr["deviceId"] = self._deviceId
#         attr["devbranch"] = False
        
#         attr["debugInfo"] = self._debugInfo
        
#         return attr

    def set_preset_mode(self, preset_mode: str) -> None:
        """Set the preset mode of the fan."""
        preset_enum = FanSpeed[preset_mode]
        self._hs.setStateInstance(self._childId,'fan-speed','fan-speed',preset_enum.toHubspaceSpeedString())
        self.update()

        
    def turn_off(self, **kwargs: Any) -> None:
        """Instruct the fan to turn off."""
        self._hs.setStateInstance(self._childId,'power','fan-power','off')
        self.update()
        
    @property
    def should_poll(self):
        """Turn on polling """
        return True
        
    def update(self) -> None:
        """Fetch new state data for this fan.

        This is the only method that should fetch new data for Home Assistant.
        """
        self._state = self._hs.getStateInstance(self._childId,'power','fan-power')
        fanspeed = self._hs.getStateInstance(self._childId,'fan-speed','fan-speed')
        _LOGGER.debug(f" Speed: {fanspeed}")
        self._attr_preset_mode = FanSpeed.fromHubspaceSpeedString(fanspeed).name
        
        _LOGGER.debug(f"UPDATE: {self._name}")
        _LOGGER.debug(f" State: {self._state}")
        _LOGGER.debug(f" Speed: {self._attr_preset_mode}")
        if self._debug:
            self._debugInfo = self._hs.getDebugInfo(self._childId)
