import asyncio
import json
import logging
import websockets
import websockets.asyncio
import websockets.asyncio.server

from enums import SymbolType

logging.basicConfig(level=logging.INFO)

class AggTradesKlineServer:

    def __init__(self, port: int, symbol_type: SymbolType, symbol: str, interval_seconds: int):
        
        if 24 * 60 * 60 % interval_seconds != 0:
            raise ValueError("interval_seconds must be a divisor of 24 * 60 * 60")

        self.port = port
        self.symbol_type = symbol_type
        self.symbol = symbol
        self.interval_ms = interval_seconds * 1000
        self.clients = set()
        self.open_time = 0
        self.trades = []
        self._logger = logging.getLogger("AggTradesKlineServer")
        
    async def _start_bnc_ws_clt(self):
        url = ""
        match self.symbol_type:
            case SymbolType.SPOT:
                url = f"wss://stream.binance.com:9443/ws/{self.symbol.lower()}@aggTrade"
            case SymbolType.FUTURES_UM:
                url = f"wss://fstream.binance.com/ws/{self.symbol.lower()}@aggTrade"
            case SymbolType.FUTURES_CM:
                url = f"wss://fstream.binance.com/ws/{self.symbol.lower()}@aggTrade"
        if not url:
            raise ValueError(f"Invalid symbol type: {self.symbol_type}")

        while True:
            self._logger.info(f"connecting to {url}")
            async with websockets.connect(url) as ws:
                self._logger.info(f"connected to {url}")
                while True:
                    try:
                        msg = await ws.recv()
                        await self._bnc_ws_clt_msg_handler(msg)
                    except websockets.ConnectionClosed:
                        self._logger.error(f"binance websocket connection closed, reconnecting...")
                        break
                
    async def _broadcast_kline(self, kline: dict):
        if not self.clients:
            return
        if kline["openTime"] == 0:
            return
        for client in self.clients:
            try:
                await client.send(json.dumps(kline))
            except websockets.ConnectionClosed:
                self.clients.remove(client)
                self._logger.info(f"client disconnected, clients number: {len(self.clients)}")
                
    async def _bnc_ws_clt_msg_handler(self, msg):
        try:
            msg_json = json.loads(msg)
        except json.JSONDecodeError as e:
            self._logger.error(f"JSONDecodeError: {e} message: {msg}")
            return
        event_type = msg_json.get("e")
        if event_type != "aggTrade":
            self._logger.info(f"event_type: {event_type} message: {msg_json}")
            return
        ts = msg_json.get("T")
        if not ts:
            self._logger.error(f"ts is None message: {msg_json}")
            return
        price = float(msg_json.get("p"))
        if not price:
            self._logger.error(f"price is None message: {msg_json}")
            return
        qty = float(msg_json.get("q"))
        if not qty:
            self._logger.error(f"qty is None message: {msg_json}")
            return
        is_buyer_maker = msg_json.get("m")
        if is_buyer_maker is None:
            self._logger.error(f"is_buyer_maker is None message: {msg_json}")
            return
        kline_open_time = ts // self.interval_ms * self.interval_ms
        if kline_open_time == self.open_time:
            self.trades.append(msg_json)
            return
        if self.trades:      
            self.trades.sort(key=lambda x: x.get("f"))
            kline = {
                "openTime": self.open_time,
                "openPrice": float(self.trades[0]["p"]),
                "highPrice": max(float(trade["p"]) for trade in self.trades),
                "lowPrice": min(float(trade["p"]) for trade in self.trades),
                "closePrice": float(self.trades[-1]["p"]),
                "volume": sum(float(trade["q"]) for trade in self.trades),
                "closeTime": self.open_time + self.interval_ms - 1,
                "quoteAssetVolume": sum(float(trade["q"]) * float(trade["p"]) for trade in self.trades),
                "tradesNumber": len(self.trades),
                "takerBuyBaseAssetVolume": sum(float(trade["q"]) for trade in self.trades if not trade["m"]),
                "takerBuyQuoteAssetVolume": sum(float(trade["q"]) * float(trade["p"]) for trade in self.trades if not trade["m"]),
                "unused": 0
                }
            await self._broadcast_kline(kline)
        self.open_time = kline_open_time
        self.trades = [msg_json]
            
    async def _ws_sv_handler(self, ws):
        self._logger.info(f"new client connected")
        self.clients.add(ws)
        self._logger.info(f"clients number: {len(self.clients)}")
        try:
            async for msg in ws:
                self._logger.info(f"msg: {msg}")
        finally:
            self.clients.remove(ws)
            self._logger.info(f"client disconnected, clients number: {len(self.clients)}")
            
    async def _start_sv(self):
        async with websockets.serve(self._ws_sv_handler, "localhost", self.port):
            await asyncio.Future()
            
    async def _start(self):
        await asyncio.gather(self._start_bnc_ws_clt(), self._start_sv())
                
    def start_forever(self):
        asyncio.run(self._start())


async def test_client(port: int):
    async with websockets.connect(f"ws://localhost:{port}") as ws:
        while True:
            msg = await ws.recv()
            print(msg)
            

if __name__ == "__main__":
    server = AggTradesKlineServer(4532, SymbolType.SPOT, "BTCUSDT", 1)
    server.start_forever()
