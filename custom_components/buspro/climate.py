"""
This component provides sensor support for Buspro.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/...
"""

import logging
from typing import Optional, List

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.components.climate import (PLATFORM_SCHEMA, ClimateEntity, ClimateEntityFeature, HVACMode, HVACAction,)
from homeassistant.components.climate.const import (SUPPORT_PRESET_MODE, SUPPORT_TARGET_TEMPERATURE,)
from homeassistant.const import (CONF_NAME, CONF_DEVICES, CONF_ADDRESS, ATTR_TEMPERATURE, UnitOfTemperature,)
from homeassistant.core import callback, HomeAssistant
from ..buspro import DATA_BUSPRO
from .pybuspro.enums import OnOffStatus, PresetMode, TemperatureType
from .pybuspro.helpers import parse_device_address
from .pybuspro.devices import FloorHeating

_LOGGER = logging.getLogger(__name__)

CONF_PRESET_MODES = "preset_modes"

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_DEVICES):
        vol.All(cv.ensure_list, [
            vol.All({
                vol.Required(CONF_ADDRESS): cv.string,
                vol.Required(CONF_NAME): cv.string,
                vol.Optional(CONF_PRESET_MODES, default=[]): vol.All(cv.ensure_list, [p.name for p in PresetMode])
            })
        ])
})


async def async_setup_platform(hass:HomeAssistant, config, async_add_entites, discovery_info=None):
    async_add_entites([BusproClimate(hass, device_config) for device_config in config[CONF_DEVICES]])
    

class BusproClimate(ClimateEntity):
    """Representation of a Buspro climate."""
    def __init__(self, hass:HomeAssistant, device_config:dict) -> None:       
        self._hass:HomeAssistant = hass
        self._device_key:str = device_config[CONF_ADDRESS]
        self._name:str = device_config[CONF_NAME]
        self._preset_modes:Optional[List[str]] = device_config[CONF_PRESET_MODES]

        device_address, _ = parse_device_address(self._device_key)
        self._device:FloorHeating = FloorHeating(self._hass.data[DATA_BUSPRO].hdl, device_address)

        self.async_register_callbacks()

    @callback
    def async_register_callbacks(self):
        """Register callbacks to update hass after device was changed."""
        async def after_update_callback(device):
            """Call after device was updated."""
            # logger.debug(f"Device '{self._device.name} IsOn={self._is_on} Mode={self._device.mode} TargetTemp={self._device.target_temperature}")
            self.async_write_ha_state()

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
    def temperature_unit(self):
        """Return the unit of measurement."""
        if self._device.unit_of_measurement == TemperatureType.Celsius:
            return UnitOfTemperature.CELSIUS
        elif self._device.unit_of_measurement == TemperatureType.Fahrenheit:
            return UnitOfTemperature.FAHRENHEIT
        else:
            _LOGGER.error(f"Not supported the temperature type: {self._device._temperature_type}, return Celsius default.")
            return UnitOfTemperature.CELSIUS

    @property
    def current_temperature(self):
        """Return the current temperature."""
        return self._device.current_temperature

    @property
    def target_temperature(self):
        """Return the temperature we try to reach."""
        return self._device.target_temperature

    @property
    def supported_features(self):
        """Return the list of supported features."""
        support = SUPPORT_TARGET_TEMPERATURE
        if len(self._preset_modes) > 0:
            support |= SUPPORT_PRESET_MODE
        return support

    @property
    def preset_mode(self) -> Optional[str]:
        """Return the current preset mode, e.g., home, away, temp.
        """
        return self._device.preset_mode

    @property
    def preset_modes(self) -> Optional[List[str]]:
        """Return a list of available preset modes.
        Requires SUPPORT_PRESET_MODE.
        """
        return self._preset_modes

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set new preset mode."""
        mode = None
        for p in PresetMode:
            if p.name == preset_mode:
                mode = p
                break
        if mode:
            _LOGGER.debug(f"Setting preset mode to '{mode}' for device '{self._name}'")
            await self._device.async_set_preset_mode(mode)
        else:
            _LOGGER.error(f"Not supported the preset mode '{preset_mode}'")

    @property
    def hvac_action(self) -> Optional[str]:
        """Return current action ie. heating, idle, off."""
        if self._device.is_on:
            return HVACAction.HEATING
        else:
            return HVACAction.OFF

    @property
    def hvac_mode(self) -> Optional[str]:
        """Return current operation ie. heat, cool, idle."""
        if self._device.is_on:
            return HVACMode.HEAT
        else:
            return HVACMode.OFF

    @property
    def hvac_modes(self) -> Optional[List[str]]:
        """Return the list of available operation modes."""
        return [HVACMode.HEAT, HVACMode.OFF]

    async def async_set_hvac_mode(self, hvac_mode: str) -> None:
        """Set operation mode."""
        if hvac_mode == HVACMode.OFF:
            await self._device.async_turn_off()
        elif hvac_mode == HVACMode.HEAT:
            await self._device.async_turn_on()
        else:
            _LOGGER.error("Unrecognized hvac mode: %s", hvac_mode)
            return

    @property
    def target_temperature_step(self):
        """Return the supported step of target temperature."""
        return 1

    @property
    def unique_id(self):
        """Return the unique id."""
        return self._device_key

    async def async_set_temperature(self, **kwargs):
        """Set new target temperature."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return
        target_temperature = int(temperature)
        _LOGGER.debug(f"Setting target temperature to {target_temperature}")

        await self._device.async_set_target_temperature(temperature)
