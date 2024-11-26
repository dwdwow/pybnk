import asyncio
import websockets
import websockets.asyncio
import websockets.asyncio.server


class AggTradesKlineServer:

    def __init__(self, port: int):
        self.port = port
        self.clients = set()

    async def handler(self, ws: websockets.asyncio.server.ServerConnection):
        self.clients.add(ws)
        try:
            await ws.wait_closed()
        finally:
            self.clients.remove(ws)


async def wssvhandler(ws: websockets.asyncio.server.ServerConnection):
    async for msg in ws:
        print(msg)
        await ws.send("pong")


async def start_server():
    async with websockets.serve(wssvhandler, "localhost", 4532):
        await asyncio.Future()  # run forever
        

async def test():
    async with websockets.connect("ws://localhost:4532") as ws:
        await ws.send("ping")
        print(await ws.recv())


if __name__ == "__main__":
    asyncio.run(start_server())
