import asyncio
import logging
from ..telegram import Telegram, ControlAirConditionData, ControlAirConditionResponseData, ReadAirConditionStatusData, ReadAirConditionStatusResponseData
from .device import Device
from ..helpers import copy_class_attrs
from ..enums import AirConditionMode, FanMode, OnOffStatus, TemperatureType

logger = logging.getLogger(__name__)

class AirCondition(Device):
    def __init__(self, buspro, device_address, ac_number):
        super().__init__(buspro, device_address)
        self.ac_number = ac_number
        self._temperature_type = None # 0-C, 1-F
        self._current_temperature = None
        self._cool_temperature = None
        self._heat_temperature = None
        self._auto_temperature = None
        self._dry_temperature = None
        self._status = None # 0-OFF, 1-ON
        self._mode = None # 0-COOL, 1-Heat, 2-FAN, 3-Auto, 4-Dry
        self._fan = None # 0-Auto, 1-High, 2-Medium, 3-Low

        self.register_telegram_received_cb(self._telegram_received_cb)
        self.call_read_air_condition_status(run_from_init=True)

    def _telegram_received_cb(self, telegram, postfix=None):
        if isinstance(telegram, ReadAirConditionStatusResponseData):
            if telegram._ac_number == self.ac_number:
                copy_class_attrs(telegram, self)
                self.call_device_updated()
        elif isinstance(telegram, ControlAirConditionResponseData):
            if telegram._ac_number == self.ac_number:
                copy_class_attrs(telegram, self)
                self.call_device_updated()
        else:
            logger.debug(f"Not supported message for operate type {telegram}")

    def _telegram_received_control_status_cb(self, telegram, air_condition_status:ControlAirConditionData):
        if isinstance(telegram, ReadAirConditionStatusResponseData):
            if telegram._ac_number == self.ac_number:
                self.unregister_telegram_received_cb(self._telegram_received_control_status_cb, air_condition_status)
                
                logger.debug(f"air_condition_status = {air_condition_status}")
                logger.debug(f"ReadAirConditionStatusResponseData = {telegrame}")
                control = ControlAirConditionData(self._device_address)
                logger.debug(f"origin control = {control}")
                copy_class_attrs(telegram, control)
                logger.debug(f"refresh control = {control}")
                copy_class_attrs(air_condition_status, control)
                logger.debug(f"Trying to control the air condition to {control}")
                
                async def _send_control_air_condition_status(buspro, control):
                    await buspro.send_telegram(control)
                asyncio.ensure_future(_send_control_air_condition_status(self._buspro, control), loop=self._buspro.loop)

    async def control_status(self, air_condition_status: ControlAirConditionData):
        self.register_telegram_received_cb(self._telegram_received_control_status_cb, air_condition_status)
        await self._read_air_condition_status()

    def call_read_air_condition_status(self, run_from_init=False):      
        asyncio.ensure_future(self._read_air_condition_status(run_from_init), loop=self._buspro.loop)

    async def _read_air_condition_status(self, run_from_init=False):
        if run_from_init:
            await asyncio.sleep(5)

        control = ReadAirConditionStatusData(self._device_address)
        control._ac_number = self.ac_number
        await self._buspro.send_telegram(control)

    @property
    def is_on(self):
        return False if self._status == OnOffStatus.OFF.value else True

    @property
    def unit_of_measurement(self):
        return TemperatureType.value_of(self._temperature_type)

    @property
    def mode(self):
        return AirConditionMode.value_of(self._mode)

    @property
    def fan_mode(self):
        return FanMode.value_of(self._fan)

    @property
    def current_temperature(self):
        return self._current_temperature

    @property
    def target_temperature(self):
        if self.mode == AirConditionMode.Cool:
            return self._cool_temperature
        elif self.mode == AirConditionMode.Heat:
            return self._heat_temperature
        elif self.mode == AirConditionMode.Auto:
            return self._auto_temperature
        elif self.mode == AirConditionMode.Dry:
            return self._dry_temperature
        else: # 还有一个fan模式
            return self._auto_temperature # 从测试看这几个模式下的温度是一样的，所以随便取一个

    async def async_turn_on(self):
        control = ControlAirConditionData(self._device_address)
        control._status = OnOffStatus.ON.value
        await self.control_status(control)
    
    async def async_turn_off(self):
        control = ControlAirConditionData(self._device_address)
        control._status = OnOffStatus.OFF.value
        await self.control_status(control)
    
    async def async_set_mode(self, mode:AirConditionMode):
        logger.debug(f"Try to set AC mode: {mode}")
        control = ControlAirConditionData(self._device_address)
        control._mode = mode.value
        control._status = OnOffStatus.ON
        await self.control_status(control)
    
    async def async_set_target_temperature(self, temperature):
        control = ControlAirConditionData(self._device_address)
        if self.mode == AirConditionMode.Cool:
            control._cool_temperature = temperature
        elif self.mode == AirConditionMode.Heat:
            control._heat_temperature = temperature
        elif self.mode == AirConditionMode.Auto:
            control._auto_temperature = temperature
        elif self.mode == AirConditionMode.Dry:
            control._dry_temperature = temperature
        else: # 还有一个fan模式
            control._auto_temperature = temperature # 随便取一个

        await self.control_status(control)
    
    async def async_set_fan_mode(self, fan_mode:FanMode):
        control = ControlAirConditionData(self._device_address)
        control._fan = fan_mode.value
        await self.control_status(control)
