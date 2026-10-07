from __future__ import annotations
import json, os
from pathlib import Path
from dotenv import load_dotenv
from .db import init_db, upsert, record_source_run
from .normalize import normalize_listing
from .opportunities import enrich_opportunity
from .classification import classify_vehicle
from .scoring import rescore_all
from .detail_enrich import hydrate_candidates
from .ai_analysis import analyze_candidates
from .notify import send_telegram_new_deals
from .sources.bazos import BazosSource
from .sources.mobile_de import MobileDeSource
from .sources.autobazar_eu import AutobazarEuSource
from .sources.marketplaces import PagedMarketplaceSource

ROOT=Path(__file__).resolve().parent.parent

def load_config(): return json.loads((ROOT/'config.json').read_text(encoding='utf-8'))

def _pages(sc:dict,mode:str,default:int=5):
    key='deep_pages' if mode=='deep' else 'quick_pages'
    return int(sc.get(key,default))

def build_sources(cfg, mode='quick'):
    ua=os.getenv('USER_AGENT','Mozilla/5.0 (Windows NT 10.0; Win64; x64) CarDealFinder/0.4')
    delay=float(os.getenv('REQUEST_DELAY_SECONDS',str(cfg.get('request_delay_seconds',1.1))))
    out=[]; s=cfg['sources']
    if s.get('bazos_sk',{}).get('enabled'):
        sc=s['bazos_sk']; out.append(BazosSource('bazos_sk',sc['search_urls'],ua,delay,_pages(sc,mode,10)))
    if s.get('bazos_cz',{}).get('enabled'):
        sc=s['bazos_cz']; out.append(BazosSource('bazos_cz',sc['search_urls'],ua,delay,_pages(sc,mode,10)))
    if s.get('autobazar_eu',{}).get('enabled'):
        sc=s['autobazar_eu']; out.append(AutobazarEuSource(sc['search_urls'],ua,delay,_pages(sc,mode,8)))
    for name in ['otomoto_pl','hasznaltauto_hu','willhaben_at','autoscout24_at']:
        sc=s.get(name,{})
        if sc.get('enabled') and sc.get('search_urls'):
            out.append(PagedMarketplaceSource(name,sc['search_urls'],ua,delay,_pages(sc,mode,5)))
    if s.get('mobile_de',{}).get('enabled'):
        mc=dict(s['mobile_de']); mc['max_pages']=_pages(mc,mode,3); out.append(MobileDeSource(mc))
    return out

def run_scan(mode='quick'):
    if mode not in {'quick','deep'}: mode='quick'
    load_dotenv(ROOT/'.env',override=True); cfg=load_config(); init_db(); stats={'mode':mode}
    for src in build_sources(cfg,mode):
        n=0; err=None
        try:
            for item in src.fetch() or []:
                x=normalize_listing(item)
                ok,conf,why=classify_vehicle(x)
                x.is_vehicle=1 if ok else 0
                x.vehicle_confidence=round(conf,3)
                x.vehicle_reject_reason=why
                if not ok:
                    continue
                x=enrich_opportunity(x)
                upsert(x); n+=1
        except Exception as e:
            err=f'{type(e).__name__}: {e}'
        stats[src.name]={'saved':n,'error':err}; record_source_run(src.name,n,err)

    # Every fetched listing gets the local analyser above. Price/scarcity is learned from the whole DB here.
    rescore_all()
    detail_limit=int(cfg.get('detail_candidates_deep' if mode=='deep' else 'detail_candidates_quick',30))
    try:
        stats['detail']=hydrate_candidates(detail_limit,delay=min(0.8,float(cfg.get('request_delay_seconds',1.1))))
        if stats['detail'].get('hydrated'): rescore_all()
    except Exception as e:
        stats['detail']={'hydrated':0,'status':f'{type(e).__name__}: {e}'}
    try:
        stats['ai']=analyze_candidates(int(cfg.get('ai_candidates_per_scan',12)))
        if stats['ai'].get('analyzed'): rescore_all()
    except Exception as e: stats['ai']={'analyzed':0,'status':str(e)}
    try: stats['telegram']={'sent':send_telegram_new_deals(cfg.get('alert_score_min',82))}
    except Exception as e: stats['telegram']={'sent':0,'error':str(e)}
    return stats

if __name__=='__main__': print(json.dumps(run_scan(),indent=2,ensure_ascii=False))
