#!/usr/bin/env python3
import urllib.request, json, sys
from pc_common import paperclip_api_key, paperclip_run_id

api_key = paperclip_api_key()
run_id = paperclip_run_id(required=True)
issue_id = sys.argv[1]
url = f'http://127.0.0.1:3100/api/issues/{issue_id}'
payload = json.dumps({"status": "done"}).encode('utf-8')
req = urllib.request.Request(url, data=payload, headers={
    'Authorization': 'Bearer ' + api_key,
    'X-Paperclip-Run-Id': run_id,
    'Content-Type': 'application/json'
}, method='PATCH')
with urllib.request.urlopen(req, timeout=15) as resp:
    data = json.loads(resp.read().decode())
    print(json.dumps(data, indent=2, ensure_ascii=False))
