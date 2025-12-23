import os
from pathlib import Path

from .config import get_settings


ASSET_DIRS = {
    "video": "videos",
    "audio": "audios",
    "sfx": "sfx",
}


def ensure_data_folders() -> None:
    settings = get_settings()
    base = Path(settings.data_dir)
    for sub in ASSET_DIRS.values():
        path = base / "assets" / sub
        path.mkdir(parents=True, exist_ok=True)
    (base / "logs").mkdir(parents=True, exist_ok=True)


def default_asset_path(asset_type: str, filename: str) -> str:
    settings = get_settings()
    subfolder = ASSET_DIRS.get(asset_type, asset_type)
    return str(Path(settings.data_dir) / "assets" / subfolder / filename)
