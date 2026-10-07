from __future__ import annotations
import re
from .models import Listing

# These are generic rarity/enthusiast signals, not a hard-coded list of exact car models.
SPECIAL_SIGNALS = [
    ('limited/special edition', 34, re.compile(r'\b(limited|edition|special\s*edition|anniversary|jubilee|heritage|final\s*edition|launch\s*edition|numbered|\d+\s*/\s*\d+)\b',re.I)),
    ('factory individualisation', 38, re.compile(r'\b(individual|designo|manufaktur|exclusive\s*line|exclusive\s*series|bespoke|tailor\s*made|atelier|sondermodell)\b',re.I)),
    ('unusual colour/interior', 36, re.compile(r'\b(harlekin|harlequin|color\s*concept|factory\s*two.?tone|mramor|marble|granit|granite|one[- ]off\s*interior|unik[aá]tny\s*interi[eé]r)\b',re.I)),
    ('performance/halo trim', 18, re.compile(r'\b(clubsport|competition|competizione|trophy|cup|sportline|type\s*r|sti|evo|nismo|quadrifoglio|gta|black\s*series|csl|gts|rs[346q]?\b)\b',re.I)),
    ('rare engine layout', 40, re.compile(r'\b(w12|v12|v10|v8|vr6|vr5|v5|i5|r5|five.?cylinder|5.?cylinder|wankel|rotary)\b',re.I)),
    ('interesting body style', 14, re.compile(r'\b(cabrio|cabriolet|convertible|kabrio|roadster|spyder|spider|targa|shooting\s*brake|coupe|coup[eé])\b',re.I)),
    ('homologation/rally/race link', 45, re.compile(r'\b(homologation|homologa[cč]|rallye?|rally|group\s*[ab]|gruppe\s*[ab]|motorsport|track\s*edition|lightweight|superleggera)\b',re.I)),
    ('government/diplomatic provenance', 42, re.compile(r'\b(vl[aá]dn|prezidentsk|ministersk|diplomat|ambas[aá]d|embassy|government|ministerial|regierungsfahrzeug|diplomatic|armou?red|pancier|gepanzert)\w*\b',re.I)),
    ('coachbuilt/special conversion', 42, re.compile(r'\b(coachbuilt|karos[aá]r|coachwork|hearse|pohrebn|landaulet|limousine\s*conversion|stretch|6x6|camper\s*conversion)\b',re.I)),
    ('original low-mileage classic cues', 20, re.compile(r'\b(original\s*(paint|lak|zustand|state)|first\s*owner|prv[ýy]\s*majite[lľ]|garaged|garage\s*kept|untouched|unrestored|neprelak|p[oô]vodn[ýy]\s*lak)\b',re.I)),
]

REPAIR_RULES = [
    (re.compile(r'\b(baterk\w*|akumul[aá]tor\w*)\b.*\b(slab|vybit|mrtv|nefunk|tot|kaputt)',re.I), 82, 80, 350, 'Pravdepodobne 12 V batéria/napájanie – často lokálna a lacnejšia oprava.', 'medium'),
    (re.compile(r'\b(altern[aá]tor|dob[ií]j\w*|lichtmaschine)\b',re.I), 72, 180, 700, 'Možný problém dobíjania/alternátora. Treba zmerať nabíjanie.', 'medium'),
    (re.compile(r'\b(start[eé]r|štart[eé]r|starter|anlasser)\b',re.I), 72, 150, 650, 'Možný štartér alebo jeho napájanie – často lokálna opraviteľná závada.', 'medium'),
    (re.compile(r'\b(senzor|sn[ií]ma[čc]|čidlo|cidlo|sensor)\b.*\b(chyb|nefunk|sviet|kontrolk|fehler|defekt)',re.I), 74, 50, 500, 'Inzerát spomína snímač/senzor. Môže ísť o relatívne lacnú opravu, diagnostika je nutná.', 'medium'),
    (re.compile(r'\b(nejde\s*okno|stahova[čc]k|sťahova[čc]k|fensterheber|central\w*\s*zamyk|zentralverriegelung)\b',re.I), 78, 60, 450, 'Komfortná elektrika – často mechanizmus, kabeláž alebo spínač.', 'low-medium'),
    (re.compile(r'\b(klimatiz\w*|klima|air\s*condition)\b.*\b(nefung|nejde|defekt|kaputt|fehler)\b',re.I), 55, 80, 1400, 'Nefunkčná klimatizácia môže byť drobnosť aj kompresor; treba tlakovú skúšku.', 'high'),
    (re.compile(r'\b(egr|agr)\b.*\b(chyb|nefunk|problem|probl[eé]m|fehler|defekt)\b',re.I), 50, 150, 1000, 'EGR/AGR môže byť čistenie alebo ventil, ale príčina môže byť širšia.', 'high'),
    (re.compile(r'\bdpf\b.*\b(chyb|upchat|ucpat|problem|probl[eé]m|fehler|verstopft)\b',re.I), 42, 150, 1900, 'DPF môže byť senzor/regenerácia, ale aj drahšia výmena. Bez diagnostiky vyššie riziko.', 'high'),
    (re.compile(r'\b(nepojazd|nepojízd|nejde\s*nastart|motor\s*klep|motorschaden|getriebeschaden|prevodovk\w*\s*(chyba|nefung|ko)|unfall|hav[aá]ri|flood|wasser)\b',re.I), 14, 700, 8000, 'Vážna alebo nejasná závada. Nízke skóre ľahkej opravy – kupovať iba po diagnostike.', 'very high'),
]

DISTINCTIVE_TOKEN_RE = re.compile(r'\b(?:limited|edition|anniversary|jubilee|heritage|individual|designo|manufaktur|harlekin|harlequin|clubsport|competition|competizione|trophy|type\s*r|sti|evo|nismo|quadrifoglio|gta|black\s*series|csl|gts|w12|v12|v10|v8|vr6|vr5|i5|r5|roadster|cabrio|cabriolet|convertible|targa|shooting\s*brake|coupe|coup[eé]|homologation|rallye?|diplomat\w*|government|embassy|armou?red|pancier\w*|gepanzert)\b',re.I)

def _dedupe(seq):
    out=[]
    for x in seq:
        if x and x not in out: out.append(x)
    return out

def enrich_opportunity(x: Listing) -> Listing:
    title=x.title or ''; desc=x.description or ''; text=' '.join(filter(None,[title,desc]))
    tags=[]; reasons=[]; special=0.0
    for label,weight,pat in SPECIAL_SIGNALS:
        if pat.search(text):
            tags.append(label); reasons.append(label); special += weight
    # Older, low-mileage cars are interesting even without a famous badge.
    if x.year and x.mileage_km and x.year <= 2005:
        age=max(0,2026-x.year)
        expected=max(1,age*9000)
        if x.mileage_km < expected*0.45:
            special += 18; tags.append('low-mileage older car'); reasons.append('nezvyčajne nízky nájazd na vek')
    x.special_score=min(100.0,special)

    title_tokens={m.group(0).lower() for m in DISTINCTIVE_TOKEN_RE.finditer(title)}
    all_tokens={m.group(0).lower() for m in DISTINCTIVE_TOKEN_RE.finditer(text)}
    hidden=all_tokens-title_tokens
    if hidden:
        x.hidden_gem_score=min(100.0,52.0+10.0*len(hidden))
        tags.append('hidden spec in description')
    else:
        x.hidden_gem_score=0.0

    rb=(0,None,None,None,None)
    for pat,score,cmin,cmax,reason,risk in REPAIR_RULES:
        if pat.search(text) and score>rb[0]: rb=(score,reason,cmin,cmax,risk)
    x.repair_score=float(rb[0]); x.repair_reason=rb[1]; x.repair_estimate_min_eur=rb[2]; x.repair_estimate_max_eur=rb[3]; x.repair_risk=rb[4]

    # Variant signature is intentionally generic. Scarcity is calculated later from the database.
    sig=[]
    if x.make: sig.append(x.make.lower())
    if x.model: sig.append(x.model.lower())
    if x.engine_signature: sig.append(x.engine_signature.lower())
    if x.body_style: sig.append(x.body_style.lower())
    for tok in sorted(all_tokens)[:4]: sig.append(tok)
    x.variant_signature=' | '.join(_dedupe(sig))[:220] if sig else None
    x.local_tags=', '.join(_dedupe(tags))[:500] if tags else None
    x.rare_score=x.special_score
    x.rare_reason=('; '.join(_dedupe(reasons))[:700] if reasons else None)
    x.opportunity_score=max(x.special_score or 0,x.repair_score or 0,x.hidden_gem_score or 0)
    x.interesting_score=x.opportunity_score
    x.interesting_reason=x.rare_reason or x.repair_reason
    return x
