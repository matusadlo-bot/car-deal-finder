from __future__ import annotations
import hashlib, re, time
from datetime import datetime, timezone
from urllib.parse import urljoin
from pathlib import Path
import requests
from bs4 import BeautifulSoup
from .db import connect
from .fx import get_czk_per_eur

BRANDS=['Stihl','Husqvarna','Dolmar','Makita','Echo','Jonsered','Solo','Oleo-Mac','Partner','Homelite','McCulloch','Hecht','Fieldmann','Shindaiwa']
BRAND_RE=re.compile(r'\\b('+'|'.join(re.escape(x) for x in BRANDS)+r')\\b',re.I)
SAW_RE=re.compile(r'\\b(motorov[aá]\\s+p[ií]la|re[tť]azov[aá]\\s+p[ií]la|benz[ií]nov[aá]\\s+p[ií]la|chainsaw|kettens[aä]ge|motorf[uű]r[eé]sz)\\b',re.I)
PART_RE=re.compile(r'\\b(re[tť]az|li[sš]ta|karbur[aá]tor|valec|piest|p[ií]st|spojka|štart[eé]r|starter|kryt|cievka|zapa[lľ]ovanie|n[aá]hradn[eé]\\s+diely|diely\\s+na)\\b',re.I)
BROKEN_LOW=[
    (re.compile(r'bez\\s+iskry|ned[aá]va\\s+iskru',re.I),88,20,90,'bez iskry – často sviečka, fajka, vypínač alebo zapaľovacia cievka','low-medium'),
    (re.compile(r'karbur[aá]tor|membr[aá]n|palivov[aá]\\s+hadi[cč]|nenas[aá]va\\s+benz[ií]n',re.I),90,15,80,'palivová sústava/karburátor – typická opraviteľná závada','low'),
    (re.compile(r'nejde\\s+naštart|neštartuje|nestartuje|zle\\s+štartuje|chyt[ií]\\s+a\\s+zhas',re.I),75,20,160,'neštartuje – môže byť palivo/zapaľovanie; preveriť kompresiu','medium'),
    (re.compile(r'nete[cč]ie\\s+olej|nemaz[ež]|olejov[eé]\\s+[cč]erpadlo',re.I),84,20,110,'mazanie reťaze – často čerpadlo, hadička alebo upchatie','low-medium'),
    (re.compile(r'štart[eé]r|starter|šnúra|sn[uú]ra',re.I),88,15,75,'štartovací mechanizmus – často lacná mechanická oprava','low'),
    (re.compile(r'spojka|brzda\\s+re[tť]aze',re.I),78,25,130,'spojka/brzda reťaze – bežne servisovateľná časť','medium'),
    (re.compile(r'na\\s+opravu|pokazen[aá]|nefunk[cč]n[aá]|nejde\\b',re.I),60,30,220,'všeobecne uvedená ako pokazená/na opravu; treba diagnostiku','medium-high'),
]
HIGH_RISK=re.compile(r'zadret|prasknut.{0,12}(blok|karter|valec)|bez\\s+kompres|slab[aá]\\s+kompres|k[lľ]uk|ložisk.{0,10}k[lľ]uk|piest.{0,10}valec|p[ií]st.{0,10}v[aá]lec',re.I)
MONEY=re.compile(r'([0-9][0-9 .]*)\\s*(Kč|CZK|€|EUR)',re.I)
VIEWS=re.compile(r'(?<!\\d)(\\d{1,3}(?:[ .]\\d{3})*|\\d{1,7})\\s*x\\b',re.I)
DATE=re.compile(r'(?<!\\d)(\\d{1,2})\\.\\s*(\\d{1,2})\\.\\s*(20\\d{2})(?!\\d)')

def _num(s): return int(re.sub(r'\\D','',s))
def _date(text):
    m=DATE.search(text)
    if not m:return None
    try:return datetime(int(m.group(3)),int(m.group(2)),int(m.group(1))).date().isoformat()
    except:return None

def _price(text,cz=False):
    m=MONEY.search(text)
    if not m:return None
    v=float(_num(m.group(1))); cur=m.group(2).upper()
    if cz or cur in {'KČ','CZK'}: return round(v/get_czk_per_eur(),2)
    return v

def _brand(text):
    m=BRAND_RE.search(text or '')
    return m.group(1).title() if m else None

def _complete(title, text):
    t=title or ''; blob=f'{t} {text or ""}'
    has_saw=bool(SAW_RE.search(blob)); has_brand=bool(BRAND_RE.search(blob))
    if PART_RE.search(t) and not SAW_RE.search(t): return False
    return has_saw or (has_brand and not PART_RE.search(t))

def _score(title,desc,price,brand):
    text=f'{title or ""} {desc or ""}'
    if HIGH_RISK.search(text):
        return 28,60,280,'riziko motora/kompresie – môže znamenať valec, piest alebo kľukový mechanizmus','high'
    best=(0,None,None,None,None)
    for pat,sc,mn,mx,reason,risk in BROKEN_LOW:
        if pat.search(text) and sc>best[0]:best=(sc,mn,mx,reason,risk)
    repair=best[0]
    if repair<=0:return 0,None,None,None,None
    brand_bonus=12 if brand and brand.lower() in {'stihl','husqvarna','dolmar','echo','jonsered','shindaiwa'} else 4 if brand else 0
    price_bonus=0
    if price is not None:
        if price<=60:price_bonus=18
        elif price<=120:price_bonus=12
        elif price<=200:price_bonus=6
    opportunity=min(100, repair*0.72+brand_bonus+price_bonus)
    return opportunity,best[1],best[2],best[3],best[4]

def init_chainsaw_db():
    with connect() as con:
        con.execute('''CREATE TABLE IF NOT EXISTS chainsaws (
          source TEXT NOT NULL, source_id TEXT NOT NULL, url TEXT, title TEXT, price_eur REAL, brand TEXT, model TEXT,
          location TEXT, views INTEGER, posted_at TEXT, description TEXT, repair_score REAL, repair_reason TEXT,
          repair_estimate_min_eur REAL, repair_estimate_max_eur REAL, repair_risk TEXT, opportunity_score REAL,
          first_seen TEXT, last_seen TEXT, PRIMARY KEY(source,source_id))''')
        con.execute('CREATE INDEX IF NOT EXISTS idx_chainsaw_score ON chainsaws(opportunity_score DESC)')

def _upsert(d):
    now=datetime.now(timezone.utc).isoformat(); init_chainsaw_db()
    with connect() as con:
        old=con.execute('SELECT first_seen FROM chainsaws WHERE source=? AND source_id=?',(d['source'],d['source_id'])).fetchone()
        d['first_seen']=old['first_seen'] if old else now; d['last_seen']=now
        cols=list(d); vals=[d[c] for c in cols]
        updates=','.join(f'{c}=excluded.{c}' for c in cols if c not in {'source','source_id','first_seen'})
        con.execute(f"INSERT INTO chainsaws ({','.join(cols)}) VALUES ({','.join('?' for _ in cols)}) ON CONFLICT(source,source_id) DO UPDATE SET {updates}",vals)

def _detail(session,url,ua):
    try:
        r=session.get(url,headers={'User-Agent':ua},timeout=18); r.raise_for_status(); soup=BeautifulSoup(r.text,'lxml')
        # Bazos detail description is usually in main text area; fallback to body text.
        for sel in ['.popisdetail','.detail','.inzeratydetail','.maincontent']:
            el=soup.select_one(sel)
            if el:
                tx=' '.join(el.get_text(' ',strip=True).split())
                if len(tx)>40:return tx[:7000]
        return ' '.join(soup.get_text(' ',strip=True).split())[:7000]
    except:return ''

def scan_chainsaws(cfg,mode='quick'):
    init_chainsaw_db(); cc=cfg.get('chainsaws',{}); ua='Mozilla/5.0 (Windows NT 10.0; Win64; x64) CarDealFinder/0.5'
    delay=float(cfg.get('request_delay_seconds',1.1)); pages=int(cc.get('deep_pages',35) if mode=='deep' else cc.get('quick_pages',8))
    sources=cc.get('sources',{})
    stats={}; session=requests.Session()
    for source,urls in sources.items():
        saved=0; err=None; cz=source.endswith('_cz')
        try:
            for base in urls:
                for page in range(pages):
                    url=base if page==0 else base.rstrip('/')+f'/{page*20}/'
                    r=session.get(url,headers={'User-Agent':ua,'Accept-Language':'sk,cs;q=0.9'},timeout=25); r.raise_for_status(); soup=BeautifulSoup(r.text,'lxml')
                    for root in soup.select('div.inzeraty'):
                        a=root.select_one('.inzeratynadpis h2 a[href], h2 a[href], .inzeratynadpis a[href]')
                        if not a:continue
                        href=urljoin(r.url,a.get('href','')); title=a.get_text(' ',strip=True); text=' '.join(root.get_text(' ',strip=True).split())
                        if not title or not _complete(title,text):continue
                        sidm=re.search(r'/inzerat/(\\d+)',href); sid=sidm.group(1) if sidm else hashlib.sha1(href.encode()).hexdigest()[:16]
                        price=_price(text,cz); brand=_brand(f'{title} {text}')
                        # Fetch detail only for likely broken/cheap/known-brand candidates.
                        detail=''
                        if any(p.search(text) for p,*_ in BROKEN_LOW) or HIGH_RISK.search(text) or (price is not None and price<=220):
                            detail=_detail(session,href,ua); time.sleep(min(delay,0.5))
                        blob=f'{text} {detail}'
                        opp,mn,mx,reason,risk=_score(title,blob,price,brand)
                        if opp<=0:continue  # user asked specifically for broken saws to repair
                        locel=root.select_one('.inzeratylok, .inzeratylokalita'); loc=' '.join(locel.get_text(' ',strip=True).split()) if locel else None
                        vm=VIEWS.search(text); views=_num(vm.group(1)) if vm else None
                        _upsert(dict(source=source,source_id=str(sid),url=href,title=title,price_eur=price,brand=brand,model=None,location=loc,views=views,posted_at=_date(text),description=blob[:8000],repair_score=float(opp),repair_reason=reason,repair_estimate_min_eur=mn,repair_estimate_max_eur=mx,repair_risk=risk,opportunity_score=float(opp),first_seen=None,last_seen=None))
                        saved+=1
                    time.sleep(delay)
        except Exception as e:err=f'{type(e).__name__}: {e}'
        stats[source]={'saved':saved,'error':err}
    return stats
