from __future__ import annotations
import re, time
from datetime import datetime, timezone
import requests
from bs4 import BeautifulSoup
from .db import connect
from .models import Listing
from .normalize import normalize_listing
from .opportunities import enrich_opportunity

VIEW_RE=re.compile(r'(?<!\d)(\d{1,3}(?:[ .]\d{3})*|\d+)\s*x\b',re.I)

def _row_to_listing(r):
    fields=Listing.__dataclass_fields__.keys()
    return Listing(**{k:r[k] for k in fields if k in r.keys()})

def hydrate_candidates(limit:int=30, delay:float=0.6, user_agent='Mozilla/5.0'):
    if limit<=0: return {'hydrated':0,'status':'disabled'}
    with connect() as con:
        rows=con.execute('''SELECT * FROM listings
            WHERE url IS NOT NULL AND (detail_fetched_at IS NULL OR detail_fetched_at < first_seen)
            ORDER BY COALESCE(interesting_score,0) DESC, COALESCE(special_score,0) DESC, COALESCE(deal_score,0) DESC
            LIMIT ?''',(limit,)).fetchall()
    done=0; errors=0
    for r in rows:
        try:
            resp=requests.get(r['url'],headers={'User-Agent':user_agent,'Accept-Language':'sk,cs,de,pl,hu,en;q=0.7'},timeout=25)
            resp.raise_for_status(); soup=BeautifulSoup(resp.text,'lxml')
            for bad in soup(['script','style','noscript','svg']): bad.decompose()
            main=soup.select_one('main, article, [role="main"]') or soup.body or soup
            text=' '.join(main.get_text(' ',strip=True).split())[:18000]
            if len(text)<80: continue
            x=_row_to_listing(r); x.description=text
            h1=soup.select_one('h1')
            if h1:
                t=' '.join(h1.get_text(' ',strip=True).split())
                if 4<len(t)<260: x.title=t
            if x.views is None:
                vm=VIEW_RE.search(text)
                if vm:
                    try: x.views=int(re.sub(r'\D','',vm.group(1)))
                    except: pass
            x=normalize_listing(x); x=enrich_opportunity(x)
            now=datetime.now(timezone.utc).isoformat()
            with connect() as con:
                con.execute('''UPDATE listings SET title=?,description=?,make=?,model=?,year=?,mileage_km=?,power_kw=?,fuel=?,transmission=?,drive=?,body_style=?,engine_signature=?,variant_signature=?,views=?,
                    special_score=?,hidden_gem_score=?,rare_score=?,rare_reason=?,repair_score=?,repair_reason=?,repair_estimate_min_eur=?,repair_estimate_max_eur=?,repair_risk=?,local_tags=?,detail_fetched_at=?
                    WHERE source=? AND source_id=?''',
                    (x.title,x.description,x.make,x.model,x.year,x.mileage_km,x.power_kw,x.fuel,x.transmission,x.drive,x.body_style,x.engine_signature,x.variant_signature,x.views,
                     x.special_score,x.hidden_gem_score,x.rare_score,x.rare_reason,x.repair_score,x.repair_reason,x.repair_estimate_min_eur,x.repair_estimate_max_eur,x.repair_risk,x.local_tags,now,x.source,x.source_id))
            done+=1; time.sleep(delay)
        except Exception:
            errors+=1
    return {'hydrated':done,'errors':errors,'status':'OK'}
