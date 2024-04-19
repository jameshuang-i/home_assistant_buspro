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
from homeassistant.components.climate.const import (ClimateEntityFeature, FAN_AUTO, FAN_LOW, FAN_MEDIUM, FAN_HIGH)
from homeassistant.const import (CONF_NAME, CONF_DEVICES, CONF_ADDRESS, ATTR_TEMPERATURE, UnitOfTemperature,)
from homeassistant.core import callback, HomeAssistant
from ..buspro import DATA_BUSPRO
from .pybuspro.enums import OnOffStatus, PresetMode, TemperatureType, AirConditionMode, FanMode
from .pybuspro.helpers import parse_device_address
from .pybuspro.devices import AirCondition, FloorHeating

FLOORHEATING = "heating"
AIRCONDITION = "ac"

_LOGGER = logging.getLogger(__name__)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_DEVICES): {
        cv.string: vol.Schema({
            vol.Required(CONF_NAME): cv.string,
            vol.Optional("type", default=AIRCONDITION): cv.string,
        })
    },
})

FAN_MODE_TRANSLATE = [FAN_AUTO, FAN_HIGH, FAN_MEDIUM, FAN_LOW]
MODE_TRANSLATE = [HVACMode.COOL, HVACMode.HEAT, HVACMode.FAN_ONLY, HVACMode.AUTO, HVACMode.DRY]
TEMPERATURE_TYPE_TRANSLATE = [UnitOfTemperature.CELSIUS, UnitOfTemperature.FAHRENHEIT]

async def async_setup_platform(hass:HomeAssistant, config, async_add_entites, discovery_info=None):
    devices = []

    for key, device_config in config[CONF_DEVICES].items():
        devices.append(BusproClimate(hass, key, device_config))

    async_add_entites(devices)
    

class BusproClimate(ClimateEntity):
    """Representation of a Buspro climate."""
    def __init__(self, hass:HomeAssistant, key:str, device_config:dict) -> None:       
        self._hass:HomeAssistant = hass
        self._device_key:str = key
        self._name:str = device_config[CONF_NAME]
        self._type = device_config['type']

        device_address, number = parse_device_address(key)
        if self._type==AIRCONDITION:
            self._device:AirCondition = AirCondition(self._hass.data[DATA_BUSPRO].hdl, device_address, number)
        elif self._type==FLOORHEATING:
            self._device:FloorHeating = FloorHeating(self._hass.data[DATA_BUSPRO].hdl, device_address)
        else:
            _LOGGER.error(f"Not supported the climate device type: {self._type}.")

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
    def unique_id(self):
        """Return the unique id."""
        return self._device_key
    
    @property
    def supported_features(self):
        """Return the list of supported features."""
        support  = ClimateEntityFeature.TARGET_TEMPERATURE 
        if self._type == AIRCONDITION:
            # support |= ClimateEntityFeature.TARGET_HUMIDITY 
            support |= ClimateEntityFeature.FAN_MODE 
            # 老板本中没有这两个
            # support |= ClimateEntityFeature.TURN_OFF 
            # support |= ClimateEntityFeature.TURN_ON 
        return support

    @property
    def temperature_unit(self):
        """Return the unit of measurement."""
        if self._device.unit_of_measurement:
            return TEMPERATURE_TYPE_TRANSLATE[self._device.unit_of_measurement.value]
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

    async def async_set_temperature(self, **kwargs):
        """Set new target temperature."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return
        target_temperature = int(temperature)
        _LOGGER.debug(f"Setting target temperature to {target_temperature}")

        await self._device.async_set_target_temperature(target_temperature)

    @property
    def target_temperature_step(self):
        """Return the supported step of target temperature."""
        return 1

    # @property
    # def preset_mode(self) -> Optional[str]:
    #     """Return the current preset mode, e.g., home, away, temp.
    #     """
    #     return self._device.preset_mode

    # @property
    # def preset_modes(self) -> Optional[List[str]]:
    #     """Return a list of available preset modes.
    #     Requires SUPPORT_PRESET_MODE.
    #     """
    #     return self._preset_modes

    # async def async_set_preset_mode(self, preset_mode: str) -> None:
    #     """Set new preset mode."""
    #     mode = None
    #     for p in PresetMode:
    #         if p.name == preset_mode:
    #             mode = p
    #             break
    #     if mode:
    #         _LOGGER.debug(f"Setting preset mode to '{mode}' for device '{self._name}'")
    #         await self._device.async_set_preset_mode(mode)
    #     else:
    #         _LOGGER.error(f"Not supported the preset mode '{preset_mode}'")

    @property
    def hvac_action(self) -> Optional[str]:
        """Return current action ie. heating, idle, off."""
        if self._device.is_on:
            if self._device.mode == AirConditionMode.Cool:
                return HVACAction.COOLING 
            elif self._device.mode == AirConditionMode.Heat:
                return HVACAction.HEATING
            elif self._device.mode == AirConditionMode.Fan:
                return HVACAction.FAN 
            elif self._device.mode == AirConditionMode.Dry:
                return HVACAction.DRYING
            elif self._device.mode == AirConditionMode.Auto:
                 return HVACAction.COOLING #自动模式下默认返回制冷吧
            else:
                return HVACAction.IDLE 
        else:
            return HVACAction.OFF

    @property
    def hvac_mode(self) -> Optional[str]:
        """Return current operation ie. heat, cool, idle."""
        if self._device.is_on:
            if self._device.mode:
                return MODE_TRANSLATE[self._device.mode.value]
            else:
                _LOGGER.error(f"Not supported the hvac mode: {self._device._mode}, return Auto default.")
                return HVACMode.AUTO
        else:
            return HVACMode.OFF

    @property
    def hvac_modes(self) -> Optional[List[str]]:
        """Return the list of available operation modes."""
        # 我的设置不支持自动模式
        if self._type==AIRCONDITION:
            return [mode for mode in MODE_TRANSLATE if mode!=HVACMode.AUTO] + [HVACMode.OFF]
        elif self._type==FLOORHEATING:
            return [HVACMode.HEAT, HVACMode.OFF]
        else:
            _LOGGER.error(f"Not supported the climate type: {self._type}.")

    async def async_set_hvac_mode(self, hvac_mode: str) -> None:
        """Set operation mode."""
        if hvac_mode == HVACMode.OFF:
            await self._device.async_turn_off()
        else:
            for index in range(len(MODE_TRANSLATE)):
                if MODE_TRANSLATE[index] == hvac_mode:
                    break
            else:
                _LOGGER.error("Unrecognized hvac mode: %s", hvac_mode)
                return
            await self._device.async_set_mode(AirConditionMode.value_of(index))            
    
    @property
    def fan_mode(self) -> str | None:
        """Return the fan setting.
        Requires ClimateEntityFeature.FAN_MODE.
        """
        if self._device.fan_mode:
            return FAN_MODE_TRANSLATE[self._device.fan_mode.value]
        else:
            _LOGGER.error(f"Unrecognized fan mode: {self._device._fan}")
            return

    @property
    def fan_modes(self) -> list[str] | None:
        """Return the list of available fan modes.
        Requires ClimateEntityFeature.FAN_MODE.
        """
        # 我的设备不支持自动风
        if self._type==AIRCONDITION:
            return [fan for fan in FAN_MODE_TRANSLATE if fan!=FAN_AUTO] 
        elif self._type==FLOORHEATING:
            return None
        else:
            _LOGGER.error(f"Not supported the climate type: {self._type}.")
    
    async def async_set_fan_mode(self, fan_mode: str) -> None:
        """Set new target fan mode."""
        for index in range(len(FAN_MODE_TRANSLATE)):
            if FAN_MODE_TRANSLATE[index] == fan_mode:
                break
        else:
            _LOGGER.error("Unrecognized fan mode: %s", fan_mode)
            return None
        await self._device.async_set_fan_mode(FanMode.value_of(index)) 
    
    async def async_turn_on(self) -> None:
        """Turn the entity on."""
        await self._device.async_turn_on()
    
    async def async_turn_off(self) -> None:
        """Turn the entity off."""
        await self._device.async_turn_off()
