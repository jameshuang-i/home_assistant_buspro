"""
This component provides sensor support for Buspro.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/...
"""

import logging
from datetime import timedelta

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.const import (
    CONF_NAME, 
    CONF_DEVICES, 
    CONF_ADDRESS, 
    CONF_TYPE, 
    CONF_UNIT_OF_MEASUREMENT,
    ILLUMINANCE, 
    TEMPERATURE, 
    CONF_DEVICE_CLASS, 
    CONF_SCAN_INTERVAL,
)
from homeassistant.core import callback
from homeassistant.helpers.entity import Entity

from ..buspro import DATA_BUSPRO

DEFAULT_CONF_UNIT_OF_MEASUREMENT = ""
DEFAULT_CONF_DEVICE_CLASS = "None"
DEFAULT_CONF_SCAN_INTERVAL = 0
DEFAULT_CONF_OFFSET = 0
CONF_DEVICE = "device"
CONF_OFFSET = "offset"
SCAN_INTERVAL = timedelta(minutes=2)

_LOGGER = logging.getLogger(__name__)

SENSOR_TYPES = {
    ILLUMINANCE,
    TEMPERATURE,
}

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_DEVICES):
        vol.All(cv.ensure_list, [
            vol.All({
                vol.Required(CONF_ADDRESS): cv.string,
                vol.Required(CONF_NAME): cv.string,
                vol.Required(CONF_TYPE): vol.In(SENSOR_TYPES),
                vol.Optional(CONF_UNIT_OF_MEASUREMENT, default=DEFAULT_CONF_UNIT_OF_MEASUREMENT): cv.string,
                vol.Optional(CONF_DEVICE_CLASS, default=DEFAULT_CONF_DEVICE_CLASS): cv.string,
                vol.Optional(CONF_DEVICE, default=None): cv.string,
                vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_CONF_SCAN_INTERVAL): cv.string,
                vol.Optional(CONF_OFFSET, default=DEFAULT_CONF_OFFSET): cv.string,
            })
        ])
})

async def async_setup_platform(hass, config, async_add_entites, discovery_info=None):
    """Set up Buspro switch devices."""
    from .pybuspro.devices import Sensor

    devices = []
    for device_config in config[CONF_DEVICES]:
        devices.append(BusproSensor(hass, device_config))

    async_add_entites(devices)


# noinspection PyAbstractClass
class BusproSensor(Entity):
    """Representation of a Buspro switch."""
    def __init__(self, hass, device_config):
        from .pybuspro.devices import Sensor

        self._hass = hass  
        self._name = device_config[CONF_NAME]
        self._sensor_type = device_config[CONF_TYPE]
        self._address = device_config[CONF_ADDRESS]
        self._offset = device_config[CONF_OFFSET]
        interval = device_config[CONF_SCAN_INTERVAL] or 0
        self._scan_interval = int(interval)

        device = device_config[CONF_DEVICE]     
        addrs = self._address.split('.')
        device_address = (int(addrs[0]), int(addrs[1]))
        self._device = Sensor(self._hass.data[DATA_BUSPRO].hdl, device_address, device=device)
        self.async_register_callbacks()

    @callback
    def async_register_callbacks(self):
        """Register callbacks to update hass after device was changed."""

        async def after_update_callback(device):
            """Call after device was updated."""
            if self._hass is not None:
                self.async_write_ha_state()

        self._device.register_device_updated_cb(after_update_callback)

    @property
    def should_poll(self):
        """No polling needed within Buspro unless explicitly set."""
        return self._scan_interval > 0

    async def async_update(self):
        await self._device.read_sensor_status()

    @property
    def name(self):
        """Return the display name of this light."""
        return self._name

    @property
    def available(self):
        """Return True if entity is available."""
        if self._device.is_connected:
            if self._sensor_type == TEMPERATURE and self.current_temperature is not None:
                return True
            elif self._sensor_type == ILLUMINANCE and self._brightness is not None:
                return True
        
        return False

    @property
    def state(self):
        """Return the state of the sensor."""
        if self._sensor_type == TEMPERATURE:
            return self.current_temperature

        if self._sensor_type == ILLUMINANCE:
            return self._device.brightness

    @property
    def current_temperature(self):
        if self._offset and self._device.temperature is not None:
            return self._device.temperature + int(self._offset)
        else:
            return self._device.temperature
        
    @property
    def device_class(self):
        """Return the class of this sensor."""
        return self._sensor_type

    @property
    def unit_of_measurement(self):
        """Return the unit this state is expressed in."""
        if self._sensor_type == TEMPERATURE:
            return "°C"
        if self._sensor_type == ILLUMINANCE:
            return "lux"
        return ""

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        attributes = {}
        attributes['state_class'] = "measurement"
        return attributes

    @property
    def unique_id(self):
        """Return the unique id."""
        return f"{self._address}-{self._sensor_type}"
