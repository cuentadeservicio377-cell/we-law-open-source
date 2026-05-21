#!/usr/bin/env python3
import json
import sys
import urllib.request

from pc_common import paperclip_api_key


api_key = paperclip_api_key()
issue_id = sys.argv[1]
url = f"http://127.0.0.1:3100/api/issues/{issue_id}"
req = urllib.request.Request(url, headers={"Authorization": "Bearer " + api_key})
with urllib.request.urlopen(req, timeout=15) as resp:
    issue = json.loads(resp.read().decode())

print(f"Issue: {issue.get('identifier') or issue.get('id')}")
print(f"Title: {issue.get('title', '')}")
print(f"Status: {issue.get('status', '')}")
print("")
print("Description:")
print(issue.get("description") or "")
comments = issue.get("comments") or []
print("")
print(f"Comments: {len(comments)}")
for comment in comments:
    body = (comment.get("body") or "").strip()
    created = comment.get("createdAt", "")
    print(f"- {created}: {body[:800]}")
