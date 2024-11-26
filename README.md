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
            

币安websocket每24小时会断开，需要重新连接，这个问题还没有很好的解决
现在可以错开时间启动两个及以上server实例，通过冗余来解决此问题

