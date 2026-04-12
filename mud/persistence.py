from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from mud.models import Player


SAVE_DIR = Path(__file__).resolve().parent.parent / "saves"


def ensure_save_dir() -> Path:
    SAVE_DIR.mkdir(parents=True, exist_ok=True)
    return SAVE_DIR


def slugify_name(name: str) -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() else "_" for ch in name.strip())
    parts = [part for part in cleaned.split("_") if part]
    return "_".join(parts) or "adventurer"


def save_path_for(player_id: str) -> Path:
    return ensure_save_dir() / f"{player_id}.json"


def save_player(player: Player) -> Path:
    path = save_path_for(player.id)
    path.write_text(json.dumps(asdict(player), indent=2), encoding="utf-8")
    return path


def load_player(path: Path) -> Player:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return Player(**payload)


def list_saves() -> list[Path]:
    save_dir = ensure_save_dir()
    return sorted(save_dir.glob("*.json"))
