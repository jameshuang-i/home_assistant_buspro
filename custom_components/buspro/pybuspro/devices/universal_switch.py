import asyncio

from ..telegram import Telegram, UniversalSwitchControlData, UniversalSwitchControlResponseData, ReadStatusOfUniversalSwitchData, ReadStatusOfUniversalSwitchResponseData
from .device import Device
from ..enums import OnOff, SwitchStatusOnOff


class UniversalSwitch(Device):
    def __init__(self, buspro, device_address, switch_number):
        super().__init__(buspro, device_address)

        self._switch_number = switch_number
        self._switch_status = OnOff.OFF

        self.register_telegram_received_cb(self._telegram_received_cb)
        self.call_read_current_status_of_universal_switch(run_from_init=True)

    def _telegram_received_cb(self, telegram, postfix=None):
        if isinstance(telegram, (UniversalSwitchControlResponseData, ReadStatusOfUniversalSwitchResponseData)):
            if self._switch_number == telegram._switch_number:
                self._switch_status = telegram._switch_status
                self.call_device_updated()

    async def set_on(self):
        await self._set(OnOff.ON)

    async def set_off(self):
        await self._set(OnOff.OFF)

    async def read_status(self):
        raise NotImplementedError

    @property
    def is_on(self):
        return False if self._switch_status == OnOff.OFF else True

    async def _set(self, switch_status):
        self._switch_status = switch_status

        control = UniversalSwitchControlData(self._device_address)
        control._switch_number = self._switch_number
        control._switch_status = self._switch_status

        await self._buspro.send_telegram(control)

    def call_read_current_status_of_universal_switch(self, run_from_init=False):
        asyncio.ensure_future(self._read_current_state_of_universal_switch(run_from_init), loop=self._buspro.loop)
    
    async def _read_current_state_of_universal_switch(self, run_from_init):
        if run_from_init:
            await asyncio.sleep(1)

        control = ReadStatusOfUniversalSwitchData(self._device_address)
        control._switch_number = self._switch_number
        await self._buspro.send_telegram(control)
