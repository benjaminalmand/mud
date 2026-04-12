from __future__ import annotations

from dataclasses import dataclass, field


SKILL_TITLES = [
    "Inept",
    "Amateur",
    "Novice",
    "Apprentice",
    "Journeyman",
    "Adept",
    "Expert",
    "Master",
    "Grandmaster",
]


@dataclass(frozen=True, slots=True)
class RaceDefinition:
    id: str
    name: str
    description: str
    size: str
    base_speed: int
    stat_adjustments: dict[str, int]
    automatic_languages: list[str]
    favored_class: str
    traits: list[str] = field(default_factory=list)
    ac_modifiers: dict[str, int] = field(default_factory=dict)
    proficiency_bonuses: dict[str, int] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ClassDefinition:
    id: str
    name: str
    description: str
    hit_die: int
    primary_abilities: list[str]
    starting_hp_bonus: int = 0
    mana_per_level: int = 0
    spellcasting_skill: str | None = None
    class_features: list[str] = field(default_factory=list)
    starting_proficiencies: dict[str, int] = field(default_factory=dict)
    starting_items: list[str] = field(default_factory=list)
    starting_spells: list[str] = field(default_factory=list)


SPELLS: dict[str, dict[str, object]] = {
    "magic_missile": {
        "id": "magic_missile",
        "name": "magic missile",
        "description": "A dart of force leaps from your hand and strikes your foe.",
        "resource_cost": 3,
        "skill_id": "arcane_magic",
        "targeting": "enemy",
        "effects": {"damage_dice_count": 1, "damage_dice_sides": 4, "damage_bonus": 1, "damage_type": "force"},
    },
    "ray_of_frost": {
        "id": "ray_of_frost",
        "name": "ray of frost",
        "description": "A narrow lance of winter-blue energy bites into your foe.",
        "resource_cost": 2,
        "skill_id": "arcane_magic",
        "targeting": "enemy",
        "effects": {"damage_dice_count": 1, "damage_dice_sides": 3, "damage_bonus": 0, "damage_type": "cold"},
    },
    "cure_light_wounds": {
        "id": "cure_light_wounds",
        "name": "cure light wounds",
        "description": "A wash of gentle radiance closes your lesser hurts.",
        "resource_cost": 3,
        "skill_id": "divine_magic",
        "targeting": "self",
        "effects": {"heal_dice_count": 1, "heal_dice_sides": 8, "heal_bonus": 1},
    },
    "sacred_flame": {
        "id": "sacred_flame",
        "name": "sacred flame",
        "description": "A brief lance of holy fire descends upon your enemy.",
        "resource_cost": 2,
        "skill_id": "divine_magic",
        "targeting": "enemy",
        "effects": {"damage_dice_count": 1, "damage_dice_sides": 4, "damage_bonus": 0, "damage_type": "fire"},
    },
}


RACES: dict[str, RaceDefinition] = {
    "human": RaceDefinition(
        id="human",
        name="Human",
        description="Humans are adaptable and ambitious, with no inherent strengths or weaknesses.",
        size="medium",
        base_speed=30,
        stat_adjustments={},
        automatic_languages=["common"],
        favored_class="any",
        traits=["adaptable", "versatile", "extra_training"],
    ),
    "dwarf": RaceDefinition(
        id="dwarf",
        name="Dwarf",
        description="Dwarves are sturdy, hard-headed folk of stone, steel, and stubborn endurance.",
        size="medium",
        base_speed=20,
        stat_adjustments={"constitution": 2, "charisma": -2},
        automatic_languages=["common", "dwarven"],
        favored_class="fighter",
        traits=["darkvision_60", "stonecunning", "poison_resistant", "stable"],
        ac_modifiers={"size": 0},
        proficiency_bonuses={"clubs": 1},
    ),
    "elf": RaceDefinition(
        id="elf",
        name="Elf",
        description="Elves are graceful, keen-sensed, and swift, though less hardy than humankind.",
        size="medium",
        base_speed=30,
        stat_adjustments={"dexterity": 2, "constitution": -2},
        automatic_languages=["common", "elven"],
        favored_class="wizard",
        traits=["low_light_vision", "keen_senses", "sleep_immune", "enchantment_resistant"],
        proficiency_bonuses={"bows": 1, "single_edged_blades": 1},
    ),
    "gnome": RaceDefinition(
        id="gnome",
        name="Gnome",
        description="Gnomes are clever and curious smallfolk with a gift for magic, lore, and illusion.",
        size="small",
        base_speed=20,
        stat_adjustments={"constitution": 2, "strength": -2},
        automatic_languages=["common", "gnome"],
        favored_class="bard",
        traits=["low_light_vision", "small", "illusion_resistant", "speak_with_burrowers"],
        ac_modifiers={"size": 1},
        proficiency_bonuses={"illusion_magic": 1},
    ),
    "half_elf": RaceDefinition(
        id="half_elf",
        name="Half-Elf",
        description="Half-elves move between two worlds, carrying some of the gifts and burdens of both.",
        size="medium",
        base_speed=30,
        stat_adjustments={},
        automatic_languages=["common", "elven"],
        favored_class="any",
        traits=["low_light_vision", "sleep_immune", "social_grace"],
    ),
    "half_orc": RaceDefinition(
        id="half_orc",
        name="Half-Orc",
        description="Half-orcs are powerful and intimidating, but often mistrusted and underestimated.",
        size="medium",
        base_speed=30,
        stat_adjustments={"strength": 2, "intelligence": -2, "charisma": -2},
        automatic_languages=["common", "orc"],
        favored_class="barbarian",
        traits=["darkvision_60", "orc_blood", "fearsome"],
    ),
    "halfling": RaceDefinition(
        id="halfling",
        name="Halfling",
        description="Halflings are nimble, light-footed, and surprisingly brave when pressed.",
        size="small",
        base_speed=20,
        stat_adjustments={"dexterity": 2, "strength": -2},
        automatic_languages=["common", "halfling"],
        favored_class="rogue",
        traits=["small", "nimble", "fear_resistant", "quiet_step"],
        ac_modifiers={"size": 1},
        proficiency_bonuses={"slings": 1, "thrown_projectiles": 1},
    ),
}


CLASSES: dict[str, ClassDefinition] = {
    "fighter": ClassDefinition(
        id="fighter",
        name="Fighter",
        description="Fighters trust steel, skill, and stubborn grit.",
        hit_die=10,
        primary_abilities=["strength", "constitution"],
        starting_hp_bonus=2,
        class_features=["martial_training", "combat_focus"],
        starting_proficiencies={"clubs": 4, "short_blades": 3, "staves": 2},
        starting_items=["broken_branch_club", "patched_goblin_cap"],
    ),
    "rogue": ClassDefinition(
        id="rogue",
        name="Rogue",
        description="Rogues excel through speed, nerve, and a blade in the dark.",
        hit_die=6,
        primary_abilities=["dexterity", "intelligence"],
        starting_hp_bonus=1,
        class_features=["quick_hands", "light_step"],
        starting_proficiencies={"short_blades": 4, "slings": 3},
        starting_items=["goblin_bone_knife", "frayed_sling"],
    ),
    "wizard": ClassDefinition(
        id="wizard",
        name="Wizard",
        description="Wizards shape the world through study, memory, and disciplined arcane force.",
        hit_die=4,
        primary_abilities=["intelligence"],
        mana_per_level=6,
        spellcasting_skill="arcane_magic",
        class_features=["spellbook_training", "arcane_focus"],
        starting_proficiencies={"staves": 3, "slings": 2, "arcane_magic": 3},
        starting_items=["gnome_prayer_beads", "frayed_sling"],
        starting_spells=["magic_missile", "ray_of_frost"],
    ),
    "cleric": ClassDefinition(
        id="cleric",
        name="Cleric",
        description="Clerics carry their deity's favor into darkness, battle, and prayer.",
        hit_die=8,
        primary_abilities=["wisdom", "charisma"],
        mana_per_level=4,
        spellcasting_skill="divine_magic",
        class_features=["divine_channeling", "holy_lore"],
        starting_proficiencies={"clubs": 3, "staves": 2, "divine_magic": 3},
        starting_items=["sunlit_candlestick", "gnome_prayer_beads"],
        starting_spells=["cure_light_wounds", "sacred_flame"],
    ),
}


DEFAULT_BASE_STATS = {
    "strength": 11,
    "dexterity": 11,
    "constitution": 11,
    "intelligence": 10,
    "wisdom": 10,
    "charisma": 10,
}


CREATION_POINT_BUDGET = 6


def proficiency_title(level: int) -> str:
    normalized = max(1, min(25, level))
    if normalized >= 25:
        return "Grandmaster"
    index = min((normalized - 1) // 3, len(SKILL_TITLES) - 2)
    return SKILL_TITLES[index]


def experience_to_next_level(level: int) -> int:
    return max(100, level * 100)
