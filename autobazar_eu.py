from __future__ import annotations
import hashlib, re, time
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup
from .base import Source
from ..models import Listing

_PRICE=re.compile(r'(?<!\d)(\d{1,3}(?:[ .]\d{3})+|\d{4,6})\s*€')
_KM=re.compile(r'(?<!\d)(\d{1,3}(?:[ .]\d{3})+|\d{4,6})\s*km\b',re.I)
_KW=re.compile(r'(?<!\d)(\d{2,3})\s*kW\b',re.I)
_YEAR=re.compile(r'(?<!\d)(19[89]\d|20[0-2]\d)(?!\d)')
_DATE=re.compile(r'(?<!\d)(\d{2})\.(\d{2})\.(20\d{2})(?!\d)')

def _num(s): return int(re.sub(r'\D','',s))

class AutobazarEuSource(Source):
    name='autobazar_eu'
    def __init__(self, urls, user_agent='Mozilla/5.0', delay=2.0, max_pages=3):
        self.urls=urls; self.ua=user_agent; self.delay=delay; self.max_pages=max_pages

    def _page_url(self, base, page):
        if page==0: return base
        sep='&' if '?' in base else '?'
        return f'{base}{sep}page={page+1}'

    def fetch(self):
        headers={'User-Agent':self.ua,'Accept-Language':'sk-SK,sk;q=0.9,en;q=0.6'}
        for base in self.urls:
            for pageno in range(self.max_pages):
                url=self._page_url(base,pageno)
                r=requests.get(url,headers=headers,timeout=30); r.raise_for_status()
                soup=BeautifulSoup(r.text,'lxml'); seen=set()
                for a in soup.select('a[href*="/detail/"]'):
                    href=urljoin(r.url,a.get('href',''))
                    if href in seen: continue
                    title=' '.join(a.get_text(' ',strip=True).split())
                    if len(title)<5 or title.upper() in {'PREMIUM','TOP','SUPER','AKCIA'} or '€' in title: continue
                    root=a
                    for _ in range(7):
                        if not root.parent: break
                        cand=root.parent; txt=' '.join(cand.get_text(' ',strip=True).split())
                        if _PRICE.search(txt) and (_KM.search(txt) or _YEAR.search(txt)):
                            root=cand; break
                        root=cand
                    text=' '.join(root.get_text(' ',strip=True).split())
                    pm=_PRICE.search(text); km=_KM.search(text); kw=_KW.search(text)
                    year_text=_DATE.sub('',text); years=[int(y) for y in _YEAR.findall(year_text)]
                    price=float(_num(pm.group(1))) if pm else None
                    mileage=_num(km.group(1)) if km else None
                    power=int(kw.group(1)) if kw else None
                    year=max([y for y in years if 1980<=y<=2030],default=None)
                    dm=_DATE.search(text); posted=f'{dm.group(3)}-{dm.group(2)}-{dm.group(1)}' if dm else None
                    sidm=re.search(r'/detail/[^/]+/([^/]+)/?',href)
                    sid=sidm.group(1) if sidm else hashlib.sha1(href.encode()).hexdigest()[:16]
                    seen.add(href)
                    yield Listing(self.name,str(sid),href,title,price_eur=price,price_original=price,currency='EUR',
                                  year=year,mileage_km=mileage,power_kw=power,posted_at=posted,description=text[:9000])
                time.sleep(self.delay)
