from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class Room:
    id: str
    name: str
    short_description: str
    long_description: str
    exits: dict[str, str]
    tags: list[str]
    map_x: int
    map_y: int


@dataclass(slots=True)
class Item:
    id: str
    name: str
    keywords: list[str]
    description: str
    room_id: str | None
    portable: bool
    value: int
    weight: int
    kind: str
    flags: list[str] = field(default_factory=list)
    condition: str = "perfect"
    equip_slots: list[str] = field(default_factory=list)
    weapon_skill: str | None = None
    weapon_type: str | None = None
    weapon_stats: dict[str, int | str] = field(default_factory=dict)
    armor_bonus_value: int = 0
    ac_bonus_types: dict[str, int] = field(default_factory=dict)
    max_dex_bonus: int | None = None
    armour_penalty: int = 0
    armour_type: str | None = None


@dataclass(slots=True)
class Character:
    id: str
    name: str
    keywords: list[str]
    description: str
    room_id: str
    posture: str = field(default="standing", kw_only=True)


@dataclass(slots=True)
class Npc(Character):
    disposition: str
    dialogue: list[str]
    quest_hint: str


@dataclass(slots=True)
class Monster(Character):
    stats: dict[str, int]
    loot_table: list[str]
    combat: dict[str, int | str | list[str]] = field(default_factory=dict)
    current_hp: int = 0

    def __post_init__(self) -> None:
        if self.current_hp <= 0:
            self.current_hp = self.stats.get("hp", 1)


@dataclass(slots=True)
class Zone:
    id: str
    name: str
    theme: str
    starting_room: str
    summary: str


@dataclass(slots=True)
class World:
    zone: Zone
    rooms: dict[str, Room]
    items: dict[str, Item]
    npcs: dict[str, Npc]
    monsters: dict[str, Monster]

    def items_in_room(self, room_id: str) -> list[Item]:
        return [item for item in self.items.values() if item.room_id == room_id]

    def npcs_in_room(self, room_id: str) -> list[Npc]:
        return [npc for npc in self.npcs.values() if npc.room_id == room_id]

    def monsters_in_room(self, room_id: str) -> list[Monster]:
        return [monster for monster in self.monsters.values() if monster.room_id == room_id]


@dataclass(slots=True)
class Event:
    room_id: str
    text: str
    kind: str = "system"
    audience: str = "all"
    recipient_id: str | None = None


@dataclass(slots=True)
class Player:
    id: str = "adventurer"
    account_id: str = ""
    name: str = "Adventurer"
    race: str = "human"
    class_id: str = "fighter"
    gender: str = "unknown"
    room_id: str = ""
    facing: str = "north"
    inventory: list[str] = field(default_factory=list)
    group_members: list[str] = field(default_factory=list)
    posture: str = "standing"
    wielded_item_id: str | None = None
    stats: dict[str, int] = field(
        default_factory=lambda: {
            "strength": 11,
            "dexterity": 11,
            "constitution": 11,
            "intelligence": 10,
            "wisdom": 10,
            "charisma": 10,
        }
    )
    base_stats: dict[str, int] = field(
        default_factory=lambda: {
            "strength": 11,
            "dexterity": 11,
            "constitution": 11,
            "intelligence": 10,
            "wisdom": 10,
            "charisma": 10,
        }
    )
    equipment: dict[str, str | None] = field(
        default_factory=lambda: {
            "finger_1": None,
            "finger_2": None,
            "face": None,
            "around_neck": None,
            "neck": None,
            "symbol": None,
            "head": None,
            "body": None,
            "legs": None,
            "feet": None,
            "hands": None,
            "arms": None,
            "waist": None,
            "wrist_1": None,
            "wrist_2": None,
            "offhand": None,
            "belt_1": None,
            "belt_2": None,
            "floating": None,
        }
    )
    proficiencies: dict[str, dict[str, int | str]] = field(default_factory=dict)
    languages: list[str] = field(default_factory=lambda: ["common"])
    racial_traits: list[str] = field(default_factory=list)
    class_features: list[str] = field(default_factory=list)
    known_spells: list[str] = field(default_factory=list)
    spellbook: list[str] = field(default_factory=list)
    prepared_spells: dict[str, list[str]] = field(default_factory=dict)
    spell_slots_used: dict[str, int] = field(default_factory=dict)
    spell_recovery_progress: int = 0
    active_quests: dict[str, str] = field(default_factory=dict)
    completed_quests: list[str] = field(default_factory=list)
    feat_points: int = 0
    stat_points_available: int = 0
    stat_points_spent: int = 0
    level: int = 1
    experience: int = 0
    base_speed: int = 30
    size: str = "medium"
    starter_item_ids: list[str] = field(default_factory=list)
    hp: int = 12
    max_hp: int = 12
    mana: int = 0
    max_mana: int = 0
    stamina: int = 100
    max_stamina: int = 100


@dataclass(slots=True)
class CombatState:
    monster_id: str
    player_turn: bool
    round_number: int = 1
    turn_actions_remaining: int = 1
    turn_movement_remaining: int = 1
