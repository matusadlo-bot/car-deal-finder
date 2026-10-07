from __future__ import annotations
import re
from .models import Listing

MAKES = [
    'Mercedes-Benz','Alfa Romeo','Land Rover','Aston Martin','Rolls-Royce','Volkswagen','Škoda','Skoda','BMW','Mercedes','Audi','VW','Seat','Cupra',
    'Porsche','Volvo','Toyota','Lexus','Ford','Opel','Peugeot','Citroen','Citroën','Renault','Dacia','Kia','Hyundai','Honda','Mazda','Nissan','Tesla',
    'Fiat','Jaguar','Mini','Suzuki','Mitsubishi','Subaru','Jeep','Chevrolet','Ferrari','Lamborghini','Maserati','Bentley','Saab','Lancia','Alpina',
    'Abarth','Dodge','Chrysler','Cadillac','Buick','Pontiac','Rover','MG','Lotus','McLaren','Smart','SsangYong','KGM','Infiniti','Genesis','Polestar',
    'Daihatsu','Isuzu','Lada','Trabant','Wartburg','Zastava','Tatra','Moskvich','Daewoo','Maybach','GMC','Hummer','Alpine'
]
PRICE_RE = re.compile(r'(?<!\d)(\d{1,3}(?:[ .]\d{3})+|\d{4,7})(?:[,.]\d{1,2})?\s*(?:€|EUR)', re.I)
KM_RE = re.compile(r'(?<!\d)(\d{1,3}(?:[ .]\d{3})+|\d{4,7})\s*(?:km|kilomet)', re.I)
KW_RE = re.compile(r'(?<!\d)(\d{2,3})\s*kW\b', re.I)
HP_RE = re.compile(r'(?<!\d)(\d{2,4})\s*(?:hp|ps|koni|koní|km\b|le\b)', re.I)
EXPLICIT_YEAR = [re.compile(r'(?:rok\s*(?:výroby|vyroby)?|r\.?\s*v\.?|rv|modelový\s*rok|modelovy\s*rok|datum\s*výroby|datum\s*vyroby|do\s*provozu|prv(?:á|a|ní|ni)\s*registr(?:ácia|acia|ace)|évjárat)\s*[:\-]?\s*(?:\d{1,2}[/.])?\s*(19[7-9]\d|20[0-2]\d)',re.I)]
TITLE_YEAR=re.compile(r'(?<!\d)(19[7-9]\d|20[0-2]\d)(?!\d)')
BODY_PATTERNS=[
    ('cabrio',re.compile(r'\b(cabrio|cabriolet|convertible|kabrio|kabriolet|roadster|spyder|spider)\b',re.I)),
    ('coupe',re.compile(r'\b(coup[eé]|kup[eé]|fastback)\b',re.I)),
    ('targa',re.compile(r'\b(targa)\b',re.I)),
    ('shooting_brake',re.compile(r'\b(shooting\s*brake)\b',re.I)),
    ('wagon',re.compile(r'\b(kombi|touring|avant|variant|estate|wagon|break)\b',re.I)),
    ('suv',re.compile(r'\b(suv|offroad|gel[aä]ndewagen)\b',re.I)),
    ('pickup',re.compile(r'\b(pick[ -]?up)\b',re.I)),
    ('van',re.compile(r'\b(van|minivan|mpv)\b',re.I)),
]

def _num(s: str) -> int: return int(re.sub(r'\D', '', s))
def _canonical_make(make: str) -> str:
    m=make.strip()
    if m.lower()=='mercedes': return 'Mercedes-Benz'
    if m.lower()=='vw': return 'Volkswagen'
    if m.lower()=='skoda': return 'Škoda'
    return m

def _engine_signature(text:str, power_kw:int|None):
    low=text.lower()
    cyl=None
    m=re.search(r'\b(w12|v12|v10|v8|v6|vr6|vr5|i6|r6|i5|r5|v5|v4|boxer|wankel|rotary)\b',low,re.I)
    if m: cyl=m.group(1).upper()
    disp=None
    for pat in [r'\b([0-6][.,]\d)\s*(?:tdi|tsi|tfsi|fsi|mpi|cdi|hdi|dci|turbo|biturbo|twin.?turbo|i\b|d\b)?',r'\b(\d{3,4})\s*cm[³3]\b']:
        m=re.search(pat,low,re.I)
        if m:
            disp=m.group(1).replace(',','.')
            if 'cm' in m.group(0):
                try: disp=f'{int(disp)/1000:.1f}'
                except: pass
            break
    tech=[]
    for token in ['tdi','tsi','tfsi','fsi','mpi','cdi','hdi','dci','gti','gtd','turbo','biturbo','kompressor','hybrid','phev','ev']:
        if re.search(rf'\b{re.escape(token)}\b',low): tech.append(token.upper())
    parts=[p for p in [cyl,disp,tech[0] if tech else None, f'{power_kw}kW' if power_kw else None] if p]
    return ' '.join(parts)[:60] if parts else None

def normalize_listing(x: Listing) -> Listing:
    title=x.title or ''; desc=x.description or ''; text=' '.join(filter(None,[title,desc]))
    if x.price_eur is None:
        m=PRICE_RE.search(text)
        if m: x.price_eur=float(_num(m.group(1)))
    if x.mileage_km is None:
        m=KM_RE.search(text)
        if m: x.mileage_km=_num(m.group(1))
    if x.year is None:
        found=None
        for pat in EXPLICIT_YEAR:
            m=pat.search(text)
            if m: found=int(m.group(1)); break
        if found is None:
            ys=[int(y) for y in TITLE_YEAR.findall(title)]
            if ys: found=max(ys)
        x.year=found
    if x.power_kw is None:
        m=KW_RE.search(text)
        if m: x.power_kw=int(m.group(1))
        else:
            hm=HP_RE.search(text)
            if hm:
                hp=int(hm.group(1))
                if 30<=hp<=1600: x.power_kw=round(hp*0.735499)
    if not x.make:
        low=text.lower()
        for make in MAKES:
            if re.search(r'(?<![a-z0-9])'+re.escape(make.lower())+r'(?![a-z0-9])',low):
                x.make=_canonical_make(make); break
    if x.make: x.make=_canonical_make(x.make)
    if x.make and not x.model:
        t=title.replace('Mercedes Benz','Mercedes-Benz'); low=t.lower(); mk=x.make.lower()
        variants=[mk, 'mercedes' if mk=='mercedes-benz' else mk, 'vw' if mk=='volkswagen' else mk, 'skoda' if mk=='škoda' else mk]
        pos=-1; used=''
        for v in variants:
            pos=low.find(v)
            if pos>=0: used=v; break
        if pos>=0:
            tail=t[pos+len(used):].strip(' :-–—'); toks=re.findall(r'[A-Za-zÀ-ž0-9.+-]+',tail)
            stop={'predam','prodám','predaj','prodej','na','for','sale','rok','r.v','rv'}
            toks=[z for z in toks if z.lower() not in stop]
            if toks:
                if toks[0].lower() in ('rad','řada','rada','series') and len(toks)>1: x.model=f'{toks[0]} {toks[1]}'[:40]
                else: x.model=toks[0][:40]
    low=text.lower()
    if not x.fuel:
        if any(k in low for k in ['diesel','nafta','tdi','dci','hdi','cdi']): x.fuel='diesel'
        elif any(k in low for k in ['benzín','benzin','petrol','benzina','tsi','tfsi','mpi','fsi']): x.fuel='petrol'
        elif any(k in low for k in ['electric','elektro','bev','e-tron']): x.fuel='electric'
        elif any(k in low for k in ['hybrid','hibrid','phev']): x.fuel='hybrid'
    if not x.transmission:
        if any(k in low for k in ['automat','dsg','steptronic','s-tronic','tiptronic','automatic','automata']): x.transmission='automatic'
        elif any(k in low for k in ['manual','manuál','manualna','manuální','kézi']): x.transmission='manual'
    if not x.drive and any(k in low for k in ['xdrive','quattro','4matic','4x4','awd','4motion','allrad']): x.drive='awd'
    if not x.body_style:
        for body,pat in BODY_PATTERNS:
            if pat.search(text): x.body_style=body; break
    x.engine_signature=x.engine_signature or _engine_signature(text,x.power_kw)
    return x
