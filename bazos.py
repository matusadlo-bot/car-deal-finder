from __future__ import annotations
import re, time, hashlib
from datetime import datetime
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup
from .base import Source
from ..models import Listing
from ..fx import get_czk_per_eur

_MONEY = re.compile(r'([0-9][0-9 .]*)\s*(Kč|CZK|€|EUR)', re.I)
_VIEWS = re.compile(r'(?<!\d)(\d{1,3}(?:[ .]\d{3})*|\d{1,7})\s*x\b', re.I)
_DATE = re.compile(r'(?<!\d)(\d{1,2})\.\s*(\d{1,2})\.\s*(20\d{2})(?!\d)')
_JUNK = re.compile(r'\b(pouze\s+d[ií]ly|na\s+d[ií]ly|n[aá]hradn[ií]\s+d[ií]ly|pneumatik|karavan|p[řr][ií]v[eě]s|autobus|dod[aá]vk|n[aá]kladn[ií])\b', re.I)

def _num(text: str) -> int:
    return int(re.sub(r'\D', '', text))

def _parse_date(text: str):
    m = _DATE.search(text)
    if not m: return None
    try:
        return datetime(int(m.group(3)), int(m.group(2)), int(m.group(1))).date().isoformat()
    except ValueError:
        return None

def _parse_price(card_text: str, price_text: str | None, source_name: str):
    sample = price_text or card_text
    m = _MONEY.search(sample)
    if not m: return None, None, None
    val = float(_num(m.group(1)))
    curr = m.group(2).upper().replace('€','EUR')
    if curr == 'KČ': curr = 'CZK'
    if source_name.endswith('_cz') or curr == 'CZK':
        return round(val / get_czk_per_eur(), 2), val, 'CZK'
    return val, val, 'EUR'

class BazosSource(Source):
    def __init__(self, name, urls, user_agent='Mozilla/5.0', delay=2.0, max_pages=3, passenger_only=True):
        self.name=name; self.urls=urls; self.ua=user_agent; self.delay=delay; self.max_pages=max_pages
        self.passenger_only=passenger_only

    def fetch(self):
        headers={'User-Agent':self.ua, 'Accept-Language':'sk,cs;q=0.9,en;q=0.6'}
        for base in self.urls:
            for page in range(self.max_pages):
                url = base if page==0 else (base.rstrip('/') + f'/{page*20}/')
                r=requests.get(url,headers=headers,timeout=25)
                r.raise_for_status(); soup=BeautifulSoup(r.text,'lxml')
                seen=set()
                for root in soup.select('div.inzeraty'):
                    a=(root.select_one('.inzeratynadpis h2 a[href]') or
                       root.select_one('h2 a[href]') or
                       root.select_one('.inzeratynadpis a[href]'))
                    if not a: continue
                    href=urljoin(r.url,a.get('href',''))
                    if '/inzerat/' not in href or href in seen: continue
                    seen.add(href)
                    title=a.get_text(' ',strip=True)
                    if not title: continue
                    text=root.get_text(' ',strip=True)
                    if self.passenger_only and _JUNK.search(title): continue
                    pe=root.select_one('.inzeratycena')
                    price_eur, price_original, currency=_parse_price(text, pe.get_text(' ',strip=True) if pe else None, self.name)
                    loc=None
                    el=root.select_one('.inzeratylok, .inzeratylokalita')
                    if el: loc=' '.join(el.get_text(' ',strip=True).split())
                    views=None
                    for node in root.find_all(string=re.compile(r'\d[\d .]*\s*x\s*$', re.I)):
                        vm=re.search(r'(\d{1,3}(?:[ .]\d{3})*|\d+)\s*x\s*$', str(node).strip(), re.I)
                        if vm:
                            views=_num(vm.group(1)); break
                    posted=_parse_date(text)
                    sidm=re.search(r'/inzerat/(\d+)',href)
                    sid=sidm.group(1) if sidm else hashlib.sha1(href.encode()).hexdigest()[:16]
                    desc=' '.join(text.split())
                    yield Listing(source=self.name,source_id=str(sid),url=href,title=title,
                                  price_eur=price_eur,price_original=price_original,currency=currency,
                                  location=loc,views=views,posted_at=posted,description=desc)
                time.sleep(self.delay)
