"""
This component provides remote control support for Tuya.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/...
"""

import logging
from datetime import timedelta
from enum import Enum
from tinytuya.Contrib.RFRemoteControlDevice import RFRemoteControlDevice
import voluptuous as vol

import homeassistant.helpers.config_validation as cv
from homeassistant.components.button import ButtonEntity, PLATFORM_SCHEMA
from homeassistant.helpers.entity_component import EntityComponent
from homeassistant.helpers.typing import ConfigType
from homeassistant.const import (CONF_NAME, CONF_DEVICES)

from . import DOMAIN

SCAN_INTERVAL = timedelta(seconds=30)

logger = logging.getLogger(__name__)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_DEVICES): vol.All(cv.ensure_list, [
        vol.All({
            vol.Required(CONF_NAME): cv.string,
            vol.Required("id"): cv.string,
            vol.Required("ip"): cv.string,
            vol.Required("local_key"): cv.string,
            vol.Optional("persist", default=True): cv.boolean,
            vol.Optional("control_type", default=1): vol.Coerce(int),
        })
    ])
})

class CommandType(Enum):
    RF = "rf"
    IR = "ir"

async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up Button entities."""
    component = hass.data[DOMAIN] = EntityComponent[TuyaRemoter](
        logger, DOMAIN, hass, SCAN_INTERVAL
    )
    await component.async_setup(config)

    component.async_register_entity_service(
            "Send_Command",
            {
                vol.Required("code"): cv.string,
                vol.Required("command_type"): vol.Coerce(CommandType),
            },
            "async_handle_send_command")

    return True

async def async_setup_platform(hass, config, async_add_entites, discovery_info=None):
    devices = []

    for device_config in config.get(CONF_DEVICES, []):
        device = TuyaRemoter(hass, device_config)
        devices.append(device)

    async_add_entites(devices)

class TuyaRemoter(ButtonEntity):
    def __init__(self, hass, config):        
        self._hass = hass
        self._name = config[CONF_NAME]
        self._device_id = config["id"]

        self._device = RFRemoteControlDevice(config["id"], address=config["ip"], local_key=config["local_key"], control_type=config["control_type"], persist=config["persist"])

    @property
    def name(self):
        return self._name

    @property
    def available(self):
        return True
    
    def send_rf_command(code):
        self._device.rf_send_button(code)
    
    def send_ir_command(code):
        self._device.send_button(code)

    async def async_handle_send_command(self, code:str, command_type:str):
        if command_type==CommandType.RF.value:
            await self._hass.async_add_executor_job(self.send_rf_command(code))
        elif command_type==CommandType.IR.value:
            await self._hass.async_add_executor_job(self.send_ir_command(code))
        else:
            logger.error(f"TuyaRemoter Not support the command type {command_type}")

    @property
    def unique_id(self):
        return self._device_id
