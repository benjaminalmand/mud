from __future__ import annotations

import getpass
import re
from dataclasses import dataclass

from mud.creation import apply_race_adjustments, build_player
from mud.models import Player
from mud.persistence import (
    AccountRecord,
    account_exists,
    change_account_password,
    create_account,
    delete_character_save,
    import_legacy_characters,
    list_character_saves,
    load_account_by_name,
    load_player,
    refresh_account_characters,
    save_player,
    verify_account_password,
)
from mud.rules import CLASSES, CREATION_POINT_BUDGET, DEFAULT_BASE_STATS, RACES


ACCOUNT_NAME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]{2,19}$")
CHARACTER_NAME_RE = re.compile(r"^[A-Za-z][A-Za-z' -]{1,19}$")


@dataclass(slots=True)
class StartupPromptResult:
    value: str | None
    should_continue: bool = True


class StartupIO:
    def write_line(self, text: str = "") -> None:
        raise NotImplementedError

    def prompt(self, text: str, *, secret: bool = False) -> StartupPromptResult:
        raise NotImplementedError


class TerminalStartupIO(StartupIO):
    def write_line(self, text: str = "") -> None:
        print(text)

    def prompt(self, text: str, *, secret: bool = False) -> StartupPromptResult:
        try:
            if secret:
                return StartupPromptResult(getpass.getpass(f"{text}: ").strip())
            return StartupPromptResult(input(f"{text}: ").strip())
        except (EOFError, KeyboardInterrupt):
            self.write_line()
            return StartupPromptResult(None, should_continue=False)


def valid_account_name(name: str) -> bool:
    return bool(ACCOUNT_NAME_RE.fullmatch(name))


def valid_character_name(name: str) -> bool:
    return bool(CHARACTER_NAME_RE.fullmatch(name))


def prompt_choice(io: StartupIO, prompt: str, options: list[tuple[str, str]]) -> str | None:
    while True:
        io.write_line()
        io.write_line(prompt)
        for index, (_, label) in enumerate(options, start=1):
            io.write_line(f" {index}. {label}")
        response = io.prompt(">").value
        if response is None:
            return None
        if response.isdigit():
            index = int(response) - 1
            if 0 <= index < len(options):
                return options[index][0]
        for key, _ in options:
            if response.lower() == key.lower():
                return key
        io.write_line("Please choose one of the listed options.")


def prompt_number(io: StartupIO, prompt: str, minimum: int, maximum: int) -> int | None:
    while True:
        response = io.prompt(f"{prompt} [{minimum}-{maximum}]").value
        if response is None:
            return None
        if response.isdigit():
            value = int(response)
            if minimum <= value <= maximum:
                return value
        io.write_line(f"Please enter a number between {minimum} and {maximum}.")


def prompt_text(io: StartupIO, prompt: str, default: str | None = None) -> str | None:
    while True:
        suffix = f" [{default}]" if default else ""
        response = io.prompt(f"{prompt}{suffix}").value
        if response is None:
            return None
        if response:
            return response
        if default is not None:
            return default
        io.write_line("Please enter a value.")


def allocate_stats(io: StartupIO) -> dict[str, int] | None:
    stats = DEFAULT_BASE_STATS.copy()
    remaining = CREATION_POINT_BUDGET
    order = ["strength", "dexterity", "constitution", "intelligence", "wisdom", "charisma"]
    io.write_line()
    io.write_line(f"Allocate {CREATION_POINT_BUDGET} stat points.")
    io.write_line("Each point raises one ability by 1 before racial adjustments.")
    while remaining > 0:
        io.write_line()
        io.write_line(f"Points remaining: {remaining}")
        for index, stat_name in enumerate(order, start=1):
            io.write_line(f" {index}. {stat_name.title():<12} {stats[stat_name]}")
        choice = prompt_number(io, "Choose a stat to raise", 1, len(order))
        if choice is None:
            return None
        stats[order[choice - 1]] += 1
        remaining -= 1
    return stats


def create_character(io: StartupIO, account: AccountRecord) -> Player | None:
    io.write_line()
    io.write_line("Create a new character")
    while True:
        name = prompt_text(io, "Name")
        if name is None:
            return None
        if valid_character_name(name):
            break
        io.write_line("Character names must start with a letter and use only letters, spaces, apostrophes, or hyphens.")
    gender = prompt_text(io, "Gender", "unknown")
    if gender is None:
        return None
    io.write_line()
    io.write_line("Races")
    for race in RACES.values():
        io.write_line(f" {race.name}: {race.description}")
    race_id = prompt_choice(io, "Choose a race", [(race.id, race.name) for race in RACES.values()])
    if race_id is None:
        return None
    io.write_line()
    io.write_line("Classes")
    for class_def in CLASSES.values():
        io.write_line(f" {class_def.name}: {class_def.description}")
    class_id = prompt_choice(io, "Choose a class", [(class_def.id, class_def.name) for class_def in CLASSES.values()])
    if class_id is None:
        return None
    allocated_stats = allocate_stats(io)
    if allocated_stats is None:
        return None
    adjusted_stats = apply_race_adjustments(allocated_stats, race_id)
    io.write_line()
    io.write_line("Final starting abilities after racial adjustments:")
    for stat_name in ["strength", "dexterity", "constitution", "intelligence", "wisdom", "charisma"]:
        io.write_line(f" {stat_name.title():<12} {adjusted_stats[stat_name]}")
    player = build_player(name, race_id, class_id, gender, allocated_stats, account_id=account.id)
    save_player(player)
    refresh_account_characters(account)
    io.write_line()
    io.write_line(f"{name} the {CLASSES[class_id].name} is ready.")
    return player


def choose_character(io: StartupIO, account: AccountRecord) -> Player | None:
    saves = list_character_saves(account.id)
    if not saves:
        io.write_line()
        io.write_line("This account has no characters yet.")
        return None
    io.write_line()
    io.write_line("Play which character?")
    for index, path in enumerate(saves, start=1):
        player = load_player(path)
        io.write_line(f" {index}. {player.name} the {player.class_id.title()} ({player.race.replace('_', '-').title()})")
    while True:
        response = io.prompt(">").value
        if response is None:
            return None
        if response.isdigit():
            index = int(response) - 1
            if 0 <= index < len(saves):
                return load_player(saves[index])
        io.write_line("Please choose one of the listed characters.")


def delete_character(io: StartupIO, account: AccountRecord) -> None:
    saves = list_character_saves(account.id)
    if not saves:
        io.write_line("This account has no characters to delete.")
        return
    io.write_line()
    io.write_line("Delete which character?")
    for index, path in enumerate(saves, start=1):
        player = load_player(path)
        io.write_line(f" {index}. {player.name} the {player.class_id.title()} ({player.race.replace('_', '-').title()})")
    response = io.prompt(">").value
    if response is None or not response.isdigit():
        io.write_line("Deletion cancelled.")
        return
    index = int(response) - 1
    if not (0 <= index < len(saves)):
        io.write_line("Deletion cancelled.")
        return
    player = load_player(saves[index])
    confirmation = io.prompt(f"Type DELETE to remove {player.name}").value
    if confirmation != "DELETE":
        io.write_line("Deletion cancelled.")
        return
    delete_character_save(account.id, player.id)
    refresh_account_characters(account)
    io.write_line(f"{player.name} has been deleted from this account.")


def maybe_import_legacy(io: StartupIO, account: AccountRecord) -> None:
    from mud.persistence import legacy_character_saves

    legacy = legacy_character_saves()
    if not legacy:
        return
    response = io.prompt(f"Import {len(legacy)} existing standalone character(s) into this account? [y/N]").value
    if not response or response.lower() not in {"y", "yes"}:
        return
    imported = import_legacy_characters(account)
    if imported:
        io.write_line(f"Imported: {', '.join(imported)}")


def authenticate_account(io: StartupIO) -> AccountRecord | None:
    io.write_line("Applehill")
    while True:
        account_name = io.prompt("Account name").value
        if account_name is None:
            return None
        if not valid_account_name(account_name):
            io.write_line("Account names must start with a letter and use 3-20 letters, numbers, or underscores.")
            continue
        password = io.prompt("Password", secret=True).value
        if password is None:
            return None

        account = load_account_by_name(account_name)
        if account is None:
            create = io.prompt(f"No account named {account_name}. Create it? [y/N]").value
            if not create or create.lower() not in {"y", "yes"}:
                continue
            if len(password) < 6:
                io.write_line("Passwords must be at least 6 characters.")
                continue
            confirm = io.prompt("Confirm password", secret=True).value
            if confirm is None:
                return None
            if confirm != password:
                io.write_line("Passwords did not match.")
                continue
            account = create_account(account_name, password)
            maybe_import_legacy(io, account)
            return account

        if verify_account_password(account, password):
            return account
        io.write_line("That password was not correct.")


def account_menu(io: StartupIO, account: AccountRecord) -> Player | None:
    while True:
        refresh_account_characters(account)
        io.write_line()
        io.write_line(f"Account: {account.name}")
        io.write_line(" 1. Play one of your characters")
        io.write_line(" 2. Start a new character in this account")
        io.write_line(" 3. Delete a character in this account")
        io.write_line(" 4. Change your account password")
        io.write_line(" 5. Logout")
        choice = io.prompt(">").value
        if choice is None:
            return None
        if choice == "1":
            player = choose_character(io, account)
            if player is not None:
                return player
            continue
        if choice == "2":
            player = create_character(io, account)
            if player is not None:
                return player
            continue
        if choice == "3":
            delete_character(io, account)
            continue
        if choice == "4":
            current = io.prompt("Current password", secret=True).value
            if current is None:
                return None
            if not verify_account_password(account, current):
                io.write_line("That password was not correct.")
                continue
            new_password = io.prompt("New password", secret=True).value
            if new_password is None:
                return None
            if len(new_password) < 6:
                io.write_line("Passwords must be at least 6 characters.")
                continue
            confirm = io.prompt("Confirm new password", secret=True).value
            if confirm is None:
                return None
            if confirm != new_password:
                io.write_line("Passwords did not match.")
                continue
            change_account_password(account, new_password)
            io.write_line("Your password has been changed.")
            continue
        if choice == "5":
            return None
        io.write_line("Please choose 1, 2, 3, 4, or 5.")


def login_and_choose_character(io: StartupIO) -> Player | None:
    while True:
        account = authenticate_account(io)
        if account is None:
            return None
        player = account_menu(io, account)
        if player is not None:
            return player
