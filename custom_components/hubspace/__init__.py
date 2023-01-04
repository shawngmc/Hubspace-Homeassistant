"""Hubspace Service Integration"""
from __future__ import annotations

import logging

from .hubspace import HubSpace
import voluptuous as vol

# Import the device class from the component that you want to support
from .fan import HubspaceFan
from .light import HubspaceLight, HubspaceLock, HubspaceOutlet, HubspaceTransformer
from homeassistant.helpers import config_validation as cv, entity_platform, service
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from datetime import timedelta

# Import exceptions from the requests module
import requests.exceptions

SCAN_INTERVAL = timedelta(seconds=60)
BASE_INTERVAL = timedelta(seconds=60)

_LOGGER = logging.getLogger(__name__)

CONF_FRIENDLYNAMES: Final = "friendlynames"
CONF_ROOMNAMES: Final = "roomnames"
CONF_DEBUG: Final = "debug"

DOMAIN = "hubspace"


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


def _add_entity(entities, hs, model, deviceClass, friendlyName, debug):

        if model == 'HPKA315CWB' or model == 'HPPA52CWBA023':
            _LOGGER.debug("Creating Outlets" )
            entities.append(HubspaceOutlet(hs, friendlyName,"1",debug))
            entities.append(HubspaceOutlet(hs, friendlyName,"2",debug))
        elif model == 'LTS-4G-W':
            _LOGGER.debug("Creating Outlets" )
            entities.append(HubspaceOutlet(hs, friendlyName,"1",debug))
            entities.append(HubspaceOutlet(hs, friendlyName,"2",debug))
            entities.append(HubspaceOutlet(hs, friendlyName,"3",debug))
            entities.append(HubspaceOutlet(hs, friendlyName,"4",debug))
        elif model == 'HB-200-1215WIFIB':
            _LOGGER.debug("Creating Transformers" )
            entities.append(HubspaceTransformer(hs, friendlyName,"1",debug))
            entities.append(HubspaceTransformer(hs, friendlyName,"2",debug))
            entities.append(HubspaceTransformer(hs, friendlyName,"3",debug))
        elif model == '52133, 37833':
            _LOGGER.debug("Creating Fan" )
            entities.append(HubspaceFan(hs, friendlyName,debug))
            _LOGGER.debug("Creating Light" )
            entities.append(HubspaceLight(hs, friendlyName,debug))
        elif model == '76278, 37278':
            _LOGGER.debug("Creating Fan" )
            entities.append(HubspaceFan(hs, friendlyName,debug))
            _LOGGER.debug("Creating Light" )
            entities.append(HubspaceLight(hs, friendlyName,debug))
        elif deviceClass == 'door-lock' and model == 'TBD':
            _LOGGER.debug("Creating Lock" )
            entities.append(HubspaceLock(hs, friendlyName,debug))
        else:
            _LOGGER.debug("creating lights" )
            entities.append(HubspaceLight(hs, friendlyName,debug))

        return entities



def setup(
    hass: HomeAssistant,
    config: ConfigType,
) -> None:
    """Set up the Hubspace component."""
    
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
            
            if deviceClass == 'light' or deviceClass == 'switch':
                entities.append(HubspaceLight(hs, friendlyName, debug, childId, model, deviceId, deviceClass, functions))
            elif deviceClass == 'power-outlet':
                for function in functions:
                    if function.get('functionClass') == 'toggle':
                        try:
                            _LOGGER.debug(f"Found toggle with id {function.get('id')} and instance {function.get('functionInstance')}")
                            outletIndex = function.get('functionInstance').split('-')[1]
                            entities.append(HubspaceOutlet(hs, friendlyName, outletIndex, debug, childId, model, deviceId, deviceClass))
                        except IndexError:
                            _LOGGER.debug('Error extracting outlet index')
            elif deviceClass == 'landscape-transformer':
                for function in functions:
                    if function.get('functionClass') == 'toggle':
                        try:
                            _LOGGER.debug(f"Found toggle with id {function.get('id')} and instance {function.get('functionInstance')}")
                            outletIndex = function.get('functionInstance').split('-')[1]
                            entities.append(HubspaceTransformer(hs, friendlyName, outletIndex, debug, childId, model, deviceId, deviceClass))
                        except IndexError:
                            _LOGGER.debug('Error extracting outlet index')
    
    if not entities:
        return
    
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
