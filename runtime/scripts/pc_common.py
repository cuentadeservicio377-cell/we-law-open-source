#!/usr/bin/env python3
import os


LOCAL_TRUSTED_API_KEY = "welaw-local-agent-jwt-secret-change-before-network"


def paperclip_api_key() -> str:
    return os.environ.get("PAPERCLIP_API_KEY") or LOCAL_TRUSTED_API_KEY


def paperclip_run_id(required: bool = False) -> str:
    run_id = os.environ.get("PAPERCLIP_RUN_ID", "")
    if required and not run_id:
        raise SystemExit("PAPERCLIP_RUN_ID is required for this write operation")
    return run_id
