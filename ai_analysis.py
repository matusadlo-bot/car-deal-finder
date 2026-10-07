from __future__ import annotations
import json, os, re
from datetime import datetime, timezone
from .db import connect


def _extract_json(text:str):
    text=(text or '').strip(); m=re.search(r'\{.*\}',text,re.S)
    if not m: return None
    try: return json.loads(m.group(0))
    except Exception: return None


def analyze_candidates(limit:int=12):
    key=os.getenv('OPENAI_API_KEY','').strip()
    if not key: return {'analyzed':0,'status':'OPENAI_API_KEY nie je nastavený – všetky inzeráty sa stále analyzujú lokálnym scoringom.'}
    model=os.getenv('OPENAI_MODEL','').strip()
    if not model: return {'analyzed':0,'status':'OPENAI_MODEL nie je nastavený. Zadaj model dostupný v tvojom API účte.'}
    try:
        from openai import OpenAI
    except Exception as e:
        return {'analyzed':0,'status':f'OpenAI knižnica nie je dostupná: {e}'}
    client=OpenAI(api_key=key)
    mode=os.getenv('AI_ANALYSIS_MODE','top').strip().lower()
    with connect() as con:
        if mode=='all':
            sql='''SELECT * FROM listings WHERE (ai_last_analyzed IS NULL OR ai_last_analyzed < last_seen)
                   ORDER BY COALESCE(interesting_score,0) DESC LIMIT ?'''
            effective=max(1,min(int(os.getenv('AI_MAX_PER_SCAN','100')),1000))
            rows=con.execute(sql,(effective,)).fetchall()
        else:
            sql='''SELECT * FROM listings WHERE (COALESCE(interesting_score,0)>=35 OR COALESCE(special_score,0)>=25 OR COALESCE(deal_score,0)>=55 OR COALESCE(repair_score,0)>=35)
                   AND (ai_last_analyzed IS NULL OR ai_last_analyzed < last_seen)
                   ORDER BY COALESCE(interesting_score,0) DESC LIMIT ?'''
            rows=con.execute(sql,(limit,)).fetchall()
        done=0
        for r in rows:
            prompt=f'''You are screening a used-car classified ad for an enthusiast buyer who wants underpriced, overlooked, unusual or cheaply repairable cars.
Do NOT rely on a whitelist of famous models. Judge the specific configuration in the ad.
Look for: unusual engine/body/trim/colour/interior, limited or obscure editions, homologation/performance links, government/diplomatic/armoured provenance, unusually original or low-mileage older cars, rare factory options, seller under-describing the specification, and faults that may be cheap relative to the car value.
Be extremely conservative. We want cars that make an enthusiast say "wow", not ordinary trims. RS, GTI, AMG, M Sport, S-line, leather, alloy wheels or a normal coupe/cabrio alone are NOT rare. A high rare_score needs concrete evidence such as an obscure factory edition, genuinely unusual engine/body combination, coachbuilt/armoured/government provenance, very unusual factory colour/interior, homologation link, exceptional originality/low mileage for an older car, or another clearly defensible special configuration. Rarity alone is not desirability. Vague no-start, engine, gearbox, crash/flood and complex electrical faults are high risk.
Return ONLY valid JSON with keys:
rare_score (0-100), rare_reason (short), hidden_gem_score (0-100), repair_opportunity_score (0-100), repair_cost_min_eur (number or null), repair_cost_max_eur (number or null), repair_risk (low/medium/high/very high), note (max 2 sentences).
TITLE: {r['title']}
MAKE/MODEL: {r['make']} {r['model']}
PRICE EUR: {r['price_eur']}  MARKET ESTIMATE: {r['market_price_eur']}
YEAR: {r['year']}  KM: {r['mileage_km']}  POWER KW: {r['power_kw']}
BODY: {r['body_style']}  ENGINE: {r['engine_signature']}
SOURCE: {r['source']}
TEXT: {(r['description'] or '')[:9000]}'''
            try:
                resp=client.responses.create(model=model,input=prompt)
                obj=_extract_json(resp.output_text or '')
                if not obj: continue
                rare=max(float(r['rare_score'] or 0),float(obj.get('rare_score') or 0))
                hidden=max(float(r['hidden_gem_score'] or 0),float(obj.get('hidden_gem_score') or 0))
                repair=max(float(r['repair_score'] or 0),float(obj.get('repair_opportunity_score') or 0))
                note=obj.get('note') or ''
                rr=obj.get('rare_reason') or r['rare_reason']
                risk=obj.get('repair_risk') or r['repair_risk']
                cmin=obj.get('repair_cost_min_eur') if obj.get('repair_cost_min_eur') is not None else r['repair_estimate_min_eur']
                cmax=obj.get('repair_cost_max_eur') if obj.get('repair_cost_max_eur') is not None else r['repair_estimate_max_eur']
                with connect() as con2:
                    con2.execute('''UPDATE listings SET rare_score=?,rare_reason=COALESCE(?,rare_reason),hidden_gem_score=?,repair_score=?,repair_estimate_min_eur=?,repair_estimate_max_eur=?,repair_risk=?,ai_note=?,ai_last_analyzed=? WHERE source=? AND source_id=?''',
                                 (round(rare,1),rr,round(hidden,1),round(repair,1),cmin,cmax,risk,note,datetime.now(timezone.utc).isoformat(),r['source'],r['source_id']))
                done+=1
            except Exception as e:
                return {'analyzed':done,'status':f'AI analýza sa zastavila: {type(e).__name__}: {e}'}
    return {'analyzed':done,'status':'OK'}
