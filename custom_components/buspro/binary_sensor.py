"""
This component provides binary sensor support for Buspro.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/...
"""

import logging

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.components.binary_sensor import (PLATFORM_SCHEMA, BinarySensorEntity,)
from homeassistant.const import (CONF_NAME, CONF_DEVICES, CONF_ADDRESS, CONF_TYPE, CONF_DEVICE_CLASS, CONF_SCAN_INTERVAL,)
from homeassistant.core import callback, HomeAssistant

from ..buspro import DATA_BUSPRO
from .pybuspro.devices import Sensor

_LOGGER = logging.getLogger(__name__)

# TODO: 
# SCAN_INTERVAL = timedelta(minutes=1)

DEFAULT_CONF_DEVICE_CLASS = "None"
DEFAULT_CONF_SCAN_INTERVAL = 0

CONF_MOTION = 'motion'
CONF_DRY_CONTACT_1 = 'dry_contact_1'
CONF_DRY_CONTACT_2 = 'dry_contact_2'
CONF_UNIVERSAL_SWITCH = 'universal_switch'
CONF_SINGLE_CHANNEL = 'single_channel'
CONF_DRY_CONTACT = 'dry_contact'

SENSOR_TYPES = {
    CONF_MOTION,
    CONF_DRY_CONTACT_1,
    CONF_DRY_CONTACT_2,
    CONF_UNIVERSAL_SWITCH,
    CONF_SINGLE_CHANNEL,
    CONF_DRY_CONTACT,
}

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_DEVICES):
        vol.All(cv.ensure_list, [
            vol.All({
                vol.Required(CONF_ADDRESS): cv.string,
                vol.Required(CONF_NAME): cv.string,
                vol.Required(CONF_TYPE): vol.In(SENSOR_TYPES),
                vol.Optional(CONF_DEVICE_CLASS, default=DEFAULT_CONF_DEVICE_CLASS): cv.string,
                vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_CONF_SCAN_INTERVAL): cv.string
            })
        ])
})

async def async_setup_platform(hass, config, async_add_entites, discovery_info=None):
    """Set up Buspro binary sensor devices."""
    sync_add_entites([BusproBinarySensor(hass, device_config) for device_config in config[CONF_DEVICES]])

class BusproBinarySensor(BinarySensorEntity):
    """Representation of a Buspro switch."""
    def __init__(self, hass:HomeAssistant, device_config:dict):      
        self._hass:HomeAssistant = hass        
        self._name:str = device_config[CONF_NAME]
        self._scan_interval:int = int(device_config[CONF_SCAN_INTERVAL]) if CONF_SCAN_INTERVAL in device_config else 0  
        self._device_class:str = device_config[CONF_DEVICE_CLASS]
        self._address:str = device_config[CONF_ADDRESS]
        self._sensor_type:str = device_config[CONF_TYPE]  

        _addrs = self._address.split('.')
        device_address = (int(_addrs[0]), int(_addrs[1]))
        universal_switch_number = int(_addrs[2]) if self._sensor_type == CONF_UNIVERSAL_SWITCH else None
        channel_number = int(_addrs[2]) if self._sensor_type == CONF_SINGLE_CHANNEL else None
        switch_number = int(_addrs[2]) if self._sensor_type == CONF_DRY_CONTACT else None
        _LOGGER.debug(f"Creating sensor for {self._name} ...")   
        self._device:Sensor = Sensor(self._hass.data[DATA_BUSPRO].hdl, device_address, universal_switch_number, channel_number, None, switch_number)

        self.async_register_callbacks()

    @callback
    def async_register_callbacks(self):
        """Register callbacks to update hass after device was changed."""
        async def after_update_callback(device):
            """Call after device was updated."""
            await self.async_write_ha_state()

        self._device.register_device_updated_cb(after_update_callback)

    @property
    def should_poll(self):
        """No polling needed within Buspro."""
        return self._scan_interval > 0  # 轮询时间为全局

    async def async_update(self):
        # if self._sensor_type == CONF_UNIVERSAL_SWITCH:
        await self._device.read_sensor_status()

    @property
    def name(self):
        """Return the display name of this light."""
        return self._name

    @property
    def available(self):
        """Return True if entity is available."""
        return self._device.is_connected

    @property
    def device_class(self):
        """Return the class of this sensor."""
        return self._device_class

    @property
    def unique_id(self):
        """Return the unique id."""
        return f"BinarySensor_{self._address}"

    @property
    def is_on(self):
        """Return true if the binary sensor is on."""
        if self._sensor_type == CONF_MOTION:
            return self._device.movement
        elif self._sensor_type == CONF_DRY_CONTACT_1:
            return self._device.dry_contact_1_is_on
        elif self._sensor_type == CONF_DRY_CONTACT_2:
            return self._device.dry_contact_2_is_on
        elif self._sensor_type == CONF_UNIVERSAL_SWITCH:
            return self._device.universal_switch_is_on
        elif self._sensor_type == CONF_SINGLE_CHANNEL:
            return self._device.single_channel_is_on
        elif self._sensor_type == CONF_DRY_CONTACT:
            return self._device.switch_status
        else:
            return None
