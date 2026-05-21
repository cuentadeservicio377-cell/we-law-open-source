# Sanitization Policy

Public commits must contain no real client data, no live Workspace URLs, no tokens, no private local paths, no production logs and no private Paperclip issue ranges. Use `scripts/public_safety_scan.py` before every commit.
