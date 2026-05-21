#!/usr/bin/env python3
import urllib.request, json, sys
from pc_common import paperclip_api_key

api_key = paperclip_api_key()
issue_id = sys.argv[1]
url = f'http://127.0.0.1:3100/api/issues/{issue_id}/comments'
req = urllib.request.Request(url, headers={'Authorization': 'Bearer ' + api_key})
with urllib.request.urlopen(req, timeout=15) as resp:
    data = json.loads(resp.read().decode())
    print(json.dumps(data, indent=2, ensure_ascii=False))
