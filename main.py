from __future__ import annotations

from mud.game import Game
from mud.models import Player
from mud.persistence import list_saves, load_player, save_player, slugify_name
from mud.rules import (
    CLASSES,
    CREATION_POINT_BUDGET,
    DEFAULT_BASE_STATS,
    RACES,
    ability_modifier,
    proficiency_title,
    spell_slots_for,
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


def apply_race_adjustments(base_stats: dict[str, int], race_id: str) -> dict[str, int]:
    race = RACES[race_id]
    adjusted = base_stats.copy()
    for stat_name, adjustment in race.stat_adjustments.items():
        adjusted[stat_name] = max(3, adjusted[stat_name] + adjustment)
    return adjusted


def build_player(name: str, race_id: str, class_id: str, gender: str, allocated_stats: dict[str, int]) -> Player:
    race = RACES[race_id]
    class_def = CLASSES[class_id]
    base_stats = apply_race_adjustments(allocated_stats, race_id)

    hp = max(1, class_def.hit_die + ability_modifier(base_stats["constitution"]))
    spell_slots_used: dict[str, int] = {}
    prepared_spells: dict[str, list[str]] = {}
    spellbook = class_def.starting_spells.copy()
    if class_def.spellcasting_ability is not None:
        slots = spell_slots_for(class_id, 1, base_stats[class_def.spellcasting_ability])
        spell_slots_used = {str(slot_level): 0 for slot_level in slots}
        for slot_level, slot_count in slots.items():
            available = [spell_id for spell_id in class_def.starting_spells if spell_id]
            if not available:
                prepared_spells[str(slot_level)] = []
                continue
            prepared_spells[str(slot_level)] = [
                available[index % len(available)]
                for index in range(slot_count)
            ]

    proficiencies = {
        skill_id: {"level": level, "title": proficiency_title(level), "progress": 0}
        for skill_id, level in {**race.proficiency_bonuses, **class_def.starting_proficiencies}.items()
    }

    return Player(
        id=slugify_name(name),
        name=name,
        race=race_id,
        class_id=class_id,
        gender=gender,
        room_id="",
        size=race.size,
        base_speed=race.base_speed,
        stats=base_stats.copy(),
        base_stats=base_stats.copy(),
        languages=race.automatic_languages.copy(),
        proficiencies=proficiencies,
        racial_traits=race.traits.copy(),
        class_features=class_def.class_features.copy(),
        known_spells=class_def.starting_spells.copy(),
        spellbook=spellbook,
        prepared_spells=prepared_spells,
        spell_slots_used=spell_slots_used,
        starter_item_ids=class_def.starting_items.copy(),
        feat_points=1 if race_id == "human" else 0,
        hp=hp,
        max_hp=hp,
    )


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
