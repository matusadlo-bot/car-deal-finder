from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from car_deal_finder.scan import run_scan, load_config
from car_deal_finder.chainsaws import scan_chainsaws

ROOT = Path(__file__).resolve().parent


def main() -> int:
    mode = (sys.argv[1] if len(sys.argv) > 1 else "quick").strip().lower()
    if mode not in {"quick", "deep"}:
        mode = "quick"

    stats = {
        "mode": mode,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "cars": {},
        "chainsaws": {},
    }
    try:
        stats["cars"] = run_scan(mode)
    except Exception as exc:
        stats["cars"] = {"fatal_error": f"{type(exc).__name__}: {exc}"}

    try:
        stats["chainsaws"] = scan_chainsaws(load_config(), mode)
    except Exception as exc:
        stats["chainsaws"] = {"fatal_error": f"{type(exc).__name__}: {exc}"}

    stats["finished_at"] = datetime.now(timezone.utc).isoformat()
    (ROOT / "last_cloud_scan.json").write_text(
        json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(stats, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
