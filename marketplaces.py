from __future__ import annotations
import hashlib, json, re, time
from urllib.parse import urljoin, urlencode, urlparse, parse_qsl, urlunparse
import requests
from bs4 import BeautifulSoup
from .base import Source
from ..models import Listing
from ..fx import to_eur

SPACE='\u00a0\u202f '
PRICE_RE=re.compile(r'(?<!\d)(\d{1,3}(?:[\s.\u00a0\u202f]\d{3})+|\d{3,9})(?:[,.]\d{1,2})?\s*(EUR|€|PLN|zł|HUF|Ft|CZK|Kč)',re.I)
KM_RE=re.compile(r'(?<!\d)(\d{1,3}(?:[\s.\u00a0\u202f]\d{3})+|\d{4,7})\s*km\b',re.I)
YEAR_RE=re.compile(r'(?<!\d)(19[7-9]\d|20[0-2]\d)(?:/\d{1,2})?(?!\d)')
KW_RE=re.compile(r'(?<!\d)(\d{2,4})\s*kW\b',re.I)
HP_PL_RE=re.compile(r'(?<!\d)(\d{2,4})\s*KM\b')
HP_HU_RE=re.compile(r'(?<!\d)(\d{2,4})\s*LE\b',re.I)

def _n(s): return int(re.sub(r'\D','',s))
def _currency(s):
    q=s.lower()
    if q in {'€','eur'}: return 'EUR'
    if q in {'pln','zł'}: return 'PLN'
    if q in {'huf','ft'}: return 'HUF'
    if q in {'czk','kč'}: return 'CZK'
    return s.upper()

def _page_url(name,base,page):
    n=page+1
    if page==0: return base
    if name=='hasznaltauto_hu': return base.rstrip('/')+f'/page{n}'
    parts=urlparse(base); qs=dict(parse_qsl(parts.query,keep_blank_values=True)); qs['page']=str(n)
    return urlunparse(parts._replace(query=urlencode(qs)))

def _valid_href(name,href):
    h=href.lower()
    if name=='otomoto_pl': return '/osobowe/oferta/' in h
    if name=='hasznaltauto_hu': return '/szemelyauto/' in h and bool(re.search(r'[-_/]\d{6,}(?:$|[/?#])',h))
    if name=='willhaben_at': return '/iad/gebrauchtwagen/d/' in h and ('auto' in h or re.search(r'/\d{6,}',h))
    if name=='autoscout24_at': return '/angebote/' in h
    return False

def _card_for_anchor(a):
    best=a.parent
    for _ in range(8):
        if not best or not getattr(best,'parent',None): break
        txt=' '.join(best.get_text(' ',strip=True).split())
        if PRICE_RE.search(txt) and (KM_RE.search(txt) or YEAR_RE.search(txt)) and len(txt)<7000:
            return best
        best=best.parent
    return a.parent

def _parse_price(text):
    m=PRICE_RE.search(text)
    if not m: return None,None,None
    value=float(_n(m.group(1))); cur=_currency(m.group(2))
    return to_eur(value,cur),value,cur

def _best_title(a,root):
    for sel in ['h2','h3','h4','[data-testid*="title"]','[class*="title"]']:
        el=root.select_one(sel) if root else None
        if el:
            t=' '.join(el.get_text(' ',strip=True).split())
            if 4<len(t)<240: return t
    t=' '.join(a.get_text(' ',strip=True).split())
    if 4<len(t)<240: return t
    return (a.get('title') or '').strip()

def _seller(text):
    low=text.lower()
    if any(k in low for k in ['magánszemély','prywatny sprzedawca','privat','private seller','súkrom','soukrom']): return 'private'
    if any(k in low for k in ['kereskedés','firma','händler','dealer']): return 'dealer'
    return None

class PagedMarketplaceSource(Source):
    def __init__(self,name,urls,user_agent='Mozilla/5.0',delay=1.1,max_pages=5):
        self.name=name; self.urls=urls; self.ua=user_agent; self.delay=delay; self.max_pages=max_pages

    def fetch(self):
        headers={'User-Agent':self.ua,'Accept-Language':'sk,cs,de,pl,hu,en;q=0.7'}
        for base in self.urls:
            for page in range(self.max_pages):
                url=_page_url(self.name,base,page)
                r=requests.get(url,headers=headers,timeout=30); r.raise_for_status()
                soup=BeautifulSoup(r.text,'lxml'); yielded=set()

                # First pass: JSON-LD item lists/products when present.
                for node in soup.select('script[type="application/ld+json"]'):
                    try: data=json.loads(node.string or '{}')
                    except Exception: continue
                    objs=data if isinstance(data,list) else [data]
                    stack=list(objs)
                    while stack:
                        obj=stack.pop()
                        if isinstance(obj,list): stack.extend(obj); continue
                        if not isinstance(obj,dict): continue
                        for key in ['itemListElement','item','mainEntity','offers']:
                            val=obj.get(key)
                            if isinstance(val,(dict,list)): stack.append(val)
                        title=obj.get('name'); href=obj.get('url')
                        if not (title and href): continue
                        full=urljoin(r.url,str(href))
                        if not _valid_href(self.name,full): continue
                        sid=hashlib.sha1(full.encode()).hexdigest()[:18]
                        if sid in yielded: continue
                        price=None; orig=None; cur=None
                        offers=obj.get('offers') if isinstance(obj.get('offers'),dict) else {}
                        if offers:
                            try:
                                orig=float(str(offers.get('price')).replace(' ','').replace(',','.'))
                                cur=_currency(str(offers.get('priceCurrency') or 'EUR')); price=to_eur(orig,cur)
                            except Exception: pass
                        yielded.add(sid)
                        yield Listing(self.name,sid,full,str(title),price_eur=price,price_original=orig,currency=cur,description=json.dumps(obj,ensure_ascii=False)[:7000])

                # Robust HTML fallback: treat each matching ad link as one separate listing.
                for a in soup.select('a[href]'):
                    href=urljoin(r.url,a.get('href',''))
                    if not _valid_href(self.name,href): continue
                    sid=hashlib.sha1(href.split('#')[0].encode()).hexdigest()[:18]
                    if sid in yielded: continue
                    root=_card_for_anchor(a); text=' '.join((root.get_text(' ',strip=True) if root else a.get_text(' ',strip=True)).split())
                    title=_best_title(a,root)
                    if not title or len(title)<4: continue
                    price,orig,cur=_parse_price(text)
                    km=None
                    vals=[_n(m.group(1)) for m in KM_RE.finditer(text)]
                    vals=[v for v in vals if 1000<=v<=2000000]
                    if vals: km=max(vals)
                    years=[int(y) for y in YEAR_RE.findall(text)]; year=max([y for y in years if 1970<=y<=2027],default=None)
                    power=None
                    m=KW_RE.search(text)
                    if m: power=int(m.group(1))
                    else:
                        hm=HP_PL_RE.search(text) if self.name=='otomoto_pl' else HP_HU_RE.search(text)
                        if hm:
                            hp=int(hm.group(1)); power=round(hp*0.735499) if 30<=hp<=1600 else None
                    yielded.add(sid)
                    yield Listing(self.name,sid,href,title,price_eur=price,price_original=orig,currency=cur,year=year,mileage_km=km,power_kw=power,
                                  seller_type=_seller(text),description=text[:9000])
                time.sleep(self.delay)
