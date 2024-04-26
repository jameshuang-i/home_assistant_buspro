import asyncio
import logging
from ..telegram import Telegram, ControlAirConditionResponseData, ReadAirConditionStatusData, ReadAirConditionStatusResponseData, ControlDLPStatusData, ControlDLPStatusResponseData
from .device import Device
from ..helpers import copy_class_attrs
from ..enums import AirConditionMode, FanMode, OnOffStatus, TemperatureType, DLPOperateCode

logger = logging.getLogger(__name__)

class AirCondition(Device):
    def __init__(self, buspro, device_address, ac_number):
        super().__init__(buspro, device_address)
        self.ac_number = ac_number
        self._temperature_type = 0 # 0-C, 1-F
        self._current_temperature = None
        self._cool_temperature = None
        self._heat_temperature = None
        self._auto_temperature = None
        self._dry_temperature = None
        self._status = 0 # 0-OFF, 1-ON
        self._mode = 3 # 0-COOL, 1-Heat, 2-FAN, 3-Auto, 4-Dry
        self._fan = 0 # 0-Auto, 1-High, 2-Medium, 3-Low

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
        elif isinstance(telegram, ControlDLPStatusResponseData):
            if telegram._number == self.ac_number:
                self._update(telegram._dlp_operate_code, telegram._data)
                self.call_device_updated()
        else:
            logger.debug(f"Not supported message for operate type {telegram}")
    
    def _update(op_code, data):
        operate = DLPOperateCode.value_of(op_code)
        if operate == DLPOperateCode.ar_status:
            self._status = data
        elif operate == DLPOperateCode.ar_fan_speed:
            self._fan = data
        elif operate == DLPOperateCode.ar_mode:
            self._mode = data
        elif operate == DLPOperateCode.ar_temperature_auto:
            self._auto_temperature = data
        elif operate == DLPOperateCode.ar_temperature_cool:
            self._cool_temperature = data
        elif operate == DLPOperateCode.ar_temperature_dry:
            self._dry_temperature = data
        elif operate == DLPOperateCode.ar_temperature_heat:
            self._heat_temperature = data
        else:
            logger.debug(f"Not supported DLP operate type {op_code}")

    async def async_control_dlp(self, operate, data):
        control = ControlDLPStatusData(self._device_address)
        control._dlp_operate_code = operate.value
        control._data = data
        control._number = self.ac_number
        await self._buspro.send_telegram(control)

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
        await self.async_control_dlp(DLPOperateCode.ar_status, OnOffStatus.ON.value)
    
    async def async_turn_off(self):
        await self.async_control_dlp(DLPOperateCode.ar_status, OnOffStatus.OFF.value)
    
    async def async_set_mode(self, mode:AirConditionMode):
        logger.debug(f"Try to set AC mode: {mode}")
        if not self.is_on:
            await self.async_control_dlp(DLPOperateCode.ar_status, OnOffStatus.ON.value)
        await self.async_control_dlp(DLPOperateCode.ar_mode, mode.value)
    
    async def async_set_target_temperature(self, temperature):        
        if self.mode == AirConditionMode.Cool:
            operate = DLPOperateCode.ar_temperature_cool
        elif self.mode == AirConditionMode.Heat:
            operate = DLPOperateCode.ar_temperature_heat
        elif self.mode == AirConditionMode.Auto:
            operate = DLPOperateCode.ar_temperature_auto
        elif self.mode == AirConditionMode.Dry:
            operate = DLPOperateCode.ar_temperature_dry
        else: # 还有一个fan模式
            logger.error(f"The air condition mode {self.mode} is not support for set target temperature!")
            return
     
        await self.async_control_dlp(operate, temperature)
    
    async def async_set_fan_mode(self, fan_mode:FanMode):
        if not self.is_on:
            await self.async_control_dlp(DLPOperateCode.ar_status, OnOffStatus.ON.value)
        await self.async_control_dlp(DLPOperateCode.ar_fan_speed, fan_mode.value)
