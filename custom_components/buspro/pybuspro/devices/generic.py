import asyncio
from .device import Device
from ..telegram import Telegram


class Generic(Device):
    def __init__(self, buspro, device_address, payload, operate_code):
        super().__init__(buspro, device_address)
        self._payload = payload
        self._operate_code = operate_code

    async def run(self):
        control = Telegram(self._device_address)
        control.operate_code = self._operate_code
        control.payload = self._payload
        await self._buspro.send_telegram(control)
