from typing import List

import asyncio
from asyncio import StreamReader, StreamWriter


class AbbotBuilder:
    def __init__(self, host: str = "127.0.0.1", port: int = 8888, handlers: List[function] = []):
        self.host = host
        self.port = port
        self.handlers = handlers

    def set_host(self, host):
        self.host = host
        return self

    def set_port(self, port):
        self.port = port
        return self

    def add_handler(self, handler):
        self.handlers.append(handler)
        return self

    async def handle_client(self, reader: StreamReader, writer: StreamWriter):
        while True:
            data = await reader.read(100)
            if not data:
                break

            for handler in self.handlers:
                await handler(data, reader, writer)

    async def run(self):
        server = await asyncio.start_server(self.handle_client, self.host, self.port)
        addr = server.sockets[0].getsockname()
        print(f"Serving on {addr}")

        async with server:
            await server.serve_forever()


async def event_handler(data: bytes, reader: StreamReader, writer: StreamWriter):
    message = data.decode()
    addr = writer.get_extra_info("peername")
    print(f"Received {message!r} from {addr!r}")

    print(f"Sending: {message!r}")
    writer.write(data)
    await writer.drain()


app = AbbotBuilder().add_handler(event_handler)
asyncio.run(app.run())
