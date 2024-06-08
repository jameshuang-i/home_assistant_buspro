''' pybuspro version 1.0.0  '''

import asyncio
import logging

from .enums import *
from .transport.network_interface import NetworkInterface


logger = logging.getLogger("buspro.log")

class StateUpdater:
    def __init__(self, buspro, sleep=10):
        self.buspro = buspro
        self.run_forever = True
        self.run_task = None
        self.sleep = sleep

    async def start(self):
        self.run_task = self.buspro.loop.create_task(self.run())

    async def run(self):
        await asyncio.sleep(0)
        logger.info("Starting StateUpdater with {} seconds interval".format(self.sleep))

        while True:
            await asyncio.sleep(self.sleep)
            await self.buspro.sync()


class Buspro:
    def __init__(self, gateway_address, local_address, loop_=None):
        self.loop = loop_ or asyncio.get_event_loop()
        self._gateway_address = gateway_address
        self._local_address = local_address

        self._state_updater = None
        self._started = False
        self._net = None
        self._all_received_telegram_callback = None
        self._device_received_telegram_callbacks = []        

    def __del__(self):
        if self._started:
            try:
                task = self.loop.create_task(self.stop())
                self.loop.run_until_complete(task)
            except RuntimeError as exp:
                logger.warning("Could not close loop, reason: {}".format(exp))

    # noinspection PyUnusedLocal
    async def start(self, state_updater=False):  # , daemon_mode=False):
        self._net = NetworkInterface(self._gateway_address, self._local_address, self._handle_received_telegram, self.loop)
        await self._net.start()

        if state_updater:
            self._state_updater = StateUpdater(self)
            await self._state_updater.start()

        '''
        if daemon_mode:
            await self._loop_until_sigint()
        '''
        self._started = True

    async def stop(self):
        if self._net:
            await self._net.stop()
            self._net = None
        self._started = False
    
    async def send_telegram(self, telegram):
        if self._net:
            await self._net.send_telegram(telegram)
        else:
            logger.error("Send telegram failed as buspro not connected!")

    def _handle_received_telegram(self, telegram):
        telegram_control = telegram.toControl()

        if self._all_received_telegram_callback:
            self._all_received_telegram_callback(telegram_control)

        for telegram_received_cb in self._device_received_telegram_callbacks:
            device_address = telegram_received_cb['device_address']

            # Sender callback kun for oppgitt kanal
            if device_address == telegram_control.target_address or device_address == telegram_control.source_address:               
                if telegram_control.operate_code is not OperateCode.TIME_IF_FROM_LOGIC_OR_SECURITY:
                    logger.debug(f"Send to device {device_address}")
                    postfix = telegram_received_cb['postfix']
                    telegram_received_cb['callback'](telegram_control, postfix)

    def register_telegram_received_all_messages_cb(self, telegram_received_cb):
        self._all_received_telegram_callback = telegram_received_cb

    def register_telegram_received_device_cb(self, telegram_received_cb, device_address, postfix=None):
        self._device_received_telegram_callbacks.append({
            'callback': telegram_received_cb,
            'device_address': device_address,
            'postfix': postfix})

    def unregister_telegram_received_device_cb(self, telegram_received_cb, device_address, postfix=None):
        self._device_received_telegram_callbacks.remove({
            'callback': telegram_received_cb,
            'device_address': device_address,
            'postfix': postfix})

    @staticmethod
    async def sync():
        # await self.callback("LOG: Sync() triggered from StateUpdater")
        # print("LOG: Sync() triggered from StateUpdater")
        raise NotImplementedError

    @property
    def connected(self):
        return self._started
