from __future__ import annotations
import re
from .models import Listing

# Hard negatives: these are overwhelmingly parts/accessories rather than whole cars.
PARTS_RE = re.compile(
    r'\b(?:alu\s*disk|disky|disky\s*r|elektr[oó]ny|pneu(?:matik)?|pneumatiky|koles[aá]|sada\s*kolies|'
    r'n[aá]razn[ií]k|svetl[oá]|dvere|kapota|blatn[ií]k|sedadl[aá]|seda[cč]ky|interi[eé]r\s+na\s+predaj|'
    r'prevodovka\s*(?:na\s*predaj)?|motor\s*(?:na\s*predaj|kompletn[yý])|turbo\s*(?:na\s*predaj)?|'
    r'dpf\s*(?:filter)?|egr\s*(?:ventil)?|n[aá]prava|tlmi[cč]e|pru[zž]iny|spojka\s*(?:sada)?|'
    r'spoiler|maska|zrkadlo|riadiaca\s+jednotka|ecu|autor[aá]dio|stre[sš]n[yý]\s+box|'
    r'na\s+n[aá]hradn[eé]\s+diely|pouze\s+d[ií]ly|n[aá]hradn[ií]\s+d[ií]ly)\b', re.I)

VEHICLE_WORDS = re.compile(r'\b(?:auto|vozidlo|automobil|osobn[eé]\s+auto|kombi|sedan|limuz[ií]na|hatchback|suv|cabrio|roadster|coupe|kup[eé])\b', re.I)


def classify_vehicle(x: Listing) -> tuple[bool, float, str | None]:
    title=(x.title or '').strip(); desc=(x.description or '').strip(); blob=f'{title} {desc}'
    # Very low prices plus parts words are almost certainly not a complete vehicle.
    if PARTS_RE.search(title):
        return False, 0.05, 'názov vyzerá ako diel/kolesá/príslušenstvo'
    # A complete-car listing usually has make/model or explicit vehicle language.
    score=0.0
    if x.make: score += 0.35
    if x.model: score += 0.25
    if x.year: score += 0.12
    if x.mileage_km: score += 0.12
    if VEHICLE_WORDS.search(blob): score += 0.08
    if x.price_eur and x.price_eur >= 500: score += 0.08
    # Parts mentions in description are tolerated unless the title itself says parts.
    if PARTS_RE.search(desc) and not (x.make and x.model): score -= 0.25
    score=max(0.0,min(1.0,score))
    return score >= 0.55, score, None if score >= 0.55 else 'málo dôkazov, že ide o celé auto'
