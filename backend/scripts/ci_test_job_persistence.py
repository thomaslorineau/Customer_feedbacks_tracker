import json
import sys
from pathlib import Path
from fastapi.testclient import TestClient
import time

# Ensure project root is on sys.path so `backend` package can be imported
proj_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(proj_root))

from backend.app import main

client = TestClient(main.app)

print('Start job persistence test')
# Start a keyword job
payload = {'keywords': ['persist_test']}
print('POST /scrape/keywords')
r = client.post('/scrape/keywords', json=payload)
print(r.status_code, json.dumps(r.json(), indent=2, ensure_ascii=False))
if r.status_code != 200:
    print('Could not start job; aborting')
    sys.exit(1)

job_id = r.json().get('job_id')
print('Job id:', job_id)

# Wait briefly for job record to be created in DB
time.sleep(0.5)

# Simulate process restart by removing job from in-memory JOBS
if job_id in main.JOBS:
    print('Simulating restart: removing job from main.JOBS')
    main.JOBS.pop(job_id, None)

# Now query job via API; get_job_status should fall back to DB
print('GET /scrape/jobs/{job_id} (after simulated restart)')
r2 = client.get(f'/scrape/jobs/{job_id}')
print(r2.status_code, json.dumps(r2.json(), indent=2, ensure_ascii=False))

if r2.status_code == 200 and r2.json().get('id') == job_id:
    print('Persistence check: OK — job found in DB fallback')
    sys.exit(0)
else:
    print('Persistence check: FAILED')
    sys.exit(2)
