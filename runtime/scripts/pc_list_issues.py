#!/usr/bin/env python3
import argparse
import json
import os
import urllib.parse
import urllib.request
from pc_common import paperclip_api_key

parser = argparse.ArgumentParser()
parser.add_argument("--api-url", default=os.environ.get("PAPERCLIP_API_URL", "http://127.0.0.1:3100/api"))
parser.add_argument("--company-id", default=os.environ.get("PAPERCLIP_COMPANY_ID", "00000000-0000-0000-0000-000000000000"))
parser.add_argument("--assignee", default="")
parser.add_argument("--limit", type=int, default=20)
args = parser.parse_args()

api_key = paperclip_api_key()
params = {"limit": str(args.limit)}
if args.assignee:
    params["assigneeAgentId"] = args.assignee
api_url = str(args.api_url).strip()
if not api_url.startswith("http"):
    api_url = "http://127.0.0.1:3100/api"
url = f"{api_url.rstrip('/')}/companies/{args.company_id}/issues?{urllib.parse.urlencode(params)}"
req = urllib.request.Request(url, headers={"Authorization": "Bearer " + api_key})
with urllib.request.urlopen(req, timeout=15) as resp:
    data = json.loads(resp.read().decode())
    print(json.dumps(data, indent=2, ensure_ascii=False))
