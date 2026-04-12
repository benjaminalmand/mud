from __future__ import annotations

import json
from pathlib import Path

from mud.models import Item, Monster, Npc, Room, World, Zone


DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "zones" / "applehill.json"


def load_world(path: Path | None = None) -> World:
    source_path = path or DATA_PATH
    payload = json.loads(source_path.read_text(encoding="utf-8"))

    zone_data = payload["zone"]
    zone = Zone(
        id=zone_data["id"],
        name=zone_data["name"],
        theme=zone_data["theme"],
        starting_room=zone_data["starting_room"],
        summary=zone_data["summary"],
    )

    room_positions = build_room_positions(payload["rooms"], zone.starting_room)
    rooms = {
        room_data["id"]: Room(
            id=room_data["id"],
            name=room_data["name"],
            short_description=room_data["short_description"],
            long_description=room_data["long_description"],
            exits=room_data["exits"],
            tags=room_data.get("tags", []),
            map_x=room_positions[room_data["id"]][0],
            map_y=room_positions[room_data["id"]][1],
        )
        for room_data in payload["rooms"]
    }
    items = {
        item_data["id"]: Item(
            id=item_data["id"],
            name=item_data["name"],
            keywords=item_data["keywords"],
            description=item_data["description"],
            room_id=item_data.get("room_id"),
            portable=item_data["portable"],
            value=item_data["value"],
            weight=item_data["weight"],
            kind=item_data["kind"],
            flags=item_data.get("flags", []),
            condition=item_data.get("condition", "perfect"),
            equip_slots=item_data.get("equip_slots", []),
            weapon_skill=item_data.get("weapon_skill"),
            weapon_type=item_data.get("weapon_type"),
            weapon_stats=item_data.get("weapon_stats", {}),
            armor_bonus_value=item_data.get("armor_bonus", 0),
            ac_bonus_types=item_data.get("ac_bonus_types", {}),
            max_dex_bonus=item_data.get("max_dex_bonus"),
            armour_penalty=item_data.get("armour_penalty", 0),
            armour_type=item_data.get("armour_type"),
        )
        for item_data in payload["items"]
    }
    npcs = {
        npc_data["id"]: Npc(
            id=npc_data["id"],
            name=npc_data["name"],
            keywords=npc_data["keywords"],
            description=npc_data["description"],
            room_id=npc_data["room_id"],
            disposition=npc_data["disposition"],
            dialogue=npc_data["dialogue"],
            quest_hint=npc_data["quest_hint"],
        )
        for npc_data in payload["npcs"]
    }
    monsters = {
        monster_data["id"]: Monster(
            id=monster_data["id"],
            name=monster_data["name"],
            keywords=monster_data["keywords"],
            description=monster_data["description"],
            room_id=monster_data["room_id"],
            stats=monster_data["stats"],
            loot_table=monster_data["loot_table"],
            combat=monster_data.get("combat", {}),
        )
        for monster_data in payload["monsters"]
    }

    validate_world(zone, rooms, items, npcs, monsters)
    return World(zone=zone, rooms=rooms, items=items, npcs=npcs, monsters=monsters)


def validate_world(
    zone: Zone,
    rooms: dict[str, Room],
    items: dict[str, Item],
    npcs: dict[str, Npc],
    monsters: dict[str, Monster],
) -> None:
    if zone.starting_room not in rooms:
        raise ValueError(f"Unknown starting room: {zone.starting_room}")

    for room in rooms.values():
        for direction, target_room_id in room.exits.items():
            if target_room_id not in rooms:
                raise ValueError(f"Room {room.id} has invalid {direction} exit to {target_room_id}")

    for item in items.values():
        if item.room_id is not None and item.room_id not in rooms:
            raise ValueError(f"Item {item.id} references unknown room {item.room_id}")

    for npc in npcs.values():
        if npc.room_id not in rooms:
            raise ValueError(f"NPC {npc.id} references unknown room {npc.room_id}")

    for monster in monsters.values():
        if monster.room_id not in rooms:
            raise ValueError(f"Monster {monster.id} references unknown room {monster.room_id}")
        for item_id in monster.loot_table:
            if item_id not in items:
                raise ValueError(f"Monster {monster.id} drops unknown item {item_id}")


def build_room_positions(rooms_data: list[dict[str, object]], starting_room: str) -> dict[str, tuple[int, int]]:
    explicit_positions = {
        room_data["id"]: (room_data["map"]["x"], room_data["map"]["y"])
        for room_data in rooms_data
        if "map" in room_data
    }
    if explicit_positions:
        return explicit_positions

    offsets = {
        "north": (0, -1),
        "south": (0, 1),
        "east": (1, 0),
        "west": (-1, 0),
        "up": (0, -2),
        "down": (0, 2),
    }

    rooms_by_id = {room_data["id"]: room_data for room_data in rooms_data}
    positions: dict[str, tuple[int, int]] = {starting_room: (0, 0)}
    queue = [starting_room]
    next_fallback_x = 3

    while queue:
        room_id = queue.pop(0)
        current_x, current_y = positions[room_id]
        exits = rooms_by_id[room_id].get("exits", {})
        for direction, target_room_id in exits.items():
            if target_room_id in positions:
                continue
            offset_x, offset_y = offsets.get(direction, (next_fallback_x, 0))
            positions[target_room_id] = (current_x + offset_x, current_y + offset_y)
            queue.append(target_room_id)
            if direction not in offsets:
                next_fallback_x += 1

    for room_id in rooms_by_id:
        if room_id not in positions:
            positions[room_id] = (next_fallback_x, 0)
            next_fallback_x += 1

    return positions
