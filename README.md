# pybnk
binance kline kit in python

diy klines server:
    - wssv.py 
        example:
            server = AggTradesKlineServer(4532, SymbolType.SPOT, "BTCUSDT", 1)
            server.start_forever()
        
client test:
    - wssv.py
        example:
            asyncio.run(wssv.test_client(4532))

