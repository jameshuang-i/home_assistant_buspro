"""
This component provides remote control support for Tuya.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/...
"""

import logging
import asyncio
from datetime import timedelta
from enum import Enum
from tinytuya.Contrib.RFRemoteControlDevice import RFRemoteControlDevice
import voluptuous as vol

from homeassistant.core import HomeAssistant
from homeassistant.components.button import ButtonEntity, PLATFORM_SCHEMA
from homeassistant.helpers import config_validation as cv, entity_platform, service
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

def async_register_services():
    platform = entity_platform.async_get_current_platform()

    platform.async_register_entity_service(
        "send_command",
        {
            vol.Required("command_code"): cv.string,
            vol.Required("command_type"): vol.Coerce(CommandType),
        },
        async_send_command,
    )

async def async_setup_platform(hass, config, async_add_entites, discovery_info=None):
    devices = []

    for device_config in config.get(CONF_DEVICES, []):
        device = TuyaRemoter(hass, device_config)
        devices.append(device)

    async_add_entites(devices)
    async_register_services()

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
    
    def press(self):
        pass
    
    def send_rf_command(self, code):
        self._device.rf_send_button(code)
    
    def send_ir_command(self, code):
        self._device.send_button(code)

    def async_handle_send_command(self, command_code:str, command_type:CommandType):
        if command_type==CommandType.RF:            
            self.send_rf_command(command_code)
        elif command_type==CommandType.IR:
            self.send_ir_command(command_code)
        else:
            logger.error(f"TuyaRemoter Not support the command type {command_type}")

    @property
    def unique_id(self):
        return self._device_id

def async_send_command(entity, service_call):
    entity.async_handle_send_command(service_call.data['command_code'], service_call.data['command_type'])