"""Configuration loading for Hermes We Law OS."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


DEFAULT_CONFIG_PATH = Path("config/welaw.yaml.example")


class ConfigError(ValueError):
    """Raised when a We Law config file is missing or malformed."""


class ConfigLoader:
    """Load the We Law config from a JSON-compatible YAML file."""

    def __init__(self, path: str | Path = DEFAULT_CONFIG_PATH):
        self.path = Path(path)

    def load(self) -> dict[str, Any]:
        if not self.path.exists():
            raise ConfigError(f"Config file not found: {self.path}")
        raw = self.path.read_text(encoding="utf-8")
        try:
            config = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ConfigError(
                "welaw.yaml.example must be JSON-compatible in offline mode"
            ) from exc
        self._validate(config)
        return config

    def _validate(self, config: dict[str, Any]) -> None:
        required = ["despacho", "paperclip", "google_workspace", "folders"]
        missing = [key for key in required if key not in config]
        if missing:
            raise ConfigError(f"Missing config sections: {', '.join(missing)}")

        paperclip = config.get("paperclip", {})
        if paperclip.get("adapter_type") != "hermes_local":
            raise ConfigError("paperclip.adapter_type must be hermes_local")

        approvals = config.get("approval_types", [])
        if "aprobar_documento" not in approvals:
            raise ConfigError("approval_types must include aprobar_documento")

    @property
    def despacho_nombre(self) -> str:
        return str(self.load()["despacho"]["nombre"])


def load_config(path: str | Path = DEFAULT_CONFIG_PATH) -> dict[str, Any]:
    return ConfigLoader(path).load()
