from __future__ import annotations

from mud.models import Player
from mud.persistence import save_player, slugify_name
from mud.rules import (
    CLASSES,
    DEFAULT_BASE_STATS,
    RACES,
    ability_modifier,
    proficiency_title,
    spell_slots_for,
)


def apply_race_adjustments(base_stats: dict[str, int], race_id: str) -> dict[str, int]:
    race = RACES[race_id]
    adjusted = base_stats.copy()
    for stat_name, adjustment in race.stat_adjustments.items():
        adjusted[stat_name] = max(3, adjusted[stat_name] + adjustment)
    return adjusted


def build_player(
    name: str,
    race_id: str,
    class_id: str,
    gender: str,
    allocated_stats: dict[str, int],
    *,
    account_id: str = "",
) -> Player:
    race = RACES[race_id]
    class_def = CLASSES[class_id]
    base_stats = apply_race_adjustments(allocated_stats, race_id)

    hp = max(1, class_def.hit_die + ability_modifier(base_stats["constitution"]))
    spell_slots_used: dict[str, int] = {}
    prepared_spells: dict[str, list[str]] = {}
    spent_prepared_slots: dict[str, list[bool]] = {}
    spellbook = class_def.starting_spells.copy()
    if class_def.spellcasting_ability is not None:
        slots = spell_slots_for(class_id, 1, base_stats[class_def.spellcasting_ability])
        spell_slots_used = {str(slot_level): 0 for slot_level in slots}
        for slot_level, slot_count in slots.items():
            prepared_spells[str(slot_level)] = []
            spent_prepared_slots[str(slot_level)] = []

    proficiencies = {
        skill_id: {"level": level, "title": proficiency_title(level), "progress": 0}
        for skill_id, level in {**race.proficiency_bonuses, **class_def.starting_proficiencies}.items()
    }

    return Player(
        id=slugify_name(name),
        account_id=account_id,
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
        spent_prepared_slots=spent_prepared_slots,
        starter_item_ids=class_def.starting_items.copy(),
        feat_points=1 if race_id == "human" else 0,
        hp=hp,
        max_hp=hp,
    )


def build_default_player(
    name: str,
    race_id: str = "human",
    class_id: str = "fighter",
    gender: str = "unknown",
    *,
    account_id: str = "",
) -> Player:
    return build_player(name, race_id, class_id, gender, DEFAULT_BASE_STATS.copy(), account_id=account_id)


def create_and_save_default_player(
    name: str,
    race_id: str = "human",
    class_id: str = "fighter",
    gender: str = "unknown",
    *,
    account_id: str = "",
) -> Player:
    player = build_default_player(name, race_id=race_id, class_id=class_id, gender=gender, account_id=account_id)
    save_player(player)
    return player
