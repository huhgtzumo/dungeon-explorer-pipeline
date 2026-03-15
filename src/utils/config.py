"""載入設定：YAML + .env（帶快取，避免重複 I/O）+ 共用工具函式"""

from __future__ import annotations

import copy
import os
from datetime import datetime
from pathlib import Path

import yaml
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).parent.parent.parent
CONFIG_PATH = PROJECT_ROOT / "config" / "settings.yaml"

_config_cache: dict | None = None


def load_config(*, force_reload: bool = False) -> dict:
    """載入 settings.yaml 並合併環境變數。結果會快取，除非 force_reload=True。"""
    global _config_cache
    if _config_cache is not None and not force_reload:
        return _config_cache

    load_dotenv(PROJECT_ROOT / ".env")

    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    # 環境變數覆蓋
    config["proxy"] = {
        "base_url": os.getenv("PROXY_BASE_URL", "http://localhost:3456/v1"),
        "api_key": os.getenv("PROXY_API_KEY", ""),
        "model": os.getenv("PROXY_MODEL", "openai/gpt-4o"),
    }
    config["youtube_api_key"] = os.getenv("YOUTUBE_API_KEY", "")
    config["gemini_api_key"] = os.getenv("GEMINI_API_KEY", "")
    config["kling_access_key"] = os.getenv("KLING_ACCESS_KEY", "")
    config["kling_secret_key"] = os.getenv("KLING_SECRET_KEY", "")
    config["fal_api_key"] = os.getenv("FAL_API_KEY", "")
    config["whisper_model"] = os.getenv("WHISPER_MODEL", "base")

    _config_cache = config
    return copy.deepcopy(config)


def now_str() -> str:
    """統一的時間戳格式，供 index_db / knowledge_base 等共用。"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
