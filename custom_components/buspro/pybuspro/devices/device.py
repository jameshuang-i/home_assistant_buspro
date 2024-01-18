import asyncio


class Device(object):
    def __init__(self, buspro, device_address):
        self._device_address = device_address
        self._buspro = buspro
        self._device_updated_cbs = []
    
    @property
    def is_connected(self):
        return self._buspro.connected

    def register_telegram_received_cb(self, telegram_received_cb, postfix=None):
        self._buspro.register_telegram_received_device_cb(telegram_received_cb, self._device_address, postfix)

    def unregister_telegram_received_cb(self, telegram_received_cb, postfix=None):
        self._buspro.unregister_telegram_received_device_cb(telegram_received_cb, self._device_address, postfix)

    def register_device_updated_cb(self, device_updated_cb):
        """Register device updated callback."""
        self._device_updated_cbs.append(device_updated_cb)

    def unregister_device_updated_cb(self, device_updated_cb):
        """Unregister device updated callback."""
        self._device_updated_cbs.remove(device_updated_cb)

    def call_device_updated(self):
        asyncio.ensure_future(self._device_updated(), loop=self._buspro.loop)
    
    async def _device_updated(self):
        for device_updated_cb in self._device_updated_cbs:
            await device_updated_cb(self)

