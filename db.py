from __future__ import annotations
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from .models import Listing

DB_PATH = Path(__file__).resolve().parent.parent / 'cars.db'

LISTING_COLUMNS = {
  'source':'TEXT NOT NULL','source_id':'TEXT NOT NULL','url':'TEXT','title':'TEXT','price_eur':'REAL','price_original':'REAL','currency':'TEXT',
  'make':'TEXT','model':'TEXT','year':'INTEGER','mileage_km':'INTEGER','power_kw':'INTEGER','fuel':'TEXT','transmission':'TEXT','drive':'TEXT',
  'body_style':'TEXT','engine_signature':'TEXT','variant_signature':'TEXT','location':'TEXT','views':'INTEGER','posted_at':'TEXT','seller_type':'TEXT',
  'description':'TEXT','first_seen':'TEXT','last_seen':'TEXT','deal_score':'REAL','market_price_eur':'REAL','discount_pct':'REAL','peer_count':'INTEGER',
  'special_score':'REAL','scarcity_score':'REAL','hidden_gem_score':'REAL','rare_score':'REAL','rare_reason':'TEXT',
  'repair_score':'REAL','repair_reason':'TEXT','repair_estimate_min_eur':'REAL','repair_estimate_max_eur':'REAL','repair_risk':'TEXT','repair_margin_eur':'REAL',
  'opportunity_score':'REAL','interesting_score':'REAL','interesting_reason':'TEXT','local_tags':'TEXT','detail_fetched_at':'TEXT','ai_note':'TEXT','ai_last_analyzed':'TEXT','is_vehicle':'INTEGER','vehicle_confidence':'REAL','vehicle_reject_reason':'TEXT'
}

def connect():
    con=sqlite3.connect(DB_PATH); con.row_factory=sqlite3.Row; return con

def _migrate(con):
    have={r['name'] for r in con.execute('PRAGMA table_info(listings)').fetchall()}
    for col,typ in LISTING_COLUMNS.items():
        if col not in have:
            con.execute(f'ALTER TABLE listings ADD COLUMN {col} {typ}')

def init_db():
    with connect() as con:
        con.execute('''CREATE TABLE IF NOT EXISTS listings (
          source TEXT NOT NULL, source_id TEXT NOT NULL, url TEXT, title TEXT,
          price_eur REAL, price_original REAL, currency TEXT, make TEXT, model TEXT, year INTEGER, mileage_km INTEGER,
          power_kw INTEGER, fuel TEXT, transmission TEXT, drive TEXT, body_style TEXT, engine_signature TEXT, variant_signature TEXT,
          location TEXT, views INTEGER, posted_at TEXT, seller_type TEXT, description TEXT, first_seen TEXT, last_seen TEXT,
          deal_score REAL, market_price_eur REAL, discount_pct REAL, peer_count INTEGER, special_score REAL, scarcity_score REAL,
          hidden_gem_score REAL, rare_score REAL, rare_reason TEXT, repair_score REAL, repair_reason TEXT, repair_estimate_min_eur REAL,
          repair_estimate_max_eur REAL, repair_risk TEXT, repair_margin_eur REAL, opportunity_score REAL, interesting_score REAL,
          interesting_reason TEXT, local_tags TEXT, detail_fetched_at TEXT, ai_note TEXT, ai_last_analyzed TEXT, is_vehicle INTEGER, vehicle_confidence REAL, vehicle_reject_reason TEXT,
          PRIMARY KEY(source, source_id))''')
        _migrate(con)
        con.executescript('''
        CREATE TABLE IF NOT EXISTS price_history (source TEXT, source_id TEXT, observed_at TEXT, price_eur REAL);
        CREATE TABLE IF NOT EXISTS source_runs (id INTEGER PRIMARY KEY AUTOINCREMENT, run_at TEXT, source TEXT, saved INTEGER, error TEXT);
        CREATE INDEX IF NOT EXISTS idx_vehicle ON listings(make, model, year, mileage_km, price_eur);
        CREATE INDEX IF NOT EXISTS idx_score ON listings(deal_score DESC);
        CREATE INDEX IF NOT EXISTS idx_interest ON listings(interesting_score DESC);
        CREATE INDEX IF NOT EXISTS idx_rare ON listings(rare_score DESC);
        CREATE INDEX IF NOT EXISTS idx_views ON listings(views);
        ''')

def upsert(x: Listing):
    now=datetime.now(timezone.utc).isoformat()
    with connect() as con:
        old=con.execute('SELECT price_eur, first_seen FROM listings WHERE source=? AND source_id=?',(x.source,x.source_id)).fetchone()
        first_seen=old['first_seen'] if old else now
        if x.price_eur is not None and (not old or old['price_eur'] != x.price_eur):
            con.execute('INSERT INTO price_history VALUES (?,?,?,?)',(x.source,x.source_id,now,x.price_eur))
        x.first_seen=first_seen; x.last_seen=now
        d=x.to_dict(); cols=list(LISTING_COLUMNS.keys()); vals=[d.get(c) for c in cols]
        placeholders=','.join('?' for _ in cols)
        preserve={'source','source_id','first_seen','deal_score','market_price_eur','discount_pct','peer_count','scarcity_score','repair_margin_eur','opportunity_score','interesting_score','interesting_reason','detail_fetched_at','ai_note','ai_last_analyzed'}
        updates=','.join(f'{c}=excluded.{c}' for c in cols if c not in preserve)
        con.execute(f'''INSERT INTO listings ({','.join(cols)}) VALUES ({placeholders})
        ON CONFLICT(source,source_id) DO UPDATE SET {updates}, last_seen=excluded.last_seen''',vals)

def record_source_run(source:str,saved:int,error:str|None):
    with connect() as con:
        con.execute('INSERT INTO source_runs(run_at,source,saved,error) VALUES (?,?,?,?)',(datetime.now(timezone.utc).isoformat(),source,saved,error))

def all_rows():
    with connect() as con: return con.execute('SELECT * FROM listings').fetchall()
