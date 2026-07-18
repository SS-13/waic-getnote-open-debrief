"""Configuration loader.

Loads .env (if present) and exposes typed settings.
Importable from anywhere: `from scripts.config import settings`.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

_REPO_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(_REPO_ROOT / ".env", override=False)


@dataclass(frozen=True)
class GetnoteSettings:
    api_base: str
    api_key: str
    user_token: str


@dataclass(frozen=True)
class RateLimitSettings:
    rps: float
    burst: int
    daily_quota: int  # 0 = unlimited


@dataclass(frozen=True)
class Settings:
    getnote: GetnoteSettings
    rate_limit: RateLimitSettings
    state_path: Path
    log_level: str

    @property
    def repo_root(self) -> Path:
        return _REPO_ROOT


def load_settings() -> Settings:
    return Settings(
        getnote=GetnoteSettings(
            api_base=os.getenv("GETNOTE_API_BASE", "https://api.getnote.com"),
            api_key=os.getenv("GETNOTE_API_KEY", ""),
            user_token=os.getenv("GETNOTE_USER_TOKEN", ""),
        ),
        rate_limit=RateLimitSettings(
            rps=float(os.getenv("RATE_LIMIT_RPS", "1")),
            burst=int(os.getenv("RATE_LIMIT_BURST", "3")),
            daily_quota=int(os.getenv("RATE_LIMIT_DAILY_QUOTA", "5000")),
        ),
        state_path=_REPO_ROOT / os.getenv("FETCH_STATE_PATH", ".fetch_state.json"),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
    )


settings: Settings = load_settings()