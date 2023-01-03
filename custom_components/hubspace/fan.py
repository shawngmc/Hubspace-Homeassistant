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

CONF_FRIENDLYNAMES: Final = "friendlynames"
CONF_ROOMNAMES: Final = "roomnames"
CONF_DEBUG: Final = "debug"

# Validation of the user's configuration
PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_USERNAME): cv.string,
    vol.Required(CONF_PASSWORD): cv.string,
    vol.Required(CONF_DEBUG, default=False): cv.boolean,
    vol.Required(CONF_FRIENDLYNAMES, default=[]): vol.All(cv.ensure_list, [cv.string]),
    vol.Required(CONF_ROOMNAMES, default=[]): vol.All(cv.ensure_list, [cv.string]),
})

def _add_entity(entities, hs, model, deviceClass, friendlyName, debug):
        if model == '52133, 37833':
            _LOGGER.debug("Creating Fan" )
            entities.append(HubspaceFan(hs, friendlyName,debug))
        elif model == '76278, 37278':
            _LOGGER.debug("Creating Fan" )
            entities.append(HubspaceFan(hs, friendlyName,debug))
        else:
            _LOGGER.debug("skipping non-fan entities")
        return entities

def setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None
) -> None:
    """Set up the Awesome Fan platform."""
    
    # Assign configuration variables.
    # The configuration check takes care they are present.
        
    username = config[CONF_USERNAME]
    password = config.get(CONF_PASSWORD)
    debug = config.get(CONF_DEBUG)
    try:
        hs = HubSpace(username,password)
    except requests.exceptions.ReadTimeout as ex:
        raise PlatformNotReady(f"Connection error while connecting to hubspace: {ex}") from ex
    
    entities = []
    for friendlyName in config.get(CONF_FRIENDLYNAMES):

        _LOGGER.debug("friendlyName " + friendlyName )
        [childId, model, deviceId, deviceClass] = hs.getChildId(friendlyName)

        _LOGGER.debug("Switch on Model " + model )
        _LOGGER.debug("childId: " + childId )
        _LOGGER.debug("deviceId: " + deviceId )
        _LOGGER.debug("deviceClass: " + deviceClass )
        
        entities = _add_entity(entities, hs, model, deviceClass, friendlyName, debug)

    for roomName in config.get(CONF_ROOMNAMES):

        _LOGGER.debug("roomName " + roomName )
        children = hs.getChildrenFromRoom(roomName)

        for childId in children:

            _LOGGER.debug("childId " + childId )
            [childId, model, deviceId, deviceClass, friendlyName] = hs.getChildInfoById(childId)

            _LOGGER.debug("Switch on Model " + model )
            _LOGGER.debug("deviceId: " + deviceId )
            _LOGGER.debug("deviceClass: " + deviceClass )
            _LOGGER.debug("friendlyName: " + friendlyName )

            entities = _add_entity(entities, hs, model, deviceClass, friendlyName, debug)
    
    if config.get(CONF_FRIENDLYNAMES) == [] and config.get(CONF_ROOMNAMES) == []:
        _LOGGER.debug('Attempting automatic discovery')
        for [childId, model, deviceId, deviceClass, friendlyName, functions] in hs.discoverDeviceIds():
            _LOGGER.debug("childId " + childId )
            _LOGGER.debug("Switch on Model " + model )
            _LOGGER.debug("deviceId: " + deviceId )
            _LOGGER.debug("deviceClass: " + deviceClass )
            _LOGGER.debug("friendlyName: " + friendlyName )
            _LOGGER.debug("functions: " + str(functions))
            
            if deviceClass == 'fan':
                entities.append(HubspaceFan(hs, friendlyName, debug, childId, model, deviceId, deviceClass))
    
    if not entities:
        return
    add_entities(entities)
    
    
    def my_service(call: ServiceCall) -> None:
        """My first service."""
        _LOGGER.info("Received data" +  str(call.data))
        
        entity_ids = call.data['entity_id']       
        functionClass = call.data['functionClass']
        value = call.data['value']
        
        if 'functionInstance' in call.data:
            functionInstance = call.data['functionInstance']
        else:
            functionInstance = None
        
        for entity_id in entity_ids:
            _LOGGER.info("entity_id: " + str(entity_id))
            for i in entities:
                if i.entity_id == entity_id:
                    _LOGGER.info("Found Entity")
                    i.send_command(functionClass,value,functionInstance)
            

    # Register our service with Home Assistant.
    hass.services.register("hubspace", 'send_command', my_service)
    
        
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

        self._supported_features = FanEntityFeature.PRESET_MODE
        self._debug = debug
        self._state = 'off'
        self._childId = childId
        self._model = model
        self._preset_modes = list(FanSpeed.__members__)
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
        self._preset_mode = FanSpeed.fromHubspaceSpeedString(fanspeed).name
        
        _LOGGER.debug(f"UPDATE: {self._name}")
        _LOGGER.debug(f" State: {self._state}")
        _LOGGER.debug(f" Speed: {self._preset_mode}")
        if self._debug:
            self._debugInfo = self._hs.getDebugInfo(self._childId)
