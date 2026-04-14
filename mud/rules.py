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
class RaceRule:
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
class ClassRule:
    id: str
    name: str
    description: str
    hit_die: int
    primary_abilities: list[str]
    bab_progression: str
    fortitude_progression: str
    reflex_progression: str
    will_progression: str
    spellcasting_ability: str | None = None
    spell_preparation: str | None = None
    class_features: list[str] = field(default_factory=list)
    starting_proficiencies: dict[str, int] = field(default_factory=dict)
    starting_items: list[str] = field(default_factory=list)
    starting_spells: list[str] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class SpellRule:
    id: str
    name: str
    spell_level: int
    school: str
    caster_lists: list[str]
    description: str
    targeting: str
    saving_throw: str | None = None
    attack_type: str | None = None
    effects: dict[str, int | str] = field(default_factory=dict)


DEFAULT_BASE_STATS = {
    "strength": 11,
    "dexterity": 11,
    "constitution": 11,
    "intelligence": 10,
    "wisdom": 10,
    "charisma": 10,
}


CREATION_POINT_BUDGET = 6


RACES: dict[str, RaceRule] = {
    "human": RaceRule(
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
    "dwarf": RaceRule(
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
    "elf": RaceRule(
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
    "gnome": RaceRule(
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
    "half_elf": RaceRule(
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
    "half_orc": RaceRule(
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
    "halfling": RaceRule(
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


CLASSES: dict[str, ClassRule] = {
    "fighter": ClassRule(
        id="fighter",
        name="Fighter",
        description="Fighters trust steel, skill, and stubborn grit.",
        hit_die=10,
        primary_abilities=["strength", "constitution"],
        bab_progression="good",
        fortitude_progression="good",
        reflex_progression="poor",
        will_progression="poor",
        class_features=["martial_training", "combat_focus"],
        starting_proficiencies={"clubs": 4, "short_blades": 3, "staves": 2},
        starting_items=["broken_branch_club", "patched_goblin_cap"],
    ),
    "rogue": ClassRule(
        id="rogue",
        name="Rogue",
        description="Rogues excel through speed, nerve, and a blade in the dark.",
        hit_die=6,
        primary_abilities=["dexterity", "intelligence"],
        bab_progression="average",
        fortitude_progression="poor",
        reflex_progression="good",
        will_progression="poor",
        class_features=["quick_hands", "light_step"],
        starting_proficiencies={"short_blades": 4, "slings": 3},
        starting_items=["goblin_bone_knife", "frayed_sling"],
    ),
    "wizard": ClassRule(
        id="wizard",
        name="Wizard",
        description="Wizards shape the world through study, memory, and disciplined arcane force.",
        hit_die=4,
        primary_abilities=["intelligence"],
        bab_progression="poor",
        fortitude_progression="poor",
        reflex_progression="poor",
        will_progression="good",
        spellcasting_ability="intelligence",
        spell_preparation="spellbook",
        class_features=["spellbook_training", "arcane_focus"],
        starting_proficiencies={"staves": 3, "slings": 2, "arcane_magic": 3},
        starting_items=["apprentice_spellbook", "frayed_sling"],
        starting_spells=["magic_missile", "ray_of_frost"],
    ),
    "cleric": ClassRule(
        id="cleric",
        name="Cleric",
        description="Clerics carry their deity's favor into darkness, battle, and prayer.",
        hit_die=8,
        primary_abilities=["wisdom", "charisma"],
        bab_progression="average",
        fortitude_progression="good",
        reflex_progression="poor",
        will_progression="good",
        spellcasting_ability="wisdom",
        spell_preparation="prayer",
        class_features=["divine_channeling", "holy_lore"],
        starting_proficiencies={"clubs": 3, "staves": 2, "divine_magic": 3},
        starting_items=["sunlit_candlestick", "gnome_prayer_beads"],
        starting_spells=["cure_light_wounds", "sacred_flame"],
    ),
}


SPELLS: dict[str, SpellRule] = {
    "magic_missile": SpellRule(
        id="magic_missile",
        name="magic missile",
        spell_level=1,
        school="evocation",
        caster_lists=["wizard"],
        description="A dart of force leaps from your hand and strikes your foe.",
        targeting="enemy",
        attack_type="auto",
        effects={"damage_dice_count": 1, "damage_dice_sides": 4, "damage_bonus": 1, "damage_type": "force"},
    ),
    "ray_of_frost": SpellRule(
        id="ray_of_frost",
        name="ray of frost",
        spell_level=1,
        school="evocation",
        caster_lists=["wizard"],
        description="A narrow lance of winter-blue energy bites into your foe.",
        targeting="enemy",
        attack_type="ranged_touch",
        effects={"damage_dice_count": 1, "damage_dice_sides": 3, "damage_bonus": 0, "damage_type": "cold"},
    ),
    "burning_hands": SpellRule(
        id="burning_hands",
        name="burning hands",
        spell_level=1,
        school="evocation",
        caster_lists=["wizard"],
        description="A fan of fire roars from your outstretched hand.",
        targeting="enemy",
        saving_throw="reflex",
        effects={"damage_dice_count": 1, "damage_dice_sides": 6, "damage_bonus": 0, "damage_type": "fire"},
    ),
    "acid_splash": SpellRule(
        id="acid_splash",
        name="acid splash",
        spell_level=1,
        school="conjuration",
        caster_lists=["wizard"],
        description="A sizzling glob of acid arcs toward your foe.",
        targeting="enemy",
        attack_type="ranged_touch",
        effects={"damage_dice_count": 1, "damage_dice_sides": 4, "damage_bonus": 0, "damage_type": "acid"},
    ),
    "cure_light_wounds": SpellRule(
        id="cure_light_wounds",
        name="cure light wounds",
        spell_level=1,
        school="conjuration",
        caster_lists=["cleric"],
        description="A wash of gentle radiance closes your lesser hurts.",
        targeting="ally",
        effects={"heal_dice_count": 1, "heal_dice_sides": 8, "heal_bonus": 1},
    ),
    "cause_light_wounds": SpellRule(
        id="cause_light_wounds",
        name="cause light wounds",
        spell_level=1,
        school="necromancy",
        caster_lists=["cleric"],
        description="A spiteful pulse of divine harm blackens flesh at your touch.",
        targeting="enemy",
        attack_type="auto",
        effects={"damage_dice_count": 1, "damage_dice_sides": 8, "damage_bonus": 1, "damage_type": "negative"},
    ),
    "sacred_flame": SpellRule(
        id="sacred_flame",
        name="sacred flame",
        spell_level=1,
        school="evocation",
        caster_lists=["cleric"],
        description="A brief lance of holy fire descends upon your enemy.",
        targeting="enemy",
        saving_throw="reflex",
        effects={"damage_dice_count": 1, "damage_dice_sides": 4, "damage_bonus": 0, "damage_type": "fire"},
    ),
    "cure_serious_wounds": SpellRule(
        id="cure_serious_wounds",
        name="cure serious wounds",
        spell_level=2,
        school="conjuration",
        caster_lists=["cleric"],
        description="A deeper wave of blessed power knits torn flesh and steadies the spirit.",
        targeting="ally",
        effects={"heal_dice_count": 2, "heal_dice_sides": 8, "heal_bonus": 3},
    ),
    "searing_light": SpellRule(
        id="searing_light",
        name="searing light",
        spell_level=2,
        school="evocation",
        caster_lists=["cleric"],
        description="A hard spear of white-gold radiance lances toward your enemy.",
        targeting="enemy",
        attack_type="ranged_touch",
        effects={"damage_dice_count": 2, "damage_dice_sides": 6, "damage_bonus": 0, "damage_type": "radiant"},
    ),
}


SPELL_SLOTS_BY_CLASS_LEVEL: dict[str, dict[int, dict[int, int]]] = {
    "wizard": {
        1: {1: 1},
        2: {1: 2},
        3: {1: 2, 2: 1},
        4: {1: 3, 2: 2},
        5: {1: 3, 2: 2, 3: 1},
    },
    "cleric": {
        1: {1: 1},
        2: {1: 2},
        3: {1: 2, 2: 1},
        4: {1: 3, 2: 2},
        5: {1: 3, 2: 2, 3: 1},
    },
}


def proficiency_title(level: int) -> str:
    normalized = max(1, min(25, level))
    if normalized >= 25:
        return "Grandmaster"
    index = min((normalized - 1) // 3, len(SKILL_TITLES) - 2)
    return SKILL_TITLES[index]


def ability_modifier(score: int) -> int:
    return (score - 10) // 2


def progression_value(level: int, progression: str) -> int:
    level = max(1, level)
    if progression == "good":
        return 2 + (level // 2)
    if progression == "average":
        return (level * 3) // 4
    return level // 2


def base_attack_bonus_for(class_id: str, level: int) -> int:
    class_rule = CLASSES[class_id]
    return progression_value(level, class_rule.bab_progression)


def save_bonus_for(class_id: str, level: int, save_name: str) -> int:
    class_rule = CLASSES[class_id]
    progression = {
        "fortitude": class_rule.fortitude_progression,
        "reflex": class_rule.reflex_progression,
        "will": class_rule.will_progression,
    }[save_name]
    return progression_value(level, progression)


def caster_ability_for(class_id: str) -> str | None:
    return CLASSES[class_id].spellcasting_ability


def bonus_spells_for(ability_score: int, spell_level: int) -> int:
    modifier = ability_modifier(ability_score)
    if modifier < spell_level:
        return 0
    return 1 + max(0, (modifier - spell_level) // 4)


def spell_slots_for(class_id: str, level: int, casting_ability_score: int) -> dict[int, int]:
    table = SPELL_SLOTS_BY_CLASS_LEVEL.get(class_id, {})
    base_slots = table.get(min(level, max(table.keys(), default=level)), {}).copy()
    result: dict[int, int] = {}
    for spell_level, count in base_slots.items():
        result[spell_level] = count + bonus_spells_for(casting_ability_score, spell_level)
    return result


def strength_carry_limits(score: int) -> tuple[int, int, int]:
    table = {
        1: (3, 6, 10),
        2: (6, 13, 20),
        3: (10, 20, 30),
        4: (13, 26, 40),
        5: (16, 33, 50),
        6: (20, 40, 60),
        7: (23, 46, 70),
        8: (26, 53, 80),
        9: (30, 60, 90),
        10: (33, 66, 100),
        11: (38, 76, 115),
        12: (43, 86, 130),
        13: (50, 100, 150),
        14: (58, 116, 175),
        15: (66, 133, 200),
        16: (76, 153, 230),
        17: (86, 173, 260),
        18: (100, 200, 300),
        19: (116, 233, 350),
        20: (133, 266, 400),
    }
    return table.get(max(1, min(20, score)), (66, 133, 200))


def experience_to_next_level(level: int) -> int:
    return max(100, level * 1000)


def class_spell_ids(class_id: str) -> list[str]:
    return sorted(
        [spell_id for spell_id, spell in SPELLS.items() if class_id in spell.caster_lists],
        key=lambda spell_id: (SPELLS[spell_id].spell_level, SPELLS[spell_id].name),
    )
