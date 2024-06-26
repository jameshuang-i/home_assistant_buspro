"""
This component provides switch support for Buspro.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/...
"""

import logging

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.components.switch import SwitchEntity, PLATFORM_SCHEMA
from homeassistant.const import (CONF_NAME, CONF_DEVICES)
from homeassistant.core import callback

from ..buspro import DATA_BUSPRO
from .pybuspro.devices import UniversalSwitch
from .pybuspro.helpers import parse_device_address

logger = logging.getLogger(__name__)

DEVICE_SCHEMA = vol.Schema({
    vol.Required(CONF_NAME): cv.string,
})

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_DEVICES): {cv.string: DEVICE_SCHEMA},
})


# noinspection PyUnusedLocal
async def async_setup_platform(hass, config, async_add_entites, discovery_info=None):
    """Set up Buspro switch devices."""
    devices = []

    for address, device_config in config[CONF_DEVICES].items():
        devices.append(BusproSwitch(hass, address, device_config))

    async_add_entites(devices)


# noinspection PyAbstractClass
class BusproSwitch(SwitchEntity):
    """Representation of a Buspro switch."""
    def __init__(self, hass, address, device_config):        
        self._hass = hass
        self._name = device_config[CONF_NAME]
        self._device_key = address

        device_address, channel_number = parse_device_address(address)
        self._device = UniversalSwitch(hass.data[DATA_BUSPRO].hdl, device_address, channel_number)

        self.async_register_callbacks()

    @callback
    def async_register_callbacks(self):
        """Register callbacks to update hass after device was changed."""

        async def after_update_callback(device):
            """Call after device was updated."""
            await self.async_update_ha_state()

        self._device.register_device_updated_cb(after_update_callback)

    @property
    def should_poll(self):
        """No polling needed within Buspro."""
        return False

    @property
    def name(self):
        """Return the display name of this light."""
        return self._name

    @property
    def available(self):
        """Return True if entity is available."""
        return self._device.is_connected

    @property
    def is_on(self):
        """Return true if light is on."""
        return self._device.is_on

    async def async_turn_on(self, **kwargs):
        """Instruct the switch to turn on."""
        await self._device.set_on()

    async def async_turn_off(self, **kwargs):
        """Instruct the switch to turn off."""
        await self._device.set_off()

    @property
    def unique_id(self):
        """Return the unique id."""
        return self._device_key
