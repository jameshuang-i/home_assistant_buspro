import asyncio
import logging
from ..telegram import Telegram, ReadFloorHeatingStatusData, ReadFloorHeatingStatusResponseData, ControlFloorHeatingStatusData, ControlFloorHeatingStatusResponseData, BroadcastTemperatureResponseData
from .device import Device
from ..helpers import copy_class_attrs
from ..enums import *

logger = logging.getLogger(__name__)

class FloorHeating(Device):
    def __init__(self, buspro, device_address):
        super().__init__(buspro, device_address)
        self._temperature_type = None   # Celsius/Fahrenheit
        self._status = None             # On/Off
        self._mode = None               # 1/2/3/4/5 (Normal/Day/Night/Away/Timer)
        self._current_temperature = None
        self._normal_temperature = None
        self._day_temperature = None
        self._night_temperature = None
        self._away_temperature = None

        self.register_telegram_received_cb(self._telegram_received_cb)
        self.call_read_current_heating_status(run_from_init=True)

    def _telegram_received_cb(self, telegram):
        if isinstance(telegram, ReadFloorHeatingStatusResponseData):
            copy_class_attrs(telegram, self)
            self.call_device_updated()
        elif isinstance(telegram, ControlFloorHeatingStatusResponseData):
            if telegram._success == SuccessOrFailure.Success:
                copy_class_attrs(telegram, self)
                self.call_device_updated()
        elif isinstance(telegram, BroadcastTemperatureResponseData):
            copy_class_attrs(telegram, self)
            self.call_device_updated()
        else:
            logger.warning(f"Not supported message for operate type {telegram.operate_code.name}")

    def _telegram_received_control_heating_status_cb(self, telegram, floor_heating_status:ControlFloorHeatingStatusData):
        if isinstance(telegram, ReadFloorHeatingStatusResponseData):
            self.unregister_device_updated_cb(self._telegram_received_control_heating_status_cb, floor_heating_status)

            control = ControlFloorHeatingStatusData(self._device_address)
            copy_class_attrs(control, telegram)
            copy_class_attrs(floor_heating_status, control)
            logger.debug(f"Trying to control the floor heating to {control}")
            
            async def _send_control_floor_heating_status(buspro, control):
                await buspro.send_telegram(control)
            asyncio.ensure_future(_send_control_floor_heating_status(self._buspro, control), loop=self._buspro.loop)

    async def control_heating_status(self, floor_heating_status: ControlFloorHeatingStatusData):
        self.register_telegram_received_cb(self._telegram_received_control_heating_status_cb, floor_heating_status)
        await self._read_current_heating_status()

    def call_read_current_heating_status(self, run_from_init=False):      
        asyncio.ensure_future(self._read_current_heating_status(run_from_init), loop=self._buspro.loop)

    async def _read_current_heating_status(self, run_from_init=False):
        if run_from_init:
            await asyncio.sleep(5)

        control = ReadFloorHeatingStatusData(self._device_address)
        await self._buspro.send_telegram(control)

    @property
    def is_on(self):
        return False if self._status == OnOffStatus.OFF.value else True

    @property
    def unit_of_measurement(self):
        return TemperatureType.value_of(self._temperature_type)

    @property
    def preset_mode(self):
        mode = PresetMode.value_of(self._mode)
        # HDL 中还有一个Timer的模式
        return mode if mode else PresetMode.none

    @property
    def current_temperature(self):
        return self._current_temperature

    @property
    def target_temperature(self):
        if self.preset_mode == PresetMode.home:
            return self._day_temperature
        elif self.preset_mode == PresetMode.away:
            return self._away_temperature
        elif self.preset_mode == PresetMode.sleep:
            return self._night_temperature
        else:
            return self._normal_temperature

    async def async_turn_on(self):
        control = ControlFloorHeatingStatusData(self._device_address)
        control._status = OnOffStatus.ON.value
        await self.control_heating_status(control)
    
    async def async_turn_off(self):
        control = ControlFloorHeatingStatusData(self._device_address)
        control._status = OnOffStatus.OFF.value
        await self.control_heating_status(control)
    
    async def async_set_preset_mode(self, mode:PresetMode):
        control = ControlFloorHeatingStatusData(self._device_address)
        control._mode = mode.value
        await self.control_heating_status(control)
    
    async def async_set_target_temperature(self, temperature):
        control = ControlFloorHeatingStatusData(self._device_address)
        if self.preset_mode == PresetMode.home:
            control._day_temperature = temperature
        elif self.preset_mode == PresetMode.away:
            control._away_temperature = temperature
        elif self.preset_mode == PresetMode.sleep:
            control._night_temperature = temperature
        else:
            control._normal_temperature = temperature
        await self.control_heating_status(control)
