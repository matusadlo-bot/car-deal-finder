from __future__ import annotations
import os, requests
from .db import connect

def _fmt(v,suffix=''):
    try: return f'{float(v):.0f}{suffix}'
    except: return '—'

def send_telegram_new_deals(min_score=82):
    token=os.getenv('TELEGRAM_BOT_TOKEN'); chat=os.getenv('TELEGRAM_CHAT_ID')
    if not token or not chat: return 0
    with connect() as con:
        rows=con.execute('''SELECT * FROM listings WHERE COALESCE(interesting_score,0)>=?
            AND datetime(first_seen)>=datetime('now','-75 minutes') ORDER BY interesting_score DESC LIMIT 20''',(min_score,)).fetchall()
    sent=0
    for r in rows:
        reason=r['interesting_reason'] or r['rare_reason'] or r['repair_reason'] or ''
        msg=(f"⭐ NÁLEZ {float(r['interesting_score'] or 0):.0f}/100\n{r['title']}\n"
             f"Cena: {_fmt(r['price_eur'],' €')} | Deal {_fmt(r['deal_score'])} | Rare {_fmt(r['rare_score'])}\n"
             f"Trh: {_fmt(r['market_price_eur'],' €')} | Pod trhom: {_fmt(r['discount_pct'],'%')}\n"
             f"{reason[:350]}\n{r['url']}")
        resp=requests.post(f'https://api.telegram.org/bot{token}/sendMessage',json={'chat_id':chat,'text':msg,'disable_web_page_preview':True},timeout=15)
        if resp.ok: sent+=1
    return sent
