import sys
sys.path.append('/usr/local/server')
import time
import threading
import traceback
import Toolbox as tb
import numpy as np
from django.shortcuts import render
# usdtSwap: 正向永续 coins: 全币种 coinSwap: 反向永续


class Params():

    """要用的参数

    Attributes:
        door (str): Description
        usdtSwapSymbols (list): Description
    """

    def __init__(self):
        self.door = 'https://monitor.jumpserver.org:1234/'
        self.arbitrageSymbols = [
            'usdt_arbitrage',
            'btc_arbitrage',
            'eth_arbitrage',
            #'bnb',
            #'usdt_ml',
        ]
        self.bitmartSymbols = [
            'btcusdt',
        ]
        self.depthSymbols = ['btc', 'eth']


paras = Params()
redis = tb.Redis()  # 配置redis
redis2 = tb.Redis()


def th_getData():   # 获取redis数据
    while 1:
        tables = [i for i in redis2.query() if 'table' in i]
        for table in tables:
            try:
                data = redis2.get(table)
                # print(data)
                setattr(paras, table, data)
            except:
                print(traceback.format_exc())
        time.sleep(30)


process = threading.Thread(target=th_getData)
process.start()


def portal(request):
    jump1 = [
        f"<a href='{paras.door}arbitrage/{paras.arbitrageSymbols[0]}/'>套利</a>",
        f"<a href='{paras.door}bitmart/{paras.bitmartSymbols[0]}/'>bit</a>",
    ]
    jump2 = [
        # f"<a href='{paras.door}hedgeAccount/'>套保账户</a>",
        f"<a href='{paras.door}depth/{paras.depthSymbols[0]}/'>流动性监控</a>",
        f"<a href='{paras.door}bitdepth/{paras.bitmartSymbols[0]}/'>bit摆盘监控</a>",
        # f"<a href='{paras.door}fundingRate/'>各交易所资金费率监控</a>",
    ]
    jump3 = [
        # f"<a href='{paras.door}binanceUsdtSwap/{paras.binanceUsdtSwapSymbols[0]}/'>币安正向合约</a>",
        # f"<a href='{paras.door}arbitrage/{paras.arbitrageSymbols[0]}/'>套利</a>",
    ]

    content = {}
    content['jump1'] = jump1
    content['jump2'] = jump2
    content['jump3'] = jump3
    return render(request, 'portal.html', content)


def jump(prefix=None):
    if prefix is None:
        symbols = ['首页']
    else:
        symbols = ['首页']+getattr(paras, f'{prefix}Symbols')

    urls = [f'{paras.door}{prefix}/{symbol}/' if symbol != '首页'
            else paras.door
            for symbol in symbols]

    pls = np.full(len(symbols), np.nan)
    for i, symbol in enumerate(symbols):
        if i == 0:
            continue
        try:
            data = np.array(
                getattr(paras, f'{prefix}_{symbol}_table'))
            data = data[:, 4]
            #print(data)
            pls[i] = np.nansum([float(i.split(':')[-1]) for i in data])
        except:
            #print(traceback.format_exc())
            continue
    pls[0] = np.nansum(pls[1:])
    urls = [[f"<a href='{url}'>{symbols[i]}\n\n{pls[i]:0.2f}</a>", pls[i]]
            for i, url in enumerate(urls)]
    return urls

def button(url, name):
    return f"<a href='{paras.door}{url}/'>{name}</a>"

def arbitrage(request, symbol=paras.arbitrageSymbols[0]):
    '''套利'''
    content = {}
    content['jump'] = jump('arbitrage')    
    content['symbol'] = symbol.upper()
    content['test'] = 'n/a'
    try:
        content['content'] = redis2.get(f'arbitrage_{symbol}_table')
        content['info'] = redis2.get(f'arbitrage_{symbol}_info')
    except:
        pass
    return render(request, 'arbitrage.html', content)

def bitmart(request, symbol=paras.bitmartSymbols[0]):
    '''bitmart'''
    content = {}
    content['jump'] = jump('bitmart')    
    content['symbol'] = symbol.upper()
    content['test'] = 'n/a'
    try:
        content['content'] = redis2.get(f'bitSpot_{symbol}_table')
        content['info'] = redis2.get(f'bitSpot_{symbol}_info')
    except:
        pass
    return render(request, 'monitorNew.html', content)

def bitdepth(request, symbol=paras.bitmartSymbols[0]):
    '''bitm=摆盘监控'''
    content = {}
    content['jump'] = jump('bitmart')
    content['symbol'] = symbol.upper()
    content['test'] = 'n/a'
    try:
        content['ordersdepth'] = redis2.get(f'bitSpot_{symbol}_ordersdepth')
        content['info'] = redis2.get(f'bitSpot_{symbol}_info')
    except:
        pass
    return render(request, 'monitor_depth.html', content)

def depth(request, symbol=paras.depthSymbols[0]):
    """流动性监控

    Args:
        request (TYPE): Description
        symbol (TYPE, optional): Description

    Returns:
        TYPE: Description
    """
    content = {}
    content['jump'] = jump('depth')
    content['mysymbol'] = symbol.upper()
    data = redis2.get(f'depth_result_{symbol}')
    key = ['timestamp', 'content', 'data_volume',
           'volume_timelist', 'time_liqu_list', 'data_liqu_list']
    data2 = redis2.get(f'depth_signal_{symbol}')
    for i, k in enumerate(key):
        if k == 'content':
            for m in data[i]:
                if m[0] in data2.keys():
                    m += data2[m[0]]
                else:
                    m += [None]*len(list(data2.values())[0])
            content[k] = data[i][-30:]
    print(content)
    return render(request, 'depth.html', content)
