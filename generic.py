from __future__ import annotations
import json, re, time, hashlib
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup
from .base import Source
from ..models import Listing

class GenericHtmlSource(Source):
    """Fallback for marketplaces with server-rendered cards or JSON-LD.
    It intentionally avoids browser automation. If a site becomes JS-only, use its API/feed
    or add a dedicated adapter rather than hammering the website.
    """
    def __init__(self,name,urls,user_agent='Mozilla/5.0',delay=2.0):
        self.name=name; self.urls=urls; self.ua=user_agent; self.delay=delay
    def fetch(self):
        for url in self.urls:
            r=requests.get(url,headers={'User-Agent':self.ua},timeout=20)
            r.raise_for_status(); soup=BeautifulSoup(r.text,'lxml')
            yielded=set()
            # JSON-LD Product/Vehicle/Offer blocks
            for node in soup.select('script[type="application/ld+json"]'):
                try: data=json.loads(node.string or '{}')
                except Exception: continue
                stack=data if isinstance(data,list) else [data]
                for obj in stack:
                    if not isinstance(obj,dict): continue
                    items=obj.get('itemListElement') or []
                    if not isinstance(items,list): items=[]
                    candidates=[obj]+[i.get('item',i) if isinstance(i,dict) else i for i in items]
                    for c in candidates:
                        if not isinstance(c,dict): continue
                        name=c.get('name')
                        href=c.get('url')
                        offers=c.get('offers') or {}
                        price=offers.get('price') if isinstance(offers,dict) else None
                        if name and href:
                            full=urljoin(r.url,href); sid=hashlib.sha1(full.encode()).hexdigest()[:16]
                            if sid in yielded: continue
                            yielded.add(sid)
                            try: price=float(str(price).replace(',','.')) if price is not None else None
                            except: price=None
                            yield Listing(self.name,sid,full,str(name),price_eur=price,description=json.dumps(c,ensure_ascii=False)[:4000])
            # Conservative fallback: anchors that look like ad/detail URLs and nearby € price.
            for a in soup.select('a[href]'):
                title=a.get_text(' ',strip=True)
                href=urljoin(r.url,a.get('href'))
                if len(title)<8 or not any(k in href.lower() for k in ['auto','vehicle','vozid','inzer','detail','offer']): continue
                root=a.parent
                text=root.get_text(' ',strip=True) if root else title
                pm=re.search(r'(\d[\d .]{2,})\s*€',text)
                if not pm: continue
                sid=hashlib.sha1(href.encode()).hexdigest()[:16]
                if sid in yielded: continue
                yielded.add(sid)
                price=float(re.sub(r'\D','',pm.group(1)))
                yield Listing(self.name,sid,href,title,price_eur=price,description=text[:4000])
            time.sleep(self.delay)
