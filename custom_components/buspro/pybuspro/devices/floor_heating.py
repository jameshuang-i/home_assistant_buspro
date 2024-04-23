import asyncio
import logging
from ..telegram import Telegram, ReadDLPStatusData, ReadDLPStatusResponseData, ControlDLPStatusData, ControlDLPStatusResponseData
from .device import Device
from ..enums import AirConditionMode, OnOffStatus, PresetMode, DLPOperateCode, TemperatureType

logger = logging.getLogger(__name__)

class FloorHeating(Device):
    def __init__(self, buspro, device_address, number):
        super().__init__(buspro, device_address)
        self._number = number
        self._status = None             # On/Off
        self._mode = None               # 1/2/3/4/5 (Normal/Day/Night/Away/Timer)
        self._temperature = 0           # 默认 0
        self._temperature_normal = None
        self._temperature_day = None
        self._temperature_night = None
        self._temperature_away = None

        self.register_telegram_received_cb(self._telegram_received_cb)
        self.call_read_current_heating_status(run_from_init=True)

    def _telegram_received_cb(self, telegram, postfix=None):
        if isinstance(telegram, (ReadDLPStatusResponseData, ControlDLPStatusResponseData)):
            self._update(telegram._dlp_operate_code, telegram._data, telegram._number)
            self.call_device_updated()
        else:
            logger.debug(f"Not supported message for operate type {telegram}")

    def _update(self, op_code, data, number):
        if number == self._number:
            operate = DLPOperateCode.value_of(op_code)
            if operate == DLPOperateCode.status:
                self._status = data
            elif operate == DLPOperateCode.mode:
                self._mode = data
            elif operate == DLPOperateCode.lock:
                pass
            elif operate == DLPOperateCode.temperature_normal:
                self._temperature_normal = data
            elif operate == DLPOperateCode.temperature_day:
                self._temperature_day = data
            elif operate == DLPOperateCode.temperature_night:
                self._temperature_night = data
            elif operate == DLPOperateCode.temperature_away:
                self._temperature_away = data
            else:
                logger.debug(f"Not supported DLP operate type {op_code}")

    async def async_read_floor_heating(self, operate):
        control = ReadDLPStatusData(self._device_address)
        control._dlp_operate_code = operate.value
        control._data = self._number
        control._number = self._number
        await self._buspro.send_telegram(control)

    async def async_control_floor_heating(self, operate, data):
        control = ControlDLPStatusData(self._device_address)
        control._dlp_operate_code = operate.value
        control._data = data
        control._number = self._number
        await self._buspro.send_telegram(control)

    def call_read_current_heating_status(self, run_from_init=False):      
        asyncio.ensure_future(self._read_current_heating_status(run_from_init), loop=self._buspro.loop)
    
    async def _read_current_heating_status(self, run_from_init=False):
        if run_from_init:
            await asyncio.sleep(5)

        await self.async_read_floor_heating(DLPOperateCode.status)
        await self.async_read_floor_heating(DLPOperateCode.mode)
        await self.async_read_floor_heating(DLPOperateCode.temperature_normal)
        await self.async_read_floor_heating(DLPOperateCode.temperature_day)
        await self.async_read_floor_heating(DLPOperateCode.temperature_night)
        await self.async_read_floor_heating(DLPOperateCode.temperature_away)

    async def async_turn_off(self):
        await self.async_control_floor_heating(DLPOperateCode.status, OnOffStatus.OFF.value)

    async def async_turn_on(self):
        await self.async_control_floor_heating(DLPOperateCode.status, OnOffStatus.ON.value)
    
    async def async_set_preset_mode(self, mode:PresetMode):
        await self.async_control_floor_heating(DLPOperateCode.mode, mode.value)
    
    async def async_set_target_temperature(self, temperature):
        operate = DLPOperateCode.temperature_normal
        if self.preset_mode == PresetMode.home:
            operate = DLPOperateCode.temperature_day
        elif self.preset_mode == PresetMode.away:
            operate = DLPOperateCode.temperature_away
        elif self.preset_mode == PresetMode.sleep:
             operate = DLPOperateCode.temperature_night
      
        await self.async_control_floor_heating(operate, temperature)
    
    async def async_set_mode(self, mode:AirConditionMode):
        await self.async_turn_on()  # 直接打开地暖

    @property
    def is_on(self):
        return False if self._status == OnOffStatus.OFF.value else True

    @property
    def unit_of_measurement(self):
        return TemperatureType.Celsius

    @property
    def preset_mode(self):
        mode = PresetMode.value_of(self._mode)
        # HDL 中还有一个Timer的模式
        return mode if mode else PresetMode.normal

    @property
    def mode(self):
        """工作模式, 只有heating"""
        return AirConditionMode.Heat

    @property
    def current_temperature(self):
        return self._temperature

    @property
    def target_temperature(self):
        if self.preset_mode == PresetMode.home:
            return self._temperature_day
        elif self.preset_mode == PresetMode.away:
            return self._temperature_away
        elif self.preset_mode == PresetMode.sleep:
            return self._temperature_night
        else:
            return self._temperature_normal