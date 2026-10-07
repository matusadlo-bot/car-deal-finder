import json
from pathlib import Path
from apscheduler.schedulers.blocking import BlockingScheduler
from car_deal_finder.scan import run_scan

cfg=json.loads((Path(__file__).parent/'config.json').read_text(encoding='utf-8'))
mins=int(cfg.get('scan_interval_minutes',60))
s=BlockingScheduler()
s.add_job(run_scan,'interval',minutes=mins,max_instances=1,coalesce=True)
print('Car Deal Finder scheduler beží. Interval:',mins,'min')
run_scan(); s.start()
