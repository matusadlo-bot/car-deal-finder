from __future__ import annotations
import os, requests
from .base import Source
from .errors import SourceUnavailable
from ..models import Listing

class MobileDeSource(Source):
    name='mobile_de'
    def __init__(self, cfg): self.cfg=cfg

    @staticmethod
    def _text(v):
        if isinstance(v, dict):
            return v.get('localDescription') or v.get('description') or v.get('name') or v.get('key')
        return v

    def fetch(self):
        user=os.getenv('MOBILE_DE_API_USERNAME','').strip(); pwd=os.getenv('MOBILE_DE_API_PASSWORD','').strip()
        if not user or not pwd:
            raise SourceUnavailable('Mobile.de: chýba MOBILE_DE_API_USERNAME / MOBILE_DE_API_PASSWORD. Oficiálny Search API vyžaduje API prístup.')
        params=dict(self.cfg.get('query') or {})
        params.setdefault('classification','refdata/classes/Car')
        params.setdefault('country',self.cfg.get('country','DE'))
        params.setdefault('sort.field','modificationTime'); params.setdefault('sort.order','DESCENDING')
        params.setdefault('page.size',min(100,int(self.cfg.get('page_size',100))))
        max_pages=int(self.cfg.get('max_pages',3))
        headers={'Accept':'application/vnd.de.mobile.api+json','User-Agent':'CarDealFinder/0.4'}
        for page in range(1,max_pages+1):
            params['page.number']=page
            r=requests.get('https://services.mobile.de/search-api/search',params=params,auth=(user,pwd),headers=headers,timeout=35)
            if r.status_code in (401,403):
                raise SourceUnavailable(f'Mobile.de API odmietlo prihlásenie ({r.status_code}). Skontroluj API credentials, nie bežné heslo do mobile.de.')
            r.raise_for_status(); data=r.json()
            for ad in data.get('ads',[]) or []:
                sid=str(ad.get('mobileAdId') or ad.get('id') or ad.get('adKey') or ad.get('key') or '')
                if not sid: continue
                make=self._text(ad.get('make')); model=self._text(ad.get('model'))
                title=(ad.get('modelDescription') or ' '.join(filter(None,[str(make or ''),str(model or '')]))).strip()
                priceobj=ad.get('price') or {}
                price=priceobj.get('consumerPriceGross') or priceobj.get('gross') or priceobj.get('amount')
                try: price=float(price)
                except (TypeError,ValueError): price=None
                reg=str(ad.get('firstRegistration') or '')
                year=int(reg[:4]) if len(reg)>=4 and reg[:4].isdigit() else None
                mileage=ad.get('mileage')
                try: mileage=int(mileage)
                except (TypeError,ValueError): mileage=None
                power=ad.get('power') or ad.get('powerKw')
                if isinstance(power,dict): power=power.get('kw') or power.get('value')
                try: power=int(float(power))
                except (TypeError,ValueError): power=None
                seller=ad.get('seller') or {}; seller_type=seller.get('type') if isinstance(seller,dict) else None
                addr=seller.get('address') if isinstance(seller,dict) else None
                location=None
                if isinstance(addr,dict): location=' '.join(filter(None,[str(addr.get('zip') or ''),str(addr.get('city') or '')])).strip() or None
                url=f'https://suchen.mobile.de/fahrzeuge/details.html?id={sid}'
                yield Listing(self.name,sid,url,title,price_eur=price,price_original=price,currency='EUR',
                              make=str(make) if make else None,model=str(model) if model else None,year=year,
                              mileage_km=mileage,power_kw=power,location=location,seller_type=seller_type,
                              posted_at=(ad.get('creationDate') or None),description=str(ad)[:9000])
            maxp=int(data.get('maxPages') or page)
            if page >= maxp: break
