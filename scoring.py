from __future__ import annotations
import math, statistics
from collections import Counter, defaultdict
from .db import connect

def _norm(v): return (v or '').strip().lower()
def _clamp(v,lo=0.0,hi=100.0): return max(lo,min(hi,float(v)))

def _distance(r,p):
    # Price peers must be genuinely comparable. No make/model mismatch allowed.
    if not r['make'] or not p['make'] or _norm(r['make']) != _norm(p['make']): return None
    if not r['model'] or not p['model'] or _norm(r['model']) != _norm(p['model']): return None
    d=0.0
    if r['year'] and p['year']:
        gap=abs(int(r['year'])-int(p['year']))
        if gap>3: return None
        d += gap*2.2
    elif bool(r['year']) != bool(p['year']): d += 3.0
    if r['mileage_km'] and p['mileage_km']:
        gap=abs(int(r['mileage_km'])-int(p['mileage_km']))
        if gap>90000: return None
        d += gap/18000.0
    elif bool(r['mileage_km']) != bool(p['mileage_km']): d += 2.5
    if r['fuel'] and p['fuel'] and r['fuel']!=p['fuel']: return None
    if r['body_style'] and p['body_style'] and r['body_style']!=p['body_style']: d += 2.5
    if r['drive'] and p['drive'] and r['drive']!=p['drive']: d += 2.5
    if r['power_kw'] and p['power_kw']:
        gap=abs(int(r['power_kw'])-int(p['power_kw']))
        if gap>55: return None
        d += gap/10.0
    if r['engine_signature'] and p['engine_signature'] and _norm(r['engine_signature'])!=_norm(p['engine_signature']): d += 3.5
    return d

def rescore_all():
    with connect() as con:
        rows=con.execute('''SELECT * FROM listings
                            WHERE COALESCE(is_vehicle,1)=1 AND price_eur BETWEEN 500 AND 1000000''').fetchall()
        cohort=defaultdict(list); variant_counts=Counter()
        for r in rows:
            make=_norm(r['make']); model=_norm(r['model'])
            if make and model: cohort[(make,model)].append(r)
            if make and model and r['variant_signature']:
                variant_counts[(make,model,_norm(r['variant_signature']))]+=1

        updates=[]
        for r in rows:
            # ----- conservative market/deal model -----
            candidates=[]
            for p in rows:
                if p['source']==r['source'] and p['source_id']==r['source_id']: continue
                if not p['price_eur']: continue
                d=_distance(r,p)
                if d is None or d>12.0: continue
                candidates.append((d,float(p['price_eur'])))
            candidates.sort(key=lambda z:z[0]); nearest=candidates[:45]
            deal=None; med=None; discount=None; pc=len(nearest)
            # Minimum 8 strong peers. Five was far too permissive and created false deals.
            if len(nearest)>=8:
                prices=[v for _,v in nearest]
                med0=statistics.median(prices)
                prices=[v for v in prices if 0.62*med0<=v<=1.55*med0]
                if len(prices)>=8:
                    med=statistics.median(prices); pc=len(prices)
                    discount=(med-float(r['price_eur']))/med*100.0
                    # Below 8% discount = no meaningful deal. 15-20%+ starts to become strong.
                    effective=max(0.0,discount-7.0)
                    evidence=min(10.0,math.log2(pc)*2.0)
                    deal=_clamp(effective*4.25 + evidence)
                    if discount < 8: deal=min(deal,18)
                    if discount < 12: deal=min(deal,42)

            # ----- scarcity: never enough by itself -----
            make=_norm(r['make']); model=_norm(r['model']); sig=_norm(r['variant_signature'])
            group=cohort.get((make,model),[]) if make and model else []
            scarcity=0.0
            if sig and len(group)>=12:
                n=variant_counts[(make,model,sig)]; share=n/max(1,len(group))
                scarcity=_clamp(100.0-share*150.0)
                if n<=2 and len(group)>=20: scarcity=max(scarcity,90)
                elif n<=3 and len(group)>=15: scarcity=max(scarcity,82)

            special=float(r['special_score'] or 0); hidden=float(r['hidden_gem_score'] or 0); repair=float(r['repair_score'] or 0); dscore=float(deal or 0)
            # Ordinary trim rarity must not become a "wow" rare car. We require explicit special evidence.
            rare=0.0
            if special>=55:
                rare=_clamp(special*0.86 + scarcity*0.26 + hidden*0.12)
            elif special>=30 and scarcity>=85:
                rare=_clamp(special*0.70 + scarcity*0.42 + hidden*0.10)
            elif hidden>=75 and special>=22 and scarcity>=75:
                rare=_clamp(hidden*0.30 + special*0.55 + scarcity*0.30)

            repair_margin=None
            if med and r['price_eur'] is not None and r['repair_estimate_max_eur'] is not None:
                repair_margin=float(med)-float(r['price_eur'])-float(r['repair_estimate_max_eur'])

            # Main section is intentionally sparse: only strong evidence gets a high score.
            collector=_clamp(max(0,rare-35)*1.35 + max(0,dscore-45)*0.30)
            bargain=_clamp(max(0,dscore-35)*1.45 + max(0,rare-55)*0.15)
            fixer=_clamp(max(0,repair-45)*1.10 + max(0,dscore-40)*0.85) if repair>=45 else 0
            interesting=max(collector,bargain,fixer)
            views=r['views']
            if interesting>=50 and views is not None:
                if views<=50: interesting=min(100,interesting+4)
                elif views<=150: interesting=min(100,interesting+2)

            reasons=[]
            if discount is not None and dscore>=55: reasons.append(f'{discount:.0f}% pod mediánom {pc} porovnateľných áut')
            if rare>=60:
                if r['rare_reason']: reasons.append(str(r['rare_reason']))
                if scarcity>=82: reasons.append(f'konfigurácia sa vyskytuje veľmi zriedka (scarcity {scarcity:.0f}/100)')
            if hidden>=75 and rare>=55: reasons.append('dôležitá špecifikácia je skrytá v texte inzerátu')
            if repair>=55 and r['repair_reason']: reasons.append(str(r['repair_reason']))
            reason='; '.join(dict.fromkeys(reasons))[:900] if reasons else None
            opportunity=max(dscore,rare,fixer)
            updates.append((round(deal,1) if deal is not None else None,round(med,0) if med else None,round(discount,1) if discount is not None else None,pc,
                            round(scarcity,1),round(rare,1),round(repair_margin,0) if repair_margin is not None else None,round(opportunity,1),round(interesting,1),reason,
                            r['source'],r['source_id']))
        con.executemany('''UPDATE listings SET deal_score=?,market_price_eur=?,discount_pct=?,peer_count=?,scarcity_score=?,rare_score=?,repair_margin_eur=?,
                            opportunity_score=?,interesting_score=?,interesting_reason=? WHERE source=? AND source_id=?''',updates)
