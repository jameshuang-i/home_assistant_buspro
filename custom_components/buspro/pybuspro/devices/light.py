import logging

import asyncio
from ..telegram import Telegram, SingleChannelControlData, SingleChannelControlResponseData, ReadStatusOfChannelsData, ReadStatusOfChannelsResponseData, SceneControlResponseData
from .device import Device
from ..enums import SuccessOrFailure

logger = logging.getLogger(__name__)

class Light(Device):
    def __init__(self, buspro, device_address, channel_number, is_dimmable=False, running_time=0):
        super().__init__(buspro, device_address)
        self._channel = channel_number
        self._is_dimmable=is_dimmable
        self._brightness = 0
        self._previous_brightness = 100
        
        if is_dimmable:
            self._running_time_mins, self._running_time_secs = divmod(running_time, 60) 
        else:
            self._running_time_mins, self._running_time_secs = 0, 0

        self.register_telegram_received_cb(self._telegram_received_cb)
        self.call_read_current_status_of_channels(run_from_init=True)

    def _telegram_received_cb(self, telegram:Telegram, postfix=None):
        logger.debug(f"Light Device received: {telegram}")
        if isinstance(telegram, SingleChannelControlResponseData):
            if self._channel == telegram._channel_number and telegram._success == SuccessOrFailure.Success.value:
                self._brightness = telegram._channel_status
                self._set_previous_brightness(self._brightness)
                self.call_device_updated()
        elif isinstance(telegram, ReadStatusOfChannelsResponseData):
            if self._channel <= telegram._channel_count:
                self._brightness = telegram.get_status(self._channel)
                self._set_previous_brightness(self._brightness)
                self.call_device_updated()
        elif isinstance(telegram, SceneControlResponseData):
            self.call_read_current_status_of_channels()
        else:
            logger.debug(f"Light device discard the telegram: {telegram}")
    
    def call_read_current_status_of_channels(self, run_from_init=False):     
        asyncio.ensure_future(self._read_current_state_of_channels(run_from_init), loop=self._buspro.loop)

    async def _read_current_state_of_channels(self, run_from_init):
        if run_from_init:
            await asyncio.sleep(3)
        control = ReadStatusOfChannelsData(self._device_address)
        await self._buspro.send_telegram(control)

    async def set_on(self):
        await self._set(100)

    async def set_off(self):
        await self._set(0)

    async def set_brightness(self, intensity):
        await self._set(intensity)

    async def read_status(self):
        raise NotImplementedError

    @property
    def supports_brightness(self):
        return self._is_dimmable

    @property
    def previous_brightness(self):
        return self._previous_brightness

    @property
    def current_brightness(self):
        return self._brightness

    @property
    def is_on(self):
        return True if self._brightness else False

    async def _set(self, intensity):
        self._brightness = intensity
        self._set_previous_brightness(self._brightness)

        control = SingleChannelControlData(self._device_address)
        control._channel_number = self._channel
        control._channel_status = intensity
        control._running_time_minutes = self._running_time_mins
        control._running_time_seconds = self._running_time_secs
        await self._buspro.send_telegram(control)
        
    def _set_previous_brightness(self, brightness):
        if self.supports_brightness and brightness > 0:
            self._previous_brightness = brightness
