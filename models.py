from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Optional

@dataclass
class Listing:
    source: str
    source_id: str
    url: str
    title: str
    price_eur: Optional[float] = None
    price_original: Optional[float] = None
    currency: Optional[str] = None
    make: Optional[str] = None
    model: Optional[str] = None
    year: Optional[int] = None
    mileage_km: Optional[int] = None
    power_kw: Optional[int] = None
    fuel: Optional[str] = None
    transmission: Optional[str] = None
    drive: Optional[str] = None
    body_style: Optional[str] = None
    engine_signature: Optional[str] = None
    variant_signature: Optional[str] = None
    location: Optional[str] = None
    views: Optional[int] = None
    posted_at: Optional[str] = None
    seller_type: Optional[str] = None
    description: Optional[str] = None
    first_seen: Optional[str] = None
    last_seen: Optional[str] = None
    deal_score: Optional[float] = None
    market_price_eur: Optional[float] = None
    discount_pct: Optional[float] = None
    peer_count: Optional[int] = None
    special_score: Optional[float] = None
    scarcity_score: Optional[float] = None
    hidden_gem_score: Optional[float] = None
    rare_score: Optional[float] = None
    rare_reason: Optional[str] = None
    repair_score: Optional[float] = None
    repair_reason: Optional[str] = None
    repair_estimate_min_eur: Optional[float] = None
    repair_estimate_max_eur: Optional[float] = None
    repair_risk: Optional[str] = None
    repair_margin_eur: Optional[float] = None
    opportunity_score: Optional[float] = None
    interesting_score: Optional[float] = None
    interesting_reason: Optional[str] = None
    local_tags: Optional[str] = None
    detail_fetched_at: Optional[str] = None
    ai_note: Optional[str] = None
    ai_last_analyzed: Optional[str] = None
    is_vehicle: Optional[int] = None
    vehicle_confidence: Optional[float] = None
    vehicle_reject_reason: Optional[str] = None

    def to_dict(self):
        return asdict(self)
