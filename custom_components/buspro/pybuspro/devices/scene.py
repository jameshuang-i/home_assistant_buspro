import asyncio
from .device import Device
from ..telegram import SceneControlData


class Scene(Device):
    def __init__(self, buspro, device_address, scene_address):
        super().__init__(buspro, device_address)
        self._area_number, self._scene_number = scene_address

    async def run(self):
        control = SceneControlData(self._device_address)
        control._area_number = self._area_number
        control._scene_number = self._scene_number
        await self._buspro.send_telegram(control)
