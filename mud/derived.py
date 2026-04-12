from __future__ import annotations

from dataclasses import dataclass

from mud.models import Item, Monster, Player, World
from mud.rules import (
    CLASSES,
    RACES,
    ability_modifier,
    base_attack_bonus_for,
    caster_ability_for,
    save_bonus_for,
    spell_slots_for,
    strength_carry_limits,
)


@dataclass(frozen=True, slots=True)
class WeaponProfile:
    name: str
    attack_bonus: int
    damage_bonus: int
    dice_count: int
    dice_sides: int
    damage_type: str
    skill_id: str
    hands_required: int
    critical_multiplier: int


@dataclass(frozen=True, slots=True)
class PlayerDerivedStats:
    size: str
    base_speed: int
    ability_modifiers: dict[str, int]
    carry_limits: tuple[int, int, int]
    carry_weight: float
    max_carry_weight: float
    load_label: str
    armor_class_breakdown: dict[str, int]
    touch_armor_class: int
    base_attack_bonus: int
    melee_attack_bonus: int
    ranged_attack_bonus: int
    ranged_spell_attack_bonus: int
    attack_power: int
    saves: dict[str, int]
    spellcasting_ability: str | None
    spellcasting_modifier: int
    spell_slots: dict[int, int]
    weapon: WeaponProfile


@dataclass(frozen=True, slots=True)
class MonsterDerivedStats:
    max_hp: int
    attack_bonus: int
    defense_bonus: int
    dexterity_modifier: int
    size_modifier: int
    deflection_bonus: int
    fortitude_save: int
    reflex_save: int
    will_save: int
    dice_count: int
    dice_sides: int
    damage_bonus: int
    initiative_bonus: int
    armor_class: int
    touch_armor_class: int


def derive_player_stats(player: Player, world: World) -> PlayerDerivedStats:
    ability_modifiers = {stat_name: ability_modifier(score) for stat_name, score in player.stats.items()}
    race = RACES.get(player.race, RACES["human"])
    size = player.size or race.size
    carry_limits = strength_carry_limits(player.stats["strength"])
    max_carry_weight = float(carry_limits[2] if size != "small" else int(carry_limits[2] * 0.75))
    carry_weight = float(sum(world.items[item_id].weight for item_id in player.inventory if item_id in world.items))
    if carry_weight <= max_carry_weight / 3:
        load_label = "light"
    elif carry_weight <= (max_carry_weight * 2) / 3:
        load_label = "medium"
    else:
        load_label = "heavy"

    armour_bonus_value = 0
    shield_bonus_value = 0
    natural_bonus_value = 0
    deflection_bonus_value = 0
    max_dex_limits: list[int] = []
    for item_id in player.equipment.values():
        if not item_id or item_id not in world.items:
            continue
        item = world.items[item_id]
        ac_bonus_types = item_ac_bonus_types(item)
        armour_bonus_value = max(armour_bonus_value, ac_bonus_types["armour"])
        shield_bonus_value = max(shield_bonus_value, ac_bonus_types["shield"])
        natural_bonus_value = max(natural_bonus_value, ac_bonus_types["natural_armour"])
        deflection_bonus_value = max(deflection_bonus_value, ac_bonus_types["deflection"])
        if item.max_dex_bonus is not None:
            max_dex_limits.append(int(item.max_dex_bonus))
    if load_label == "medium":
        max_dex_limits.append(3)
    elif load_label == "heavy":
        max_dex_limits.append(1)

    dex_bonus = ability_modifiers["dexterity"]
    if max_dex_limits:
        dex_bonus = min(dex_bonus, min(max_dex_limits))
    size_bonus = race.ac_modifiers.get("size", 1 if size == "small" else 0)
    armor_class_breakdown = {
        "base": 10,
        "dexterity_modifier": dex_bonus,
        "size": size_bonus,
        "armour": armour_bonus_value,
        "shield": shield_bonus_value,
        "natural_armour": natural_bonus_value,
        "deflection": deflection_bonus_value,
    }
    armor_class_breakdown["total"] = 10 + dex_bonus + size_bonus + armour_bonus_value + shield_bonus_value + natural_bonus_value + deflection_bonus_value
    touch_armor_class = 10 + dex_bonus + size_bonus + deflection_bonus_value

    weapon = wielded_weapon_profile(player, world)
    base_attack_bonus = base_attack_bonus_for(player.class_id, player.level)
    melee_attack_bonus = base_attack_bonus + ability_modifiers["strength"] + weapon.attack_bonus + race_attack_bonus(player)
    melee_attack_bonus += proficiency_attack_bonus(player, weapon.skill_id)
    ranged_attack_bonus = base_attack_bonus + dex_bonus + weapon.attack_bonus + race_attack_bonus(player)
    ranged_attack_bonus += proficiency_attack_bonus(player, weapon.skill_id)

    saves = {
        "fortitude": save_bonus_for(player.class_id, player.level, "fortitude") + ability_modifiers["constitution"],
        "reflex": save_bonus_for(player.class_id, player.level, "reflex") + dex_bonus + (1 if size == "small" else 0),
        "will": save_bonus_for(player.class_id, player.level, "will") + ability_modifiers["wisdom"],
    }

    spellcasting_ability = caster_ability_for(player.class_id)
    spellcasting_modifier = ability_modifiers[spellcasting_ability] if spellcasting_ability else 0
    spell_slots = spell_slots_for(player.class_id, player.level, player.stats[spellcasting_ability]) if spellcasting_ability else {}

    return PlayerDerivedStats(
        size=size,
        base_speed=player.base_speed,
        ability_modifiers=ability_modifiers,
        carry_limits=carry_limits,
        carry_weight=carry_weight,
        max_carry_weight=max_carry_weight,
        load_label=load_label,
        armor_class_breakdown=armor_class_breakdown,
        touch_armor_class=touch_armor_class,
        base_attack_bonus=base_attack_bonus,
        melee_attack_bonus=melee_attack_bonus,
        ranged_attack_bonus=ranged_attack_bonus,
        ranged_spell_attack_bonus=base_attack_bonus + dex_bonus + spellcasting_modifier,
        attack_power=max(1, 1 + ability_modifiers["strength"] + weapon.damage_bonus + race_attack_bonus(player)),
        saves=saves,
        spellcasting_ability=spellcasting_ability,
        spellcasting_modifier=spellcasting_modifier,
        spell_slots=spell_slots,
        weapon=weapon,
    )


def derive_monster_stats(monster: Monster) -> MonsterDerivedStats:
    combat = monster.combat if isinstance(monster.combat, dict) else {}
    attack_bonus = int(combat.get("attack_bonus", monster.stats.get("attack", 1)))
    defense_bonus = int(combat.get("defense_bonus", monster.stats.get("defense", 1)))
    dexterity_modifier = int(combat.get("dexterity_modifier", max(0, defense_bonus // 2 - 1)))
    size_modifier = int(combat.get("size_modifier", 0))
    deflection_bonus = int(combat.get("deflection_bonus", 0))
    fortitude_save = int(combat.get("fortitude_save", max(0, attack_bonus // 2)))
    reflex_save = int(combat.get("reflex_save", max(0, dexterity_modifier + defense_bonus // 3)))
    will_save = int(combat.get("will_save", max(0, defense_bonus // 2)))
    dice_count = int(combat.get("dice_count", 1))
    dice_sides = int(combat.get("dice_sides", 4))
    damage_bonus = int(combat.get("damage_bonus", max(0, attack_bonus // 3)))
    initiative_bonus = int(combat.get("initiative_bonus", dexterity_modifier))
    armor_class = 10 + defense_bonus + size_modifier + deflection_bonus
    touch_armor_class = 10 + dexterity_modifier + size_modifier + deflection_bonus
    return MonsterDerivedStats(
        max_hp=max(1, int(monster.stats.get("hp", 1))),
        attack_bonus=attack_bonus,
        defense_bonus=defense_bonus,
        dexterity_modifier=dexterity_modifier,
        size_modifier=size_modifier,
        deflection_bonus=deflection_bonus,
        fortitude_save=fortitude_save,
        reflex_save=reflex_save,
        will_save=will_save,
        dice_count=dice_count,
        dice_sides=dice_sides,
        damage_bonus=damage_bonus,
        initiative_bonus=initiative_bonus,
        armor_class=armor_class,
        touch_armor_class=touch_armor_class,
    )


def wielded_weapon_profile(player: Player, world: World) -> WeaponProfile:
    item = None
    if player.wielded_item_id and player.wielded_item_id in world.items and player.wielded_item_id in player.inventory:
        candidate = world.items[player.wielded_item_id]
        if candidate.kind == "weapon":
            item = candidate
    if item is None:
        return WeaponProfile(
            name="bare hands",
            attack_bonus=0,
            damage_bonus=0,
            dice_count=1,
            dice_sides=2,
            damage_type="strike",
            skill_id="brawling",
            hands_required=1,
            critical_multiplier=2,
        )
    weapon_stats = item.weapon_stats if isinstance(item.weapon_stats, dict) else {}
    return WeaponProfile(
        name=item.name,
        attack_bonus=int(weapon_stats.get("attack_bonus", inferred_weapon_attack_bonus(item))),
        damage_bonus=int(weapon_stats.get("damage_bonus", inferred_weapon_damage_bonus(item))),
        dice_count=max(1, int(weapon_stats.get("dice_count", inferred_weapon_dice(item)[0]))),
        dice_sides=max(2, int(weapon_stats.get("dice_sides", inferred_weapon_dice(item)[1]))),
        damage_type=str(weapon_stats.get("damage_type", inferred_weapon_damage_type(item))),
        skill_id=item.weapon_skill or str(weapon_stats.get("skill_id", inferred_weapon_skill(item))),
        hands_required=max(1, int(weapon_stats.get("hands_required", 1))),
        critical_multiplier=max(2, int(weapon_stats.get("critical_multiplier", 2))),
    )


def item_ac_bonus_types(item: Item) -> dict[str, int]:
    if item.ac_bonus_types:
        return {
            "armour": int(item.ac_bonus_types.get("armour", 0)),
            "shield": int(item.ac_bonus_types.get("shield", 0)),
            "natural_armour": int(item.ac_bonus_types.get("natural_armour", 0)),
            "deflection": int(item.ac_bonus_types.get("deflection", 0)),
        }
    weapon_stats = item.weapon_stats if isinstance(item.weapon_stats, dict) else {}
    return {
        "armour": int(weapon_stats.get("ac_armour", item.armor_bonus_value if item.kind == "armor" and "shield" not in item.name.lower() else 0)),
        "shield": int(weapon_stats.get("ac_shield", item.armor_bonus_value if "shield" in item.name.lower() or "lid" in item.name.lower() else 0)),
        "natural_armour": int(weapon_stats.get("ac_natural_armour", 0)),
        "deflection": int(weapon_stats.get("ac_deflection", 0)),
    }


def proficiency_attack_bonus(player: Player, skill_id: str) -> int:
    entry = player.proficiencies.get(skill_id)
    if not entry:
        return 0
    level = int(entry.get("level", 1))
    return max(0, (level - 1) // 6)


def race_attack_bonus(player: Player) -> int:
    race = RACES.get(player.race)
    if race is None:
        return 0
    return race.ac_modifiers.get("size", 0)


def inferred_weapon_skill(item: Item) -> str:
    name = item.name.lower()
    if "knife" in name or "dagger" in name:
        return "short_blades"
    if "sling" in name:
        return "slings"
    if "staff" in name:
        return "staves"
    return "clubs"


def inferred_weapon_attack_bonus(item: Item) -> int:
    name = item.name.lower()
    if "knife" in name or "dagger" in name:
        return 1
    if "sling" in name:
        return 1
    return 0


def inferred_weapon_damage_bonus(item: Item) -> int:
    name = item.name.lower()
    if "knife" in name or "dagger" in name:
        return 0
    if "club" in name:
        return 0
    if "sling" in name:
        return 0
    return 0


def inferred_weapon_dice(item: Item) -> tuple[int, int]:
    name = item.name.lower()
    if "knife" in name or "dagger" in name:
        return (1, 4)
    if "club" in name:
        return (1, 6)
    if "sling" in name:
        return (1, 4)
    return (1, 4)


def inferred_weapon_damage_type(item: Item) -> str:
    name = item.name.lower()
    if "knife" in name or "dagger" in name:
        return "pierce"
    if "sling" in name:
        return "shot"
    if "club" in name:
        return "crush"
    return "strike"
