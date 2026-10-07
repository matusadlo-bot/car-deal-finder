from __future__ import annotations

import json
import math
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from car_deal_finder.db import init_db
from car_deal_finder.chainsaws import init_chainsaw_db

ROOT = Path(__file__).resolve().parent
DB = ROOT / "cars.db"
OUT = ROOT / "docs" / "data" / "results.json"
SCAN = ROOT / "last_cloud_scan.json"

CAR_FIELDS = [
    "source", "source_id", "url", "title", "price_eur", "market_price_eur",
    "discount_pct", "peer_count", "make", "model", "year", "mileage_km",
    "power_kw", "fuel", "transmission", "drive", "body_style", "engine_signature",
    "variant_signature", "location", "views", "posted_at", "first_seen", "last_seen",
    "deal_score", "rare_score", "special_score", "scarcity_score", "hidden_gem_score",
    "repair_score", "repair_reason", "repair_estimate_min_eur", "repair_estimate_max_eur",
    "repair_risk", "repair_margin_eur", "interesting_score", "interesting_reason",
    "rare_reason", "ai_note"
]

SAW_FIELDS = [
    "source", "source_id", "url", "title", "price_eur", "brand", "model", "location",
    "views", "posted_at", "first_seen", "last_seen", "repair_score", "repair_reason",
    "repair_estimate_min_eur", "repair_estimate_max_eur", "repair_risk", "opportunity_score"
]


def safe(v):
    if v is None:
        return None
    if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
        return None
    return v


def project(row, fields):
    return {k: safe(row[k]) for k in fields if k in row.keys()}


def load_scan_status():
    if not SCAN.exists():
        return {}
    try:
        return json.loads(SCAN.read_text(encoding="utf-8"))
    except Exception:
        return {}


def main():
    init_db()
    init_chainsaw_db()
    OUT.parent.mkdir(parents=True, exist_ok=True)

    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    cars = con.execute(
        """SELECT * FROM listings
           WHERE COALESCE(is_vehicle,1)=1
             AND price_eur IS NOT NULL
             AND price_eur BETWEEN 500 AND 1000000
           ORDER BY COALESCE(interesting_score,0) DESC, COALESCE(last_seen,'') DESC"""
    ).fetchall()
    saws = con.execute(
        """SELECT * FROM chainsaws
           WHERE opportunity_score IS NOT NULL
           ORDER BY opportunity_score DESC, COALESCE(last_seen,'') DESC"""
    ).fetchall()
    runs = con.execute(
        """SELECT r.* FROM source_runs r
           JOIN (SELECT source, MAX(id) id FROM source_runs GROUP BY source) x ON x.id=r.id
           ORDER BY r.source"""
    ).fetchall()
    con.close()

    all_candidates = []
    deals = []
    wow = []
    repairs = []
    for r in cars:
        d = project(r, CAR_FIELDS)
        deal = float(r["deal_score"] or 0)
        rare = float(r["rare_score"] or 0)
        special = float(r["special_score"] or 0)
        scarcity = float(r["scarcity_score"] or 0)
        hidden = float(r["hidden_gem_score"] or 0)
        repair = float(r["repair_score"] or 0)
        interesting = float(r["interesting_score"] or 0)
        peers = int(r["peer_count"] or 0)
        discount = float(r["discount_pct"] or 0)
        evidence = bool((r["rare_reason"] or "").strip() or (r["interesting_reason"] or "").strip())

        # The website intentionally shows fewer but stronger results.
        if interesting >= 58 or deal >= 66 or rare >= 72 or repair >= 68:
            all_candidates.append(d)
        if deal >= 70 and peers >= 10 and discount >= 12:
            deals.append(d)
        if evidence and rare >= 75 and (special >= 45 or hidden >= 70 or scarcity >= 88):
            wow.append(d)
        if repair >= 68 and ((r["repair_margin_eur"] or 0) >= 700 or deal >= 48):
            repairs.append(d)

    all_candidates = all_candidates[:2500]
    deals = sorted(deals, key=lambda x: (x.get("deal_score") or 0, x.get("discount_pct") or 0), reverse=True)[:600]
    wow = sorted(wow, key=lambda x: (x.get("rare_score") or 0, x.get("interesting_score") or 0), reverse=True)[:500]
    repairs = sorted(repairs, key=lambda x: (x.get("repair_score") or 0, x.get("repair_margin_eur") or 0), reverse=True)[:500]
    saw_out = [project(r, SAW_FIELDS) for r in saws if float(r["opportunity_score"] or 0) >= 62][:800]

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "counts": {
            "cars_in_db": len(cars),
            "strong_candidates": len(all_candidates),
            "deals": len(deals),
            "wow": len(wow),
            "repairs": len(repairs),
            "chainsaws": len(saw_out),
        },
        "cars": all_candidates,
        "deals": deals,
        "wow": wow,
        "repairs": repairs,
        "chainsaws": saw_out,
        "source_runs": [dict(r) for r in runs],
        "scan": load_scan_status(),
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"Wrote {OUT} ({OUT.stat().st_size/1024:.1f} KiB)")


if __name__ == "__main__":
    main()
