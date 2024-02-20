import asyncio
import logging
from ..telegram import *
from .device import Device
from ..helpers import copy_class_attrs

logger = logging.getLogger("buspro.devices.sensor")

class Sensor(Device):
    def __init__(self, buspro, device_address, universal_switch_number=None, channel_number=None, device=None, switch_number=None):
        super().__init__(buspro, device_address)
        self._universal_switch_number = universal_switch_number
        self._channel_number = channel_number
        self._device = device
        self._switch_number = switch_number
        
        self._current_temperature = None
        self._brightness = None
        self._motion_sensor = None
        self._sonic = None
        self._dry_contact_1_status = None
        self._dry_contact_2_status = None
        self._universal_switch_status = OnOffStatus.OFF
        self._channel_status = 0
        self._switch_status = 0

        self.register_telegram_received_cb(self._telegram_received_cb)
        self.call_read_current_status_of_sensor(run_from_init=True)

    def _telegram_received_cb(self, telegram):
        if isinstance(telegram, ReadSensorStatusResponseData):
            copy_class_attrs(telegram, self)
            if telegram._success == SuccessOrFailure.Success:
                self._brightness = telegram._brightness_high + telegram._brightness_low
                self.call_device_updated()
        elif isinstance(telegram, ReadSensorsInOneStatusResponseData):
            copy_class_attrs(telegram, self)
            self.call_device_updated()
        elif isinstance(telegram, BroadcastSensorStatusResponseData):
            copy_class_attrs(telegram, self)
            self.call_device_updated()
        elif isinstance(telegram, BroadcastSensorStatusAutoResponseData):
            copy_class_attrs(telegram, self)
            self._current_temperature = telegram._current_temperature if self._device == "12in1" else telegram._current_temperature - 20
            self._brightness = telegram._brightness_high + telegram._brightness_low
            self.call_device_updated()
        elif isinstance(telegram, ReadFloorHeatingStatusResponseData):
            self._current_temperature = telegram._current_temperature
            self.call_device_updated()
        elif isinstance(telegram, BroadcastTemperatureResponseData):
            self._current_temperature = telegram._current_temperature
            self.call_device_updated()
        elif isinstance(telegram, ReadStatusOfUniversalSwitchResponseData):
            if self._universal_switch_number == telegram._switch_number:
                self._universal_switch_status = telegram._switch_status
                self.call_device_updated()
        elif isinstance(telegram, BroadcastStatusOfUniversalSwitchData):
            if self._universal_switch_number and self._universal_switch_number <= telegram._switch_count:
                self._universal_switch_status = telegram.get_switch_status(self._universal_switch_number)
                self.call_device_updated()
        elif isinstance(telegram, UniversalSwitchControlResponseData):
            if self._universal_switch_number == telegram._switch_number:
                self._universal_switch_status = telegram._switch_status
                self.call_device_updated()
        elif isinstance(telegram, ReadStatusOfChannelsResponseData):
            if self._channel_number and self._channel_number <= telegram._channel_count:
                self._channel_status = telegram.get_status(self._channel_number)
                self.call_device_updated()
        elif isinstance(telegram, SingleChannelControlResponseData):
            if self._channel_number == telegram._channel_number:
                self._channel_status = telegram._channel_status
                self.call_device_updated()
        elif isinstance(telegram, ReadDryContactStatusResponseData):
            if self._switch_number == telegram._switch_number:
                self._switch_status = telegram._switch_status
                self.call_device_updated()
        else:
            logger.debug(f"Sensor device discard the telegram: {telegram}")

    async def read_sensor_status(self):
        if self._universal_switch_number:
            control = ReadStatusOfUniversalSwitchData(self._device_address)
            control._switch_number = self._universal_switch_number            
        elif self._channel_number:
            control = ReadStatusOfChannelsData(self._device_address)
        elif self._device and self._device == "dlp":
            control = ReadFloorHeatingStatusData(self._device_address)
        elif self._device and self._device == "dry_contact":
            control = ReadDryContactStatusData(self._device_address)
            control._switch_number = self._switch_number
        elif self._device and self._device == "sensors_in_one":
            control = ReadSensorsInOneStatusData(self._device_address)
        else:
            control = ReadSensorStatusData(self._device_address)
        await self._buspro.send_telegram(control)

    @property
    def temperature(self):
        if self._current_temperature is None:
            return None
        if self._device and self._device in ("dlp", "12in1"):
            return self._current_temperature
        return self._current_temperature - 20

    @property
    def brightness(self):
        return self._brightness

    @property
    def movement(self):
        if self._motion_sensor == 1 or self._sonic == 1:
            return True
        else:
            return False

    @property
    def dry_contact_1_is_on(self):
        return True if self._dry_contact_1_status == 1 else False

    @property
    def dry_contact_2_is_on(self):
        return True if self._dry_contact_2_status == 1 else False

    @property
    def universal_switch_is_on(self):
        return True if self._universal_switch_status == 1 else False

    @property
    def single_channel_is_on(self):
        return True if self._channel_status else False

    @property
    def switch_status(self):
        return True if self._switch_status==1 else False

    def call_read_current_status_of_sensor(self, run_from_init=False):
        asyncio.ensure_future(self._read_current_status_of_sensor(run_from_init), loop=self._buspro.loop)
    
    async def _read_current_status_of_sensor(self, run_form_init):
        if run_from_init:
            await asyncio.sleep(5)
        await self.read_sensor_status()
