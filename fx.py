from __future__ import annotations
import os, time
import xml.etree.ElementTree as ET
import requests

ECB_URL='https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml'
_CACHE={'rates':{},'ts':0.0}
FALLBACK={'CZK':25.0,'PLN':4.30,'HUF':390.0,'GBP':0.86,'CHF':0.94}

def _load_rates():
    if _CACHE['rates'] and time.time()-_CACHE['ts']<6*3600: return _CACHE['rates']
    rates=dict(FALLBACK)
    for cur in list(rates):
        env=os.getenv(f'{cur}_PER_EUR')
        if env:
            try: rates[cur]=float(env.replace(',','.'))
            except ValueError: pass
    try:
        r=requests.get(ECB_URL,timeout=8,headers={'User-Agent':'CarDealFinder/0.4'})
        r.raise_for_status(); root=ET.fromstring(r.content)
        for node in root.iter():
            cur=node.attrib.get('currency')
            if cur and 'rate' in node.attrib:
                rates[cur]=float(node.attrib['rate'])
    except Exception:
        pass
    _CACHE.update(rates=rates,ts=time.time()); return rates

def get_per_eur(currency:str)->float:
    cur=(currency or 'EUR').upper()
    if cur=='EUR': return 1.0
    return float(_load_rates().get(cur,FALLBACK.get(cur,1.0)))

def to_eur(value:float|int|None,currency:str|None):
    if value is None: return None
    cur=(currency or 'EUR').upper()
    if cur=='EUR': return float(value)
    rate=get_per_eur(cur)
    return round(float(value)/rate,2) if rate else None

def get_czk_per_eur()->float: return get_per_eur('CZK')
