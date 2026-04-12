from __future__ import annotations

from mud.creation import apply_race_adjustments, build_player
from mud.game import Game
from mud.models import Player
from mud.persistence import list_saves, load_player, save_player, slugify_name
from mud.rules import (
    CLASSES,
    CREATION_POINT_BUDGET,
    DEFAULT_BASE_STATS,
    RACES,
)


def prompt_choice(prompt: str, options: list[tuple[str, str]]) -> str:
    while True:
        print(f"\n{prompt}")
        for index, (_, label) in enumerate(options, start=1):
            print(f" {index}. {label}")
        response = input("> ").strip()
        if response.isdigit():
            index = int(response) - 1
            if 0 <= index < len(options):
                return options[index][0]
        for key, _ in options:
            if response.lower() == key.lower():
                return key
        print("Please choose one of the listed options.")


def prompt_number(prompt: str, minimum: int, maximum: int) -> int:
    while True:
        response = input(f"{prompt} [{minimum}-{maximum}]: ").strip()
        if response.isdigit():
            value = int(response)
            if minimum <= value <= maximum:
                return value
        print(f"Please enter a number between {minimum} and {maximum}.")


def prompt_text(prompt: str, default: str | None = None) -> str:
    while True:
        suffix = f" [{default}]" if default else ""
        response = input(f"{prompt}{suffix}: ").strip()
        if response:
            return response
        if default is not None:
            return default
        print("Please enter a value.")


def allocate_stats() -> dict[str, int]:
    stats = DEFAULT_BASE_STATS.copy()
    remaining = CREATION_POINT_BUDGET
    order = ["strength", "dexterity", "constitution", "intelligence", "wisdom", "charisma"]
    print(f"\nAllocate {CREATION_POINT_BUDGET} stat points.")
    print("Each point raises one ability by 1 before racial adjustments.")
    while remaining > 0:
        print(f"\nPoints remaining: {remaining}")
        for index, stat_name in enumerate(order, start=1):
            print(f" {index}. {stat_name.title():<12} {stats[stat_name]}")
        choice = prompt_number("Choose a stat to raise", 1, len(order))
        stats[order[choice - 1]] += 1
        remaining -= 1
    return stats

def create_character() -> Player:
    print("\nCreate a new character")
    name = prompt_text("Name")
    gender = prompt_text("Gender", "unknown")
    print("\nRaces")
    for race in RACES.values():
        print(f" {race.name}: {race.description}")
    race_id = prompt_choice(
        "Choose a race",
        [(race.id, race.name) for race in RACES.values()],
    )
    print("\nClasses")
    for class_def in CLASSES.values():
        print(f" {class_def.name}: {class_def.description}")
    class_id = prompt_choice(
        "Choose a class",
        [(class_def.id, class_def.name) for class_def in CLASSES.values()],
    )
    allocated_stats = allocate_stats()
    adjusted_stats = apply_race_adjustments(allocated_stats, race_id)
    print("\nFinal starting abilities after racial adjustments:")
    for stat_name in ["strength", "dexterity", "constitution", "intelligence", "wisdom", "charisma"]:
        print(f" {stat_name.title():<12} {adjusted_stats[stat_name]}")
    player = build_player(name, race_id, class_id, gender, allocated_stats)
    save_player(player)
    print(f"\n{name} the {CLASSES[class_id].name} is ready.")
    return player


def choose_save() -> Player | None:
    saves = list_saves()
    if not saves:
        print("\nNo saved characters found.")
        return None

    print("\nLoad a character")
    for index, path in enumerate(saves, start=1):
        player = load_player(path)
        print(f" {index}. {player.name} the {player.class_id.title()} ({player.race.replace('_', '-').title()})")

    while True:
        response = input("> ").strip()
        if response.isdigit():
            index = int(response) - 1
            if 0 <= index < len(saves):
                return load_player(saves[index])
        print("Please choose one of the listed saves.")


def startup_menu() -> Player:
    while True:
        print("\nApplehill")
        print(" 1. New Character")
        print(" 2. Load Character")
        print(" 3. Quit")
        choice = input("> ").strip()
        if choice == "1":
            return create_character()
        if choice == "2":
            player = choose_save()
            if player is not None:
                return player
            continue
        if choice == "3":
            raise SystemExit(0)
        print("Please choose 1, 2, or 3.")


def main() -> None:
    player = startup_menu()
    game = Game(player=player)
    game.run()


if __name__ == "__main__":
    main()
