import logging
import traceback
from struct import *

from .udp_client import UDPClient
from ..telegram import Telegram
from ..enums import DeviceType, OperateCode

logger = logging.getLogger(__name__)

class NetworkInterface:
    def __init__(self, gateway_address, local_address, telegram_received_callback, loop=None, protocol="UDP"):
        self._gateway_address = gateway_address
        self._local_address = local_address
        self._telegram_received_callback = telegram_received_callback
        self._loop = loop

        if protocol=="UDP":
            self._client = UDPClient(self._gateway_address, self._local_address, self._handle_received_data, self._loop)
        else:
            logger.erro(f"Unsupported the network protocol: {protocol}")
            raise NotImplemented(f"Not Implemented {protocol} protocol")

    def _handle_received_data(self, data, address):
        if self._telegram_received_callback:
            telegram = self._build_telegram_data(data, address)
            if telegram: 
                self._telegram_received_callback(telegram)

    """
    public methods
    """
    def register_callback(self, telegram_received_callback):
        self._telegram_received_callback = _telegram_received_callback

    async def start(self):
        await self._client.start()

    async def stop(self):
        if self._client:
            await self._client.stop()
            self._client = None

    async def send_telegram(self, telegram):

        def _print_message(m):
            return ' '.join([format(x, '02x') for x in m])

        logger.debug(f"Send Telegram: {telegram}")
        message = self._build_send_buffer(telegram)
        logger.debug(f"Send Message: {_print_message(message)}")
        if message and self._client:
            await self._client.send_message(message)
        else:
            logger.error("Send telegram failed as message build failed or client not started!")
    
    def _build_telegram_data(self, data, address=None):

        def _print_bytes(datas):
            return ' '.join([format(x, '02x') for x in datas])

        logger.debug(f"RECEIVED DATA: {_print_bytes(data)}")
        if not data or len(data) <= 27:
            # logger.debug("The received data is none or less then 27, abort!")
            return None

        try:
            # index = 14 # 从16开始算
            # 验证消息头
            if data[14: 16 ] != b'\xAA\xAA':
                # logger.debug("The telegarm check failed!")
                return None
            # index += 2 # 16
            length_package = data[16]
            # 校验长度
            if length_package + 16 != len(data):
                logger.debug(f"The data length {len(data)} not match the package length {length_package}")
                return None
            # CRC校验
            crc = data[-2:]
            crc_bufer = data[16:-2]
            crc_computed = pack(">H", self._crc16(crc_bufer))
            if crc_computed != crc:
                logger.debug('CRC check failed!')
                return None

            # 获取各字段
            # index += 1 # 17
            telegram = Telegram()      
            telegram.source_address = (data[17], data[18]) 
            telegram.source_device_type = DeviceType.value_of(data[19: 21])
            telegram.operate_code = OperateCode.value_of(data[21: 23])
            telegram.target_address = (data[23], data[24])
            telegram.payload = list(data[25:-2])
            telegram.crc = crc
            # telegram.udp_address = address
            
            logger.debug(f"RECEIVED TELEGRAM: Source={telegram.source_address}, Target={telegram.target_address}, Operate={telegram.operate_code}, type={telegram.source_device_type}")
            return telegram
            
        except Exception as e:
            logger.error("Error building telegram: {}".format(traceback.format_exc()))
            return None
    
    def _build_send_buffer(self, telegram: Telegram):
        if telegram is None:
            return None

        # if telegram.payload is None:
        #     telegram.payload = []

        # 消息头
        send_buf = bytearray([192, 168, 0, 200])
        send_buf.extend('HDLMIRACLE'.encode())
        send_buf.append(0xAA)
        send_buf.append(0xAA)
        # 长度
        length_of_data_package = 11 + len(telegram.payload)
        send_buf.append(length_of_data_package)
        # 源地址
        if telegram.source_address:
            send_buf.extend(telegram.source_address)
        else:
            send_buf.extend((200,200))
        # 设备类型
        if telegram.source_device_type:
            send_buf.extend(telegram.source_device_type.value)
        else:
            send_buf.extend((0,0))
        # 操作码
        send_buf.extend(telegram.operate_code.value)
        # 目标地址
        send_buf.extend(telegram.target_address)
        # 消息内容
        send_buf.extend(telegram.payload)
        # CRC校验
        crc = self._crc16(bytes(send_buf[16:])) #从长度开始的内容
        crc0, crc1 = pack(">H", crc)
        send_buf.extend((crc0,crc1))

        return send_buf

    def _crc16(self, data: bytes):
        xor_in = 0x0000  # initial value
        xor_out = 0x0000  # final XOR value
        poly = 0x1021  # generator polinom (normal form)
    
        reg = xor_in
        for octet in data:
            # reflect in
            for i in range(8):
                topbit = reg & 0x8000
                if octet & (0x80 >> i):
                    topbit ^= 0x8000
                reg <<= 1
                if topbit:
                    reg ^= poly
            reg &= 0xFFFF
            # reflect out
        return reg ^ xor_out