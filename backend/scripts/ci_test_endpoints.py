import json
import sys
from pathlib import Path
from fastapi.testclient import TestClient

# Ensure project root is on sys.path so `backend` package can be imported
proj_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(proj_root))

from backend.app import main

client = TestClient(main.app)

print('GET /settings/queries:')
r = client.get('/settings/queries')
print(r.status_code, json.dumps(r.json(), indent=2, ensure_ascii=False))

print('\nPOST /settings/queries:')
r = client.post('/settings/queries', json={'keywords': ['ci_test', 'ovh']})
print(r.status_code, json.dumps(r.json(), indent=2, ensure_ascii=False))

print('\nGET /settings/queries (after save):')
r = client.get('/settings/queries')
print(r.status_code, json.dumps(r.json(), indent=2, ensure_ascii=False))

print('\nPOST /scrape/x?query=ci_test&limit=1:')
r = client.post('/scrape/x?query=ci_test&limit=1')
print(r.status_code, json.dumps(r.json(), indent=2, ensure_ascii=False))

print('\nPOST /scrape/keywords (start job):')
payload = {'keywords': ['ci_test','ovh_test']}
r = client.post('/scrape/keywords', json=payload)
print(r.status_code, json.dumps(r.json(), indent=2, ensure_ascii=False))
if r.status_code == 200:
	job_id = r.json().get('job_id')
	print('\nPolling job status...')
	import time
	for i in range(10):
		jr = client.get(f'/scrape/jobs/{job_id}')
		print(i, jr.status_code, json.dumps(jr.json(), indent=2, ensure_ascii=False))
		if jr.json().get('status') in ('completed','failed','cancelled'):
			break
		time.sleep(0.5)
