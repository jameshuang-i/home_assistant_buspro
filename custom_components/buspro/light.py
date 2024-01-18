"""
This component provides light support for Buspro.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/...
"""

import logging

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.components.light import LightEntity, PLATFORM_SCHEMA, SUPPORT_BRIGHTNESS, ATTR_BRIGHTNESS
from homeassistant.const import (CONF_NAME, CONF_DEVICES)
from homeassistant.core import callback

from ..buspro import DATA_BUSPRO

_LOGGER = logging.getLogger(__name__)

DEFAULT_DEVICE_RUNNING_TIME = 0
DEFAULT_PLATFORM_RUNNING_TIME = 0
DEFAULT_DIMMABLE = False

DEVICE_SCHEMA = vol.Schema({
    vol.Optional("running_time", default=DEFAULT_DEVICE_RUNNING_TIME): cv.positive_int,
    vol.Optional("dimmable", default=DEFAULT_DIMMABLE): cv.boolean,
    vol.Required(CONF_NAME): cv.string,
})

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_DEVICES): {cv.string: DEVICE_SCHEMA},
})


# noinspection PyUnusedLocal
async def async_setup_platform(hass, config, async_add_entites, discovery_info=None):
    """Set up Buspro light devices."""
    devices = []

    for key, device_config in config[CONF_DEVICES].items():
        devices.append(BusproLight(hass, key, device_config))

    async_add_entites(devices)


# noinspection PyAbstractClass
class BusproLight(LightEntity):
    """Representation of a Buspro light."""

    def __init__(self, hass, key, device_config):
        from .pybuspro.devices import Light

        self._hass = hass
        self._name = device_config[CONF_NAME]        
        self._device_id = key
        # 创建light设备
        _addrs = key.split('.')
        buspro = hass.data[DATA_BUSPRO].hdl
        device_address = (int(_addrs[0]), int(_addrs[1]))
        channel_num = int(_addrs[2])
        device_running_time = int(device_config["running_time"])
        dimmable = bool(device_config["dimmable"])
        self._device = Light(buspro, device_address, channel_num, dimmable, device_running_time)

        self.async_register_callbacks()

    @callback
    def async_register_callbacks(self):
        """Register callbacks to update hass after device was changed."""

        # noinspection PyUnusedLocal
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
    def brightness(self):
        """Return the brightness of the light."""
        brightness = self._device.current_brightness / 100 * 255
        return brightness

    @property
    def supported_features(self):
        """Flag supported features."""
        flags = 0
        if self._device.supports_brightness:
            flags |= SUPPORT_BRIGHTNESS
        return flags

    @property
    def is_on(self):
        """Return true if light is on."""
        return self._device.is_on

    async def async_turn_on(self, **kwargs):
        """Instruct the light to turn on."""
        brightness = int(kwargs.get(ATTR_BRIGHTNESS, 255) / 255 * 100)

        # 如果只是打开灯，那灯的亮度设置为之前关闭灯时的亮度
        if not self.is_on and self._device.previous_brightness is not None and brightness == 100:
            brightness = self._device.previous_brightness

        await self._device.set_brightness(brightness)

    async def async_turn_off(self, **kwargs):
        """Instruct the light to turn off."""
        await self._device.set_off()

    @property
    def unique_id(self):
        """Return the unique id."""
        return self._device_id
