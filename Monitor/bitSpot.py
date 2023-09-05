import sys
sys.path.append('../..')
from wbfAPI.base import exceptions
from wbfAPI.base import wss
from wbfAPI.base import rest
from wbfAPI.base import transform
import threading
import json
import datetime
import urllib
from urllib.request import Request, urlopen
from hashlib import sha256
import hmac
import time
import numpy as np
import requests
import simplejson
import hashlib
import hmac
# import os
# os.environ['http_proxy'] = 'http://127.0.0.1:1080'
# os.environ['https_proxy'] = 'https://127.0.0.1:1080'


class _params():

    def __init__(self):
        """该类只放参数
        """
        self.exc = 'bitSpot'

        self.restUrl = 'https://betaapi.bitexch.dev'
        self.acctWssUrl = 'wss://betaws.bitexch.dev'
        self.wssUrl = 'wss://betaws.bitexch.dev'

        self.restUrl = 'https://spot-api.bit.com'
        self.acctWssUrl = 'wss://spot-ws.bit.com'
        self.wssUrl = 'wss://spot-ws.bit.com'
        self.umrestUrl = "https://api.bit.com"
        self.umwssUrl = ""

        self.restPaths = {
            'getAccount': 'GET /spot/v1/accounts',
            'getBalance': 'GET /spot/v1/accounts',
            'getPosition': 'GET /fapi/v2/positionRisk',
            'getFee': '',
            'getTick': 'GET /spot/v1/market/trades',
            'getDepth': 'GET /spot/v1/orderbooks',
            'getKline': 'GET /spot/v1/klines',
            'getFundingRate': 'GET /fapi/v1/premiumIndex',
            'getClearPrice': 'GET /fapi/v1/premiumIndex',
            'makeOrder': 'POST /spot/v1/orders',
            'makeOrders': 'POST /spot/v1/batchorders',
            'cancelOrder': 'POST /spot/v1/cancel_orders',
            'cancelAll': 'POST /spot/v1/cancel_orders',
            'queryOrder': 'GET /spot/v1/orders',
            'getOpenOrders': 'GET /spot/v1/open_orders',
            'getDeals': 'GET /spot/v1/user/trades',
            'getIncreDepth': 'GET /fapi/v1/depth',
            'getListenKey': 'GET /spot/v1/ws/auth',
            'refreshListenKey': 'PUT /fapi/v1/listenKey',
        }

        self.wssPaths = {
            'tick': {"type":"subscribe","pairs":["BTC-USDT"],"channels":["ticker"],"interval": "100ms"},
            'depth': {"type":"subscribe","pairs":["<symbol>"],"channels":["order_book.10.10"],"interval": "100ms"
            },
            #'increDepthFlow': {'params': ['<symbol>@depth@100ms'], 'method': 'SUBSCRIBE', 'id': 1},
            #'kline': {'params': ['<symbol>@kline_<period>'], 'method': 'SUBSCRIBE', 'id': 1},
            #'clearPrice': {'params': ['<symbol>@markPrice@1s'], 'method': 'SUBSCRIBE', 'id': 1},

            'orders': {"type":"subscribe","channels":["order"],"interval": "100ms","token":'<token>'},
            'deals': {"type":"subscribe","channels":["user_trade"],"interval": "100ms","token":'<token>'},
            'balance': {"type":"subscribe","channels":["account"],"interval": "100ms","token":'<token>'},
            'position': '',
        }

        self.klinePeriods = {
            '1m': '1m',
            '3m': '3m',
            '5m': '5m',
            '15m': '15m',
            '30m': '30m',
            '1h': '1h',
            '2h': '2h',
            '4h': '4h',
            '6h': '6h',
            '8h': '8h',
            '12h': '12h',
            '1d': '1d',
            '3d': '3d',
            '1w': '1w',
            '1M': '1M',
        }
        self.reverseKlinePeriods = {v: k for k, v in self.klinePeriods.items()}

        self.statusDict = {
            'pending': 'submit',
            'PARTIALLY_FILLED': 'partial-filled',
            #'filled': 'filled',
            'cancelled': 'cancel',
            # 'REJECTED': 'rejected',
            'EXPIRED': 'expired',
        }

        self.legalCurrency = [
            'USDT', 'USD', 'BTC', 'ETH',
        ]

    def getSymbol(self, symbol):
        return symbol.replace('/', '-').upper()

    def getSymbol_re(self, symbol):
        return symbol.replace( '-','/').lower()

    def accountWsSymbol(self, symbol):
        for lc in self.legalCurrency:
            if lc in symbol:
                symbol = f"{symbol.split(lc)[0]}/{lc}".lower()
        return symbol

    def getPeriod(self, key):
        return key

    def getRestPath(self, key):
        if key not in self.restPaths \
                or self.restPaths[key] == '':
            exceptions.raisePathError(self.exc, key)
        return self.restPaths[key]

    def getWssPath(self, **kwargs):
        """拿wss订阅字段

        Args:
            *args: topic/symbol/....

        Returns:
            TYPE: Description
        """
        key = kwargs['topic']
        if 'symbol' in kwargs:
            kwargs['symbol'] = self.getSymbol(kwargs['symbol'])
        if 'period' in kwargs:
            kwargs['period'] = self.getPeriod(kwargs['period'])

        if key not in self.wssPaths \
                or self.wssPaths[key] == '':
            exceptions.raisePathError(self.exc, key)
        req = self.wssPaths[key]
        keys = list(req.keys())
        if "token" in keys:
            req["token"] = kwargs["token"]
        if "pairs" in keys:
            req["pairs"][0] = kwargs["symbol"]
        # for k, v in kwargs.items():
        #     req[key] = [req[key][0].replace(f"<{k}>", v.lower())]
        print(333,req)
        return json.dumps(req)



class AccountRest(rest.Rest):

    def init(self):
        self._params = _params()

    def encode_list(self, item_list):
        list_val = []
        for item in item_list:
            obj_val = self.encode_object(item)
            list_val.append(obj_val)
        sorted_list = sorted(list_val)
        output = '&'.join(sorted_list)
        output = '[' + output + ']'
        return output

    def encode_object(self, param_map):
        sorted_keys = sorted(param_map.keys())
        ret_list = []
        for key in sorted_keys:
            val = param_map[key]
            if isinstance(val, list):
                list_val = self.encode_list(val)
                ret_list.append(f'{key}={list_val}')
            elif isinstance(val, dict):
                # call encode_object recursively
                dict_val = self.encode_object(val)
                ret_list.append(f'{key}={dict_val}')
            elif isinstance(val, bool):
                bool_val = str(val).lower()
                ret_list.append(f'{key}={bool_val}')
            else:
                general_val = str(val)
                ret_list.append(f'{key}={general_val}')

        sorted_list = sorted(ret_list)
        output = '&'.join(sorted_list)
        return output

    def sign(self, http_method, api_path, param_map):
        str_to_sign = api_path + '&' + self.encode_object(param_map)
        # print('str_to_sign = ' + str_to_sign)
        sig = hmac.new(self.privateKey.encode('utf-8'), str_to_sign.encode('utf-8'), digestmod=hashlib.sha256).hexdigest()
        # print(sig)
        return sig

    def httpRequest(self, method, url, headers=None, body={}, timeout=5):
        try:
            res = getattr(requests, method.lower())(url, headers=headers, timeout=timeout) \
                if len(body) == 0 else \
                getattr(requests, method.lower())(url, headers=headers, data=json.dumps(body), timeout=timeout)
            res = res.json()
        except requests.exceptions.ConnectTimeout:
            exceptions.raiseTimeout(self._params.exc, timeout=timeout)
        except requests.exceptions.ReadTimeout:
            exceptions.raiseTimeout(self._params.exc, timeout=timeout)
        except requests.exceptions.ProxyError:
            exceptions.raiseProxyError(self._params.exc)
        except simplejson.errors.JSONDecodeError:
            exceptions.raise400(self._params.exc)
        return res

    def request(self, path, params={}, body={}, timeout=5, isSign=True):
        """http request function

        Args:
            path (TYPE): request url
            params (dict, optional): in url
            body (dict, optional): in request body
            timeout (int, optional): request timeout(s)
        """
        # self.privateKey = "eabc3108-dd2b-43df-a98d-3e2054049b73"
        # # price = 8000 & qty = 30 & instrument_id = BTC - PERPETUAL & timestamp = 1588242614000
        # str_to_sign = "/v1/margins&instrument_id=BTC-PERPETUAL&price=8000&qty=30&timestamp=1588242614000"
        # sig = hmac.new(self.privateKey.encode('utf-8'), str_to_sign.encode('utf-8'),digestmod=hashlib.sha256).hexdigest()
        # print(sig)
        # exit()
        method, path = path.split(' ')
        if not isSign:
            req = params
        else:
            req = {
                # 'recvWindow': 3000,
                'timestamp': int(time.time()*1000),
            }
            req.update(params)
            # sign = urllib.parse.urlencode(req)
            # print(666,path)
            req['signature'] = self.sign(http_method = method,api_path = path ,param_map = req)

        if method == "GET":
            req = urllib.parse.urlencode(req)
            url = f"{self._params.restUrl}{path}" + f"?{req}"
            # print(url)
        else:
            body = req
            url = f"{self._params.restUrl}{path}"
            # print(url,req)
        headers = {
            'X-Bit-Access-Key': self.publicKey,
            'Content-Type': "application/json"
        }
        # body = req
        # print(url,body)
        res = self.httpRequest(method, url, headers, body, timeout)
        return res


    def getBalance(self):
        path = self._params.getRestPath(sys._getframe().f_code.co_name)
        data = self.request(path)
        # print(data)
        data = data["data"]['balances']
        # ---------------------------------
        data = [{
            'symbol': d['currency'].lower(),
            'balance': float(d['available']) + float(d['frozen']),
            'available': float(d['available']),
            'frozen': float(d['frozen']),
        } for d in data]

        data = transform.normalizeBalance(data=data)
        return data


    def getTick(self, symbol):
        params = {
            'pair': self._params.getSymbol(symbol),
            'count': 10,
        }
        path = self._params.getRestPath(sys._getframe().f_code.co_name)
        data = self.request(path, params=params, isSign=False)
        # print(data)
        # ---------------------------------
        data = [[
            d['created_at'],
            float(d['price']),
            float(d['qty']),
            -1 if d["side"]=="sell" else 1,
        ] for d in data["data"]]
        data = transform.normalizeTick(data=data)
        return data

    def getDepth(self, symbol, type=20):
        params = {
            'pair': self._params.getSymbol(symbol),
            'level': type,
        }
        path = self._params.getRestPath(sys._getframe().f_code.co_name)
        data = self.request(path, params=params, isSign=False)
        # print(data)
        # ---------------------------------
        timestamp = int(time.time()*1000)
        bids = np.array(data["data"]['bids']).astype('float').tolist()
        asks = np.array(data["data"]['asks']).astype('float').tolist()
        data = [data["data"]['timestamp'], bids, asks, timestamp]
        data = transform.normalizeDepth(data=data)
        return data

    def getKline(self, symbol, period, count=20):
        params = {
            'symbol': self._params.getSymbol(symbol),
            'interval': period,
            'limit': count,
        }
        path = self._params.getRestPath(sys._getframe().f_code.co_name)
        data = self.request(path, params=params, isSign=False)
        # print(data)
        # ---------------------------------
        data = [[
            float(d[0]),
            float(d[1]),
            float(d[2]),
            float(d[3]),
            float(d[4]),
            float(d[5]),
            float(d[7]),
        ] for d in data]
        data = transform.normalizeKline(data=data)
        return data

    def getFundingRate(self, symbol):
        params = {
            'symbol': self._params.getSymbol(symbol),
        }
        path = self._params.getRestPath(sys._getframe().f_code.co_name)
        data = self.request(path, params=params, isSign=False)
        # ---------------------------------
        timestamp = int(time.time()*1000)
        data = [
            data['time'],
            float(data['lastFundingRate']),
            np.nan,
            timestamp,
        ]
        data = transform.normalizeFundingRate(data=data)
        return data

    def getClearPrice(self, symbol):
        params = {
            'symbol': self._params.getSymbol(symbol),
        }
        path = self._params.getRestPath(sys._getframe().f_code.co_name)
        data = self.request(path, params=params, isSign=False)
        # ---------------------------------
        timestamp = int(time.time()*1000)
        data = [
            data['time'],
            float(data['indexPrice']),
            np.nan,
            timestamp
        ]
        data = transform.normalizeClearPrice(data=data)
        return data

    def makeOrder(self, symbol, vol, price=0, orderType='buy-limit',
                  offset='open', postOnly=False, clientOrderId=None):
        side, orderType = orderType.split('-')
        timeInForce = 'GTX' if postOnly else 'GTC'
        params = {
            'pair': self._params.getSymbol(symbol),
            'side': side,
            'qty': "%f"%(vol),
            'price': str(price),
            'order_type': orderType,
            'post_only': postOnly,
            # 'timeInForce': timeInForce,
        }
        path = self._params.getRestPath(sys._getframe().f_code.co_name)
        data = self.request(path, params=params)
        # print(data)
        # ---------------------------------
        if 'code' in data and data['code'] == 0:
            status = 'success'
            data = {
                'orderId': data["data"]['order_id'],
                'code': 0,
                'info': 'success',
            }
        else:
            status = 'failed'
            data = {
                'code': -1,
                'info': data,
            }

        data = transform.normalizeMakeOrder(status=status, data=data)
        return data

    def makeOrders(self, symbol, vol, price, orderType='buy-limit',
                   offset='open', postOnly=True, clientOrderId=None):
        side, orderType = orderType.split('-')
        timeInForce = 'GTX' if postOnly else 'GTC'
        if clientOrderId is None:
            clientOrderId = [None]*len(vol)
        reduceOnly = False if offset == 'open' else True if offset == 'close' else None
        timeInForce = 'GTX' if postOnly else 'GTC'
        batchOrders = [{
            'pair': self._params.getSymbol(symbol),
            'side': side,
            'qty': "%f"%(vol[i]),
            'price': str(price[i]),
            'order_type': orderType,
            'post_only': postOnly,
        } for i in range(len(vol))]
        params = {
            'orders_data': batchOrders,
        }
        path = self._params.getRestPath(sys._getframe().f_code.co_name)
        data = self.request(path, params=params)
        if 'code' in data and data['code'] == 0:
            status = 'success'
            data = {
                'orderId': data["data"],
                'code': 0,
                'info': 'success',
            }
        else:
            status = 'failed'
            data = {
                'code': -1,
                'info': data,
            }
        # print(data)
        data = transform.normalizeMakeOrder(status=status, data=data)
        return data

    def cancelOrder(self, symbol, orderId):
        params = {
            'pair': self._params.getSymbol(symbol),
            # 'orderId': orderId,
        }
        path = self._params.getRestPath(sys._getframe().f_code.co_name)
        data = self.request(path, params=params)
        # ---------------------------------
        if 'code' in data \
                and data['code'] == 0:
            status = 'success'
            data = {
                'orderId': orderId,
                'code': 0,
                'info': 'success',
            }
        else:
            status = 'failed'
            data = {
                'code': -1,
                'orderId': orderId,
                'info': data,
            }
        data = transform.normalizeCancelOrder(status=status, data=data)
        return data

    def cancelAll(self, symbol):
        params = {
            'pair': self._params.getSymbol(symbol),
            # 'orderId': orderId,
        }
        path = self._params.getRestPath(sys._getframe().f_code.co_name)
        data = self.request(path, params=params)
        # ---------------------------------
        if 'code' in data \
                and data['code'] == 0:
            status = 'success'
            data = {
                #'orderId': orderId,
                'code': 0,
                'info': 'success',
            }
        else:
            status = 'failed'
            data = {
                'code': -1,
                # 'orderId': orderId,
                'info': data,
            }
        data = transform.normalizeCancelOrder(status=status, data=data)
        return data

    def queryOrder(self, symbol, orderId):
        params = {
            'pair': self._params.getSymbol(symbol),
            'order_id': orderId,
        }
        path = self._params.getRestPath(sys._getframe().f_code.co_name)
        data = self.request(path, params=params)
        # print(data)
        # ---------------------------------
        if not(len(data["data"]) == 1):
            status = 'failed'
            data = {
                'symbol': symbol,
                'orderId': orderId,
                'info': data,
            }
        else:
            status = 'success'
            data = data["data"][0]
            data = {
                'ts': data['updated_at'],
                'symbol': symbol,
                'orderId': data['order_id'],
                'price': float(data['price']),
                'matchPrice': float(data['avg_price']),
                'vol': float(data['qty']),
                'matchVol': float(data['filled_qty']),
                # 'amt': float(data['price']) * float(data['origQty']),
                'side': data['side'].lower(),
                # 'offset': 'close' if data['reduceOnly'] else 'open',
                # 'type': data['type'].lower(),
                'postOnly': data['post_only'],
                'status': self._params.statusDict[data['status']] if data['status'] in self._params.statusDict else data['status'],
                'info': 'success',
            }
        data = transform.normalizeQueryOrder(status=status, data=data)
        return data

    def getOpenOrders(self, symbol):
        params = {
            'pair': self._params.getSymbol(symbol),
        }
        path = self._params.getRestPath(sys._getframe().f_code.co_name)
        data = self.request(path, params=params)
        # ---------------------------------
        # print(data)
        data = [{
            'ts': d['updated_at'],
            'symbol': symbol,
            'orderId': d['order_id'],
            'price': float(d['price']),
            'vol':  float(d['qty']),
            'matchVol': 0,
            # 'amt': float(d['price']) * float(d['origQty']),
            'side': d['side'].lower(),
            # 'offset': 'close' if d['reduceOnly'] else 'open',
            # 'type': d['type'].lower(),
            'postOnly': d['post_only'],
            'status': self._params.statusDict[d['status']] if d['status'] in self._params.statusDict else d['status'],
        } for d in data["data"]]
        data = transform.normalizeOpenOrders(data=data)
        return data

    def getDeals(self, symbol, count=100):
        if symbol == "all":
            params = {
                # 'pair': self._params.getSymbol(symbol),
                'count': count,
            }
        else:
            params = {
                'pair': self._params.getSymbol(symbol),
                'count': count,
            }
        path = self._params.getRestPath(sys._getframe().f_code.co_name)
        data = self.request(path, params=params)
        # print(data["data"])
        # ---------------------------------
        data = [{
            'ts': d['created_at'],
            'symbol': self._params.getSymbol_re(d['pair']),
            'myOrderId': d['order_id'],
            'tradeId': d['trade_id'],
            'price': float(d['price']),
            'vol': float(d['qty']),
            'amt': float(d['price']) * float(d['qty']),
            'fee': -float(d["fee"]),
            'feeAsset': self._params.getSymbol_re(d['pair']).split("/")[0] if d['side'] == "buy" else self._params.getSymbol_re(d['pair']).split("/")[1],
            'side': d['side'],
            'role': 'maker' if d["is_taker"] ==False else 'taker',
            } for d in data["data"]][::-1]
        data = transform.normalizeDeals(data=data)
        return data


class AccountWss(AccountRest, wss.websocketApp):

    def __init__(self, publicKey, privateKey, rspFunc, restartGap=0):
        self.publicKey = publicKey
        self.privateKey = privateKey
        self._params = _params()
        self.rspFunc = rspFunc
        self.author()  # 鉴权
        self.start(restartGap=restartGap)
        ping = threading.Thread(target=self.ping)
        ping.start()

    def getListenKey(self):
        path = self._params.getRestPath(sys._getframe().f_code.co_name)
        data = self.request(path, isSign=True)
        # print(1111, data)
        return data

    def refreshListenKey(self):
        params = {
            'listenKey': self.listenKey,
        }
        path = self._params.getRestPath(sys._getframe().f_code.co_name)
        data = self.request(path, params=params, isSign=False)
        return data

    def ping(self):
        while 1:
            time.sleep(60)
            try:
                req = {"type":"ping","params":{ "id":123}
}
                self.ws.send(req)
                pass
                # self.refreshListenKey()
            except:
                pass


    def init(self):
        self.subscribe(topic='balance', token =self.listenKey)
        self.subscribe(topic='orders', token=self.listenKey)
        self.subscribe(topic='deals', token=self.listenKey)
        pass

    def author(self):
        self.listenKey = self.getListenKey()['data']['token']
        # print(222,self.listenKey)
        self.wssUrl = f"{self._params.acctWssUrl}"

    def openRsp(self):
        # print(f"===== {time.strftime('%Y-%m-%d %H:%M:%S')} {self._params.exc} Account Websocket Connected =====")
        self.init()

        def ping(self):
            while 1:
                time.sleep(60)
                try:
                    req = {"type": "ping", "params": {"id": 123}
                           }
                    self.ws.send(req)
                    pass
                    # self.refreshListenKey()
                except:
                    pass

    def messageRsp(self, message):
        data = json.loads(message)

        # print(data)
        # return
        # ---------------------------------
        if data['channel'] == 'account':  # balance and position
            status = 'balance'
            data = data["data"]['balances']
            # ---------------------------------
            data = [{
                'symbol': d['currency'].lower(),
                'balance': float(d['available']) + float(d['frozen']),
                'available': float(d['available']),
                'frozen': float(d['frozen']),
            } for d in data]
            balance = transform.normalizeBalance(status=status, data=data)
            self.rspFunc(balance)


            return
        elif data['channel'] == 'user_trade':  # deals
            if data['o']['x'] == 'TRADE':
                status = 'deals'
                data = [{
                    'ts': d['created_at'],
                    'symbol': d["pair"].replace("-","/").lower(),
                    'myOrderId': d['order_id'],
                    'tradeId': d['trade_id'],
                    'price': float(d['price']),
                    'vol': float(d['qty']),
                    'amt': float(d['price']) * float(d['qty']),
                    'fee': float(d["fee"]),
                    'feeAsset': d["pair"].replace("-","/").lower().split("/")[0] if d['side'] == "buy" else d["pair"].replace("-","/").lower().split("/")[1],
                    'side': d['side'],
                    'role': 'maker' if d["is_taker"] == False else 'taker',
                } for d in data["data"]]
                deals = transform.normalizeDeals(status=status, data=data)
                self.rspFunc(deals)
            pass

        elif data['channel'] == 'order':  # deals
            status = 'orders'

            data = [{
                'ts': d['updated_at'],
                'symbol': d["pair"].replace("-","/").lower(),
                'orderId': d['order_id'],
                'price': float(d['price']),
                'vol': float(d['qty']),
                # 'matchVol': float(d['executedQty']),
                # 'amt': float(d['price']) * float(d['origQty']),
                'side': d['side'].lower(),
                # 'offset': 'close' if d['reduceOnly'] else 'open',
                # 'type': d['type'].lower(),
                'postOnly': d['post_only'],
                'status': self._params.statusDict[d['status']] if d['status'] in self._params.statusDict else d[
                    'status'],
            } for d in data["data"]]
            orders = transform.normalizeQueryOrder(status=status, data=data)
            self.rspFunc(orders)
            return

        else:
            return

        self.rspFunc(data)

    def closeRsp(self, isRestart):
        if isRestart:
            print(f"===== {time.strftime('%Y-%m-%d %H:%M:%S')} {self._params.exc} Account Websocket Reconnecting =====")
        else:
            print(f"===== {time.strftime('%Y-%m-%d %H:%M:%S')} {self._params.exc} Account Websocket Closed!! =====")


class DataWss(AccountWss):

    def __init__(self, symbol, publicKey='8xPSsNUylQUZEs81IWC3H28iLfY2lGbhH8aOMlLPlB9BEs2eEcXoraLBsx73rjsj'):
        self._params = _params()
        self.publicKey = publicKey
        self.wssUrl = self._params.wssUrl
        self.symbol = symbol
        # self.start(ping_interval=5, ping_timeout=3)
        self.start()
        ping = threading.Thread(target=self.ping)
        ping.start()

    def init(self):
        # self.subscribe(topic='tick', symbol=self.symbol)
        self.subscribe(topic='depth', symbol=self.symbol)
        # self.subscribe(topic='increDepthFlow', symbol=self.symbol)
        # self.subscribe(topic='kline', symbol=self.symbol, period='1m')
        # self.subscribe(topic='clearPrice', symbol=self.symbol)
        pass


    def openRsp(self):
        print(f"===== {time.strftime('%Y-%m-%d %H:%M:%S')} {self._params.exc} Websocket Connected =====")
        self.init()

    def messageRsp(self, message):
        rsp = json.loads(message)
        timestamp = int(time.time()*1000)
        # print(rsp, '\n')
        if "channel" in rsp:
            if rsp["channel"] == "ticker":  # tick
                data = [[rsp["timestamp"], float(rsp['data']["last_price"]), float(rsp['data']["last_qty"]), 0]]
                info = f"_wssData_{self.symbol}_tick"
                setattr(self, info, [timestamp, data])
                # print(info)
                # print(data)

            elif rsp["channel"] == "order_book.10.10":
                data = rsp
                bids = np.array(data["data"]['bids']).astype('float').tolist()
                asks = np.array(data["data"]['asks']).astype('float').tolist()
                data = [data["data"]['timestamp'], bids, asks, timestamp]
                info = f"_wssData_{self.symbol}_depth"
                setattr(self, info, [timestamp, data])
                # print(data[1][0], data[2][0])



    def closeRsp(self, isRestart):
        if isRestart:
            print(f"===== {time.strftime('%Y-%m-%d %H:%M:%S')} {self._params.exc} Websocket Reconnecting =====")
        else:
            print(f"===== {time.strftime('%Y-%m-%d %H:%M:%S')} {self._params.exc} Websocket Closed!! =====")


if __name__ == '__main__':
    publicKey = 'iMg4IeAm3t6yZjfXT1CTpajyZuL1ykYJKxVCSNeSNb3T9t3Phw8rr3gbRfXNCYQO'
    privateKey = 'QMG9RUaD7IWL5SFHDNz2cQ5j8GFkrVtdmR6ot14BYmUwjgGQFlvioews7rHc1bn4'
    publicKey = 'ak-3fed49b7-9628-46cd-bf3f-f8279f199bee'
    privateKey = '56uav0U98PitKSTb287dtDxuQlbOB2yLCHZF1FP6jNkTt1py1cARzVlWY66oi9zV'
    publicKey = 'ak-74909913-9345-43c0-a7af-78a0512d6a93'
    privateKey = 'GcmWDGM6rexQB3nJYBb1gAynPwOv0qkOoXdC0f7G48GB3bQdsTelznT557IMeBZD'
    #publicKey = 'ak-7b0e5054-36e9-4d8f-a01a-6ada5c07a033'
    #privateKey = 'meCRCDax2hxgNGasPYK6KWtLVHFhb14fBNVW7cxYZIY288yKiXskjfLm4F0KQ7h4'
    task = AccountRest(publicKey, privateKey)
    # print(task.getAccount())
    print(task.getBalance())
    # print(task.getPosition('trx/usdt'))
    # print(task.getFee('btc/usdt'))
    print(task.getTick('btc/usdt'))
    # print(task.getDepth('btc/usdt'))
    # print(task.getKline('btc/usdt', '1m'))
    # print(task.getFundingRate('btc/usdt'))
    # print(task.getClearPrice('btc/usdt'))
    # print(task.makeOrder('btc/usdt', 0.0008, price=45000, postOnly=True, orderType='buy-limit'))

    # print(task.makeOrders('btc/usdt', vol = [0.1,0.1], price = [5000,5000],orderType='buy-limit', postOnly=True))
    # print(task.cancelOrder('btc/usdt', 7768526829))
    # '52316405'
    # print(task.queryOrder('btc/usdt','73009549'))
    # print(task.getOpenOrders('btc/usdt'))
    # print(task.getDeals('btc/usdt', count=250))
    # vol = 0
    # fee = 0
    #data = task.getDeals('all', count=500)['data']
    #print(data)
    # for i in data:
    #     vol += i['vol']
    #     fee += float(i['fee'])
    # print(vol, fee)
    # '''--------------------------------------------------'''
    # def rspFunc(content):
    #     print(content)
    #task = AccountWss(publicKey, privateKey, rspFunc)
    # print(task.cancelAll('btc/usdt'))
    '''--------------------------------------------------'''
    # task = DataWss('btc/usdt')
