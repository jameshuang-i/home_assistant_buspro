"""
Support for Buspro devices.

For more details about this component, please refer to the documentation at
https://home-assistant.io/...
"""

import logging
import typing

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.const import (CONF_HOST, CONF_PORT, CONF_NAME,)
from homeassistant.const import (EVENT_HOMEASSISTANT_STOP,)
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

from .pybuspro.buspro import Buspro
from .pybuspro.devices.scene import Scene
from .pybuspro.devices.generic import Generic
from .pybuspro.devices.universal_switch import UniversalSwitch

_LOGGER = logging.getLogger(__name__)

DOMAIN = "buspro"
DATA_BUSPRO = "buspro"

DEFAULT_CONF_NAME = ""

SERVICE_BUSPRO_SEND_MESSAGE = "send_message"
SERVICE_BUSPRO_ACTIVATE_SCENE = "activate_scene"
SERVICE_BUSPRO_UNIVERSAL_SWITCH = "set_universal_switch"

SERVICE_BUSPRO_ATTR_OPERATE_CODE = "operate_code"
SERVICE_BUSPRO_ATTR_ADDRESS = "address"
SERVICE_BUSPRO_ATTR_PAYLOAD = "payload"
SERVICE_BUSPRO_ATTR_SCENE_ADDRESS = "scene_address"
SERVICE_BUSPRO_ATTR_SWITCH_NUMBER = "switch_number"
SERVICE_BUSPRO_ATTR_STATUS = "status"

"""{ "address": [1,74], "scene_address": [3,5] }"""
SERVICE_BUSPRO_ACTIVATE_SCENE_SCHEMA = vol.Schema({
    vol.Required(SERVICE_BUSPRO_ATTR_ADDRESS): vol.Any([cv.positive_int]),
    vol.Required(SERVICE_BUSPRO_ATTR_SCENE_ADDRESS): vol.Any([cv.positive_int]),
})

"""{ "address": [1,74], "operate_code": [4,12], "payload": [1,75,0,3] }"""
SERVICE_BUSPRO_SEND_MESSAGE_SCHEMA = vol.Schema({
    vol.Required(SERVICE_BUSPRO_ATTR_ADDRESS): vol.Any([cv.positive_int]),
    vol.Required(SERVICE_BUSPRO_ATTR_OPERATE_CODE): vol.Any([cv.positive_int]),
    vol.Required(SERVICE_BUSPRO_ATTR_PAYLOAD): vol.Any([cv.positive_int]),
})

"""{ "address": [1,100], "switch_number": 100, "status": 1 }"""
SERVICE_BUSPRO_UNIVERSAL_SWITCH_SCHEMA = vol.Schema({
    vol.Required(SERVICE_BUSPRO_ATTR_ADDRESS): vol.Any([cv.positive_int]),
    vol.Required(SERVICE_BUSPRO_ATTR_SWITCH_NUMBER): vol.Any(cv.positive_int),
    vol.Required(SERVICE_BUSPRO_ATTR_STATUS): vol.Any(cv.positive_int),
})

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        vol.Required(CONF_HOST): cv.string,
        vol.Required(CONF_PORT): cv.port,
        vol.Optional(CONF_NAME, default=DEFAULT_CONF_NAME): cv.string
    })
}, extra=vol.ALLOW_EXTRA)

async def async_setup(hass: HomeAssistant, config: dict):
    """Setup the Buspro component. """
    if DOMAIN not in config:
        return True
    _LOGGER.debug(f"Trying to setup buspro with config {config[DOMAIN]} ...")
    return await _init_buspro(hass, config[DOMAIN])

async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Setup the Buspro component. """
    _LOGGER.debug(f"Trying to setup entry for buspro with config {config_entry.data} ...")
    return await _init_buspro(hass, config_entry.data)

async def _init_buspro(hass:HomeAssistant, config: dict) -> bool:
    buspro_module = BusproModule(hass, config[CONF_HOST], config[CONF_PORT])
    hass.data[DATA_BUSPRO] = buspro_module
    _LOGGER.info("Inited the buspro module and try to start service ...")
    await buspro_module.start()
    _LOGGER.info("Try to register ha services ...")
    buspro_module.register_services()
    return True


class BusproModule:
    """Representation of Buspro Object."""

    def __init__(self, hass:HomeAssistant, host:str, port:int):
        """Initialize of Buspro module."""
        self.hass:HomeAssistant = hass
        self.gateway_address:typing.Tuple[str,int] = (host, port)
        self.local_address:typing.Tuple[str,int] = ('', port)

        self.connected:bool = False
        # Initialize of Buspro object.
        self.hdl:Buspro = Buspro(self.gateway_address, self.local_address, self.hass.loop)     

    async def start(self):
        """Start Buspro object. Connect to tunneling device."""
        await self.hdl.start(state_updater=False)
        self.hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, self.stop)
        self.connected = True

    async def stop(self, event):
        """Stop Buspro object. Disconnect from tunneling device."""
        await self.hdl.stop()
        self.connected = False

    async def service_activate_scene(self, call):
        _LOGGER.debug(f"Activate scene service called with data {call.data}")
        attr_address = call.data.get(SERVICE_BUSPRO_ATTR_ADDRESS)
        attr_scene_address = call.data.get(SERVICE_BUSPRO_ATTR_SCENE_ADDRESS)
        scene = Scene(self.hdl, attr_address, attr_scene_address)
        await scene.run()

    async def service_send_message(self, call):
        _LOGGER.debug(f"Send message service called with data {call.data}")
        attr_address = call.data.get(SERVICE_BUSPRO_ATTR_ADDRESS)
        attr_payload = call.data.get(SERVICE_BUSPRO_ATTR_PAYLOAD)
        attr_operate_code = call.data.get(SERVICE_BUSPRO_ATTR_OPERATE_CODE)
        generic = Generic(self.hdl, attr_address, attr_payload, attr_operate_code)
        await generic.run()

    async def service_set_universal_switch(self, call):
        _LOGGER.debug(f"Universal switch service called with data {call.data}")
        attr_address = call.data.get(SERVICE_BUSPRO_ATTR_ADDRESS)
        attr_switch_number = call.data.get(SERVICE_BUSPRO_ATTR_SWITCH_NUMBER)
        universal_switch = UniversalSwitch(self.hdl, attr_address, attr_switch_number)

        status = call.data.get(SERVICE_BUSPRO_ATTR_STATUS)
        if status == 1:
            await universal_switch.set_on()
        else:
            await universal_switch.set_off()

    def register_services(self):
        """ activate_scene """
        self.hass.services.async_register(
            DOMAIN, SERVICE_BUSPRO_ACTIVATE_SCENE,
            self.service_activate_scene,
            schema=SERVICE_BUSPRO_ACTIVATE_SCENE_SCHEMA)

        """ send_message """
        self.hass.services.async_register(
            DOMAIN, SERVICE_BUSPRO_SEND_MESSAGE,
            self.service_send_message,
            schema=SERVICE_BUSPRO_SEND_MESSAGE_SCHEMA)

        """ universal_switch """
        self.hass.services.async_register(
            DOMAIN, SERVICE_BUSPRO_UNIVERSAL_SWITCH,
            self.service_set_universal_switch,
            schema=SERVICE_BUSPRO_UNIVERSAL_SWITCH_SCHEMA)
