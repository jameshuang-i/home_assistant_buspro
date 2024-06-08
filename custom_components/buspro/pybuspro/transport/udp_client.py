import asyncio
import socket
import logging

logger = logging.getLogger("buspro.udp_client")

class UDPProtocol(asyncio.DatagramProtocol):
    def __init__(self, data_received_callback=None):
        self.transport = None
        self._callback = data_received_callback

    def connection_made(self, transport):
        self.transport = transport

    def datagram_received(self, data, address):
        if self._callback:
            self._callback(data, address)

    def error_received(self, exc):
        logger.warning(f'Error received: {exc}')

    def connection_lost(self, exc):
        logger.info(f'closing transport {exc}')

class UDPClient:
    def __init__(self, gateway_address, local_address, data_received_callback, loop):
        self._gateway_address = gateway_address
        self._local_address = local_address
        self._data_received_callback = data_received_callback
        self._loop = loop or asyncio.get_event_loop()
        self._transport = None

    async def _connect(self):
        try:
            protol = UDPProtocol(self._data_received_callback)
            # Create multicast socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            if sock is None:
                logger.error("Create multicast socket failed!")
                return 

            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)            
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_LOOP, 0)
            sock.setblocking(False)
            sock.bind(self._local_address)

            (transport, _) = await self._loop.create_datagram_endpoint(lambda: protol, sock=sock)

            self._transport = transport
        except Exception as ex:
            logger.error(f"Could not create UDP endpoint to {self._gateway_address}: {ex}")

    async def start(self):
        await self._connect()

    async def stop(self):
        if self._transport:
            self._transport.close()
            self._transport = None

    async def send_message(self, message):
        if self._transport:
            logger.debug(f"Try to send busp message:\n{message}")
            self._transport.sendto(message, self._gateway_address)
        else:
            logger.warn("Could not send message. Transport is None.")
