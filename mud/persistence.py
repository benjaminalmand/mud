from __future__ import annotations

import hashlib
import json
import os
import secrets
from dataclasses import asdict, dataclass, field
from pathlib import Path

from mud.models import Player


DEFAULT_SAVE_DIR = Path(__file__).resolve().parent.parent / "saves"
LEGACY_CHARACTER_NAME_RE = r"^[A-Za-z][A-Za-z' -]{1,19}$"


@dataclass(slots=True)
class AccountRecord:
    id: str
    name: str
    password_salt: str
    password_hash: str
    characters: list[str] = field(default_factory=list)


def configured_save_dir() -> Path:
    override = os.getenv("APPLEHILL_SAVE_DIR", "").strip()
    if override:
        return Path(override).expanduser()
    return DEFAULT_SAVE_DIR


def configured_account_dir() -> Path:
    override = os.getenv("APPLEHILL_ACCOUNT_DIR", "").strip()
    if override:
        return Path(override).expanduser()
    return configured_save_dir().parent / "accounts"


def ensure_save_dir() -> Path:
    save_dir = configured_save_dir()
    save_dir.mkdir(parents=True, exist_ok=True)
    return save_dir


def ensure_account_dir() -> Path:
    account_dir = configured_account_dir()
    account_dir.mkdir(parents=True, exist_ok=True)
    return account_dir


def slugify_name(name: str) -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() else "_" for ch in name.strip())
    parts = [part for part in cleaned.split("_") if part]
    return "_".join(parts) or "adventurer"


def account_path_for(account_id: str) -> Path:
    return ensure_account_dir() / f"{account_id}.json"


def save_path_for(player_id: str, account_id: str = "") -> Path:
    if account_id:
        account_dir = ensure_save_dir() / account_id
        account_dir.mkdir(parents=True, exist_ok=True)
        return account_dir / f"{player_id}.json"
    return ensure_save_dir() / f"{player_id}.json"


def save_player(player: Player) -> Path:
    path = save_path_for(player.id, player.account_id)
    path.write_text(json.dumps(asdict(player), indent=2), encoding="utf-8")
    return path


def load_player(path: Path) -> Player:
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload.setdefault("account_id", path.parent.name if path.parent != ensure_save_dir() else "")
    return Player(**payload)


def list_saves() -> list[Path]:
    save_dir = ensure_save_dir()
    return sorted(save_dir.glob("*.json"))


def list_character_saves(account_id: str) -> list[Path]:
    char_dir = ensure_save_dir() / account_id
    char_dir.mkdir(parents=True, exist_ok=True)
    return sorted(char_dir.glob("*.json"))


def delete_character_save(account_id: str, character_id: str) -> None:
    path = save_path_for(character_id, account_id)
    if path.exists():
        path.unlink()


def hash_password(password: str, salt: str) -> str:
    derived = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt), 200_000)
    return derived.hex()


def create_account(name: str, password: str) -> AccountRecord:
    account_id = slugify_name(name)
    salt = secrets.token_hex(16)
    account = AccountRecord(
        id=account_id,
        name=name,
        password_salt=salt,
        password_hash=hash_password(password, salt),
    )
    save_account(account)
    return account


def save_account(account: AccountRecord) -> Path:
    path = account_path_for(account.id)
    path.write_text(json.dumps(asdict(account), indent=2), encoding="utf-8")
    return path


def load_account(path: Path) -> AccountRecord:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return AccountRecord(**payload)


def load_account_by_name(name: str) -> AccountRecord | None:
    path = account_path_for(slugify_name(name))
    if not path.exists():
        return None
    return load_account(path)


def verify_account_password(account: AccountRecord, password: str) -> bool:
    return hash_password(password, account.password_salt) == account.password_hash


def change_account_password(account: AccountRecord, password: str) -> None:
    account.password_salt = secrets.token_hex(16)
    account.password_hash = hash_password(password, account.password_salt)
    save_account(account)


def account_exists(name: str) -> bool:
    return account_path_for(slugify_name(name)).exists()


def list_accounts() -> list[AccountRecord]:
    return sorted(
        (load_account(path) for path in ensure_account_dir().glob("*.json")),
        key=lambda account: account.name.lower(),
    )


def legacy_character_saves() -> list[Path]:
    return list_saves()


def import_legacy_characters(account: AccountRecord) -> list[str]:
    imported: list[str] = []
    for path in legacy_character_saves():
        player = load_player(path)
        if not _looks_like_valid_character_name(player.name):
            path.unlink(missing_ok=True)
            continue
        player.account_id = account.id
        save_player(player)
        imported.append(player.name)
        path.unlink(missing_ok=True)
    refresh_account_characters(account)
    return imported


def refresh_account_characters(account: AccountRecord) -> None:
    account.characters = [path.stem for path in list_character_saves(account.id)]
    save_account(account)


def _looks_like_valid_character_name(name: str) -> bool:
    import re

    return bool(re.fullmatch(LEGACY_CHARACTER_NAME_RE, name))
