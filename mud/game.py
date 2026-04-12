from __future__ import annotations

import random
from collections import defaultdict
from shutil import get_terminal_size

from mud.derived import derive_monster_stats, derive_player_stats, item_ac_bonus_types as derived_item_ac_bonus_types
from mud.models import CombatState, Event, Item, Monster, Npc, Player, World
from mud.persistence import save_player
from mud.quests import QUESTS
from mud.session import GameSession, LocalTerminalSession
from mud.rules import (
    CLASSES,
    RACES,
    SPELLS,
    ability_modifier,
    base_attack_bonus_for,
    caster_ability_for,
    experience_to_next_level,
    proficiency_title,
    save_bonus_for,
    spell_slots_for,
    strength_carry_limits,
)
from mud.socials import SOCIALS
from mud.world import load_world


DIRECTION_ALIASES = {
    "n": "north",
    "north": "north",
    "s": "south",
    "south": "south",
    "e": "east",
    "east": "east",
    "w": "west",
    "west": "west",
    "u": "up",
    "up": "up",
    "d": "down",
    "down": "down",
}


class Game:
    def __init__(self, player: Player | None = None) -> None:
        self.world: World = load_world()
        self.player = player or Player(room_id=self.world.zone.starting_room)
        if not self.player.room_id:
            self.player.room_id = self.world.zone.starting_room
        self.hydrate_player_state()
        self.combat: CombatState | None = None
        self.room_events_by_room: dict[str, list[Event]] = defaultdict(list)
        self.set_room_view(
            f"Welcome to {self.world.zone.name}. Type 'help' if you need a hand.",
            self.world.zone.summary,
        )

    def run(self) -> None:
        self.run_session(LocalTerminalSession())

    def run_session(self, session: GameSession) -> None:
        self.emit_self_event("You steady yourself for the road ahead.")
        while True:
            session.display(session.render(self))
            result = session.read_command(self)
            if not result.should_continue:
                break
            if not self.step(result.command):
                break

    def step(self, command: str | None) -> bool:
        if command is None:
            command = ""
        if not command:
            self.recover_stamina()
            return True
        should_continue = self.handle_command(command)
        self.recover_stamina()
        return should_continue

    def handle_command(self, raw_command: str) -> bool:
        parts = raw_command.lower().split()
        verb = parts[0]
        args = parts[1:]

        if self.combat is not None and verb not in {
            "look", "l", "score", "stats", "equipment", "eq", "help", "kill", "attack", "hit",
            "wield", "wear", "equip", "hold", "remove", "unequip", "eat", "n", "s", "e", "w", "u", "d",
            "north", "south", "east", "west", "up", "down", "quit", "exit", "cast", "spells", "spellbook",
            "say", "sayto",
        }:
            self.emit_self_event("You are in combat. Fight, flee, or tend to immediate needs first.")
            return True

        if verb in DIRECTION_ALIASES:
            self.move(DIRECTION_ALIASES[verb])
            return True

        if verb in {"look", "l"}:
            self.look(args)
            return True

        if verb in {"inventory", "inv", "i"}:
            self.show_inventory()
            return True

        if verb in {"equipment", "eq"}:
            self.show_equipment()
            return True

        if verb in {"score", "stats"}:
            self.show_score()
            return True

        if verb in {"quest", "quests", "journal"}:
            self.show_quests()
            return True

        if verb in {"spells", "spellbook"}:
            self.show_spells()
            return True

        if verb in {"prepare", "memorize"}:
            self.prepare_spell(args)
            return True

        if verb == "sit":
            self.sit_down()
            return True

        if verb == "stand":
            self.stand_up()
            return True

        if verb == "rest":
            self.rest()
            return True

        if verb in {"get", "take"}:
            self.take_item(args)
            return True

        if verb == "drop":
            self.drop_item(args)
            return True

        if verb in {"wield", "hold"}:
            self.equip_item(args)
            return True

        if verb in {"wear", "equip"}:
            self.equip_item(args)
            return True

        if verb in {"remove", "unequip"}:
            self.remove_item(args)
            return True

        if verb in {"talk", "ask"}:
            self.talk(args)
            return True

        if verb == "say":
            self.say(args)
            return True

        if verb == "sayto":
            self.say_to(args)
            return True

        if verb in SOCIALS:
            self.perform_social(verb, args)
            return True

        if verb in {"kill", "attack", "hit"}:
            self.attack(args)
            return True

        if verb == "eat":
            self.eat(args)
            return True

        if verb == "cast":
            self.cast_spell(args)
            return True

        if verb == "help":
            self.show_help()
            return True

        if verb == "save":
            self.save_character()
            return True

        if verb in {"quit", "exit"}:
            self.emit_self_event("Your adventure in Applehill pauses for now.")
            return False

        self.emit_self_event(f"You do not know how to '{raw_command}'.")
        return True

    def visible_room_events(self) -> list[str]:
        return [
            event.text
            for event in self.room_events_by_room[self.player.room_id]
            if event.audience in {"all", "self"} or (event.audience == "target" and event.recipient_id == self.player.id)
        ]

    def player_snapshot(self):
        return derive_player_stats(self.player, self.world)

    def monster_snapshot(self, monster: Monster):
        return derive_monster_stats(monster)

    def hydrate_player_state(self) -> None:
        if not self.player.spellbook and self.player.known_spells:
            self.player.spellbook = self.player.known_spells.copy()
        if not self.player.prepared_spells:
            self.reset_spell_preparation()
        held_item_ids = set(self.player.inventory)
        held_item_ids.update(item_id for item_id in self.player.equipment.values() if item_id)
        if self.player.wielded_item_id:
            held_item_ids.add(self.player.wielded_item_id)
        held_item_ids.update(self.player.starter_item_ids)
        for item_id in held_item_ids:
            item = self.world.items.get(item_id)
            if item is not None:
                item.room_id = None
        for item_id in self.player.starter_item_ids:
            if item_id not in self.player.inventory and item_id not in self.player.equipment.values():
                self.player.inventory.append(item_id)
        if self.player.wielded_item_id is None:
            for item_id in self.player.inventory:
                item = self.world.items.get(item_id)
                if item is not None and item.kind == "weapon":
                    self.player.wielded_item_id = item_id
                    break
        for item_id in self.player.inventory:
            item = self.world.items.get(item_id)
            if item is None or item.kind == "weapon":
                continue
            slot = choose_equipment_slot(item, self.player.equipment)
            if slot is not None and self.player.equipment.get(slot) is None:
                self.player.equipment[slot] = item_id

    def set_room_view(self, *lines: str) -> None:
        room_id = self.player.room_id
        self.room_events_by_room[room_id] = [
            Event(room_id=room_id, text=line, audience="self")
            for line in lines
            if line
        ]

    def emit_event(
        self,
        text: str,
        *,
        room_id: str | None = None,
        kind: str = "system",
        audience: str = "all",
    ) -> None:
        target_room = room_id or self.player.room_id
        self.room_events_by_room[target_room].append(
            Event(room_id=target_room, text=text, kind=kind, audience=audience)
        )
        self.room_events_by_room[target_room] = self.room_events_by_room[target_room][-40:]

    def emit_self_event(self, text: str, *, kind: str = "system") -> None:
        self.emit_event(text, kind=kind, audience="self")

    def emit_room_event(self, room_id: str, text: str, *, kind: str = "room") -> None:
        self.emit_event(text, room_id=room_id, kind=kind, audience="others")

    def emit_target_event(self, recipient_id: str, text: str, *, room_id: str | None = None, kind: str = "social") -> None:
        target_room = room_id or self.player.room_id
        self.room_events_by_room[target_room].append(
            Event(room_id=target_room, text=text, kind=kind, audience="target", recipient_id=recipient_id)
        )
        self.room_events_by_room[target_room] = self.room_events_by_room[target_room][-40:]

    def default_combat_action(self, monster: Monster) -> str:
        preferred_spell = self.preferred_combat_spell()
        if preferred_spell is not None:
            return f"cast {preferred_spell.name}"
        return f"kill {monster.name}"

    def preferred_combat_spell(self):
        slots = self.available_spell_slots()
        for spell_ids in self.player.prepared_spells.values():
            for spell_id in spell_ids:
                spell = SPELLS.get(spell_id)
                if spell is None or spell.targeting != "enemy":
                    continue
                used = int(self.player.spell_slots_used.get(str(spell.spell_level), 0))
                if used >= slots.get(spell.spell_level, 0):
                    continue
                return spell
        return None

    def can_take_action(self, *, in_combat_message: str) -> bool:
        if self.combat is None:
            return True
        if not self.combat.player_turn:
            self.emit_self_event("You are still recovering from the last exchange.")
            return False
        if self.combat.turn_actions_remaining <= 0:
            self.emit_self_event(in_combat_message)
            return False
        return True

    def spend_action(self) -> None:
        if self.combat is not None:
            self.combat.turn_actions_remaining = 0

    def spend_movement(self) -> None:
        if self.combat is not None:
            self.combat.turn_movement_remaining = 0

    def action_summary_line(self) -> str:
        if self.combat is None:
            return ""
        action_state = "ready" if self.combat.turn_actions_remaining > 0 else "spent"
        move_state = "ready" if self.combat.turn_movement_remaining > 0 else "spent"
        return f"Round {self.combat.round_number}: action {action_state}, movement {move_state}."

    def combat_footer_text(self) -> str:
        monster = self.current_combatant()
        if self.combat is None or monster is None:
            return ""
        target_status = wound_status_line(monster.name, monster.current_hp, self.monster_snapshot(monster).max_hp).replace(f"{monster.name} is ", "")
        action_state = "ready" if self.combat.turn_actions_remaining > 0 else "spent"
        move_state = "ready" if self.combat.turn_movement_remaining > 0 else "spent"
        turn_owner = "you" if self.combat.player_turn else monster.name
        return f"{monster.name} | round {self.combat.round_number} | turn {turn_owner} | action {action_state} | move {move_state} | target {target_status}"

    def move(self, direction: str) -> None:
        room = self.world.rooms[self.player.room_id]
        if self.player.posture == "sitting":
            self.emit_self_event("You must stand before you can move.")
            return
        if self.combat is not None:
            self.attempt_flee(direction)
            return
        if direction not in room.exits:
            if direction in {"north", "south", "east", "west"}:
                self.player.facing = direction
            self.emit_self_event("You cannot go that way.")
            return

        old_room_id = self.player.room_id
        new_room_id = room.exits[direction]
        self.emit_room_event(old_room_id, departure_text(self.player.name, direction), kind="departure")
        self.emit_room_event(new_room_id, arrival_text(self.player.name, opposite_direction(direction)), kind="arrival")
        self.player.room_id = new_room_id
        if direction in {"north", "south", "east", "west"}:
            self.player.facing = direction
        self.player.posture = "standing"
        self.set_room_view(f"You walk {direction}.")

    def look(self, args: list[str]) -> None:
        if not args:
            self.set_room_view()
            return

        target = " ".join(args)
        if target in {"self", "me", "myself"}:
            self.emit_self_event(f"{self.player.name} stands ready for adventure.")
            self.emit_self_event(
                f"HP {self.player.hp}/{self.player.max_hp}  "
                f"Attack {self.player_attack_power()}  Defense {self.player_defense_value()}"
            )
            return

        item = self.find_item(target, include_inventory=True)
        if item is not None:
            self.emit_self_event(item.description)
            return

        npc = self.find_npc(target)
        if npc is not None:
            self.emit_self_event(npc.description)
            return

        monster = self.find_monster(target)
        if monster is not None:
            self.emit_self_event(monster.description)
            return

        self.emit_self_event(f"You see no '{target}' here.")

    def show_inventory(self) -> None:
        if not self.player.inventory:
            self.emit_self_event("You are carrying nothing.")
            return
        names = [self.world.items[item_id].name for item_id in self.player.inventory]
        self.emit_self_event(f"You are carrying: {', '.join(names)}")

    def show_equipment(self) -> None:
        lines = ["You are using:"]
        for slot in EQUIPMENT_DISPLAY_ORDER:
            item_id = self.player.equipment.get(slot)
            if not item_id or item_id not in self.world.items:
                continue
            lines.append(f"{slot_display_label(slot):<22} {format_item_summary(self.world.items[item_id])}")
        wielded = self.wielded_weapon()
        if wielded is not None:
            lines.append(f"{slot_display_label('weapon'):<22} {format_item_summary(wielded)}")
        if len(lines) == 1:
            lines.append("Nothing.")
        self.set_room_view(*lines)

    def show_score(self) -> None:
        width = min(get_terminal_size((120, 36)).columns - 2, 79)
        divider = "-" * max(30, width)
        class_def = CLASSES.get(self.player.class_id, CLASSES["fighter"])
        race_def = RACES.get(self.player.race, RACES["human"])
        snapshot = self.player_snapshot()
        class_name = class_def.name
        race_name = race_def.name
        ac = snapshot.armor_class_breakdown
        title = f" {self.player.name}, {class_name} of Applehill "
        lines = [divider]
        lines.append(title.center(len(divider)))
        lines.append(f" Class: {class_name.lower():<12} Race: {race_name.lower():<12} Level: {self.player.level:<3} Gender: {self.player.gender}")
        lines.append(f" XP: {self.player.experience}/{experience_to_next_level(self.player.level):<6} Feat Points: {self.player.feat_points:<3} Stat Points: {self.player.stat_points_available:<3} Load: {snapshot.load_label}")
        lines.append(f" Carry Weight: {snapshot.carry_weight:>5.1f}/{snapshot.max_carry_weight:<6.1f} Speed: {snapshot.base_speed:<3} Size: {snapshot.size}")
        lines.append(" " + "-" * 20 + "+" + "-" * (len(divider) - 22))
        lines.append(f" {'Ability Scores':<20}| Armour Class")
        for stat_name, armor_slot in zip(
            ["strength", "dexterity", "constitution", "intelligence", "wisdom", "charisma"],
            ["head", "body", "arms", "hands", "waist", "legs"],
        ):
            stat_score = self.player.stats[stat_name]
            base_score = self.player.base_stats.get(stat_name, stat_score)
            line_left = f" {abbr(stat_name):<3} {stat_score:>2}/{base_score:<2} Bonus: {stat_bonus(stat_score):+d}"
            line_right = f"{armor_slot:<6} {ac['total']:>2} ({equipped_item_name(self.world, self.player, armor_slot)})"
            lines.append(f"{line_left:<20}| {line_right}")
        lines.append(" " + "-" * 20 + "+" + "-" * (len(divider) - 22))
        lines.append(f" {'Saving Throws':<20}| AC Breakdown")
        fort = self.player_save_throw("fortitude")
        reflex = self.player_save_throw("reflex")
        will = self.player_save_throw("will")
        lines.append(f" {'Fortitude:':<12}{fort:>3}{'':5}| Dex: {ac['dexterity_modifier']:+d}")
        lines.append(f" {'Reflex:':<12}{reflex:>3}{'':5}| Size: {ac['size']:+d}")
        lines.append(f" {'Will:':<12}{will:>3}{'':5}| Armour: {ac['armour']:+d}  Shield: {ac['shield']:+d}")
        damage = weapon_damage_text(self.wielded_weapon())
        lines.append(" " + "-" * 20 + "+" + "-" * (len(divider) - 22))
        lines.append(f" {'Combat Stats':<20}| Spellcasting & Traits")
        lines.append(f" {'BAB:':<12}{snapshot.base_attack_bonus:>3}{'':5}| {self.spell_slot_summary_line()}")
        lines.append(f" {'Attack:':<12}{snapshot.melee_attack_bonus:>3}{'':5}| {', '.join((self.player.racial_traits + self.player.class_features)[:2]) or 'none'}")
        lines.append(f" {'Weapon:':<12}{damage:>3}{'':5}| Caster: {snapshot.spellcasting_ability or 'none'}")
        lines.append(
            f" Health: {self.player.hp}/{self.player.max_hp}   "
            f"Stamina: {self.player.stamina}/{self.player.max_stamina}   "
            f"Speed: {snapshot.base_speed}"
        )
        if self.player.proficiencies:
            sample = ", ".join(
                f"{skill_id.replace('_', ' ').title()} {payload['level']}"
                for skill_id, payload in list(sorted(self.player.proficiencies.items()))[:3]
            )
            lines.append(f" Proficiencies: {sample}")
        lines.append(divider)
        self.set_room_view(*lines)

    def save_character(self) -> None:
        path = save_player(self.player)
        self.emit_self_event(f"Your progress is saved to {path.name}.")

    def show_spells(self) -> None:
        if not self.player.spellbook:
            self.emit_self_event("You do not know any spells.")
            return
        lines = ["Prepared Spells"]
        lines.append(self.spell_slot_summary_line())
        prepared_any = False
        for slot_level in sorted(self.available_spell_slots()):
            prepared = self.player.prepared_spells.get(str(slot_level), [])
            if prepared:
                prepared_any = True
                lines.append(f"Level {slot_level}:")
                for spell_id in prepared:
                    spell = SPELLS.get(spell_id)
                    if spell is None:
                        continue
                    lines.append(f"- {spell.name} ({spell.school})")
        if not prepared_any:
            lines.append("You have no spells prepared.")
        lines.append("")
        lines.append("Spellbook")
        for spell_id in self.player.spellbook:
            spell = SPELLS.get(spell_id)
            if spell is None:
                continue
            lines.append(f"- {spell.name} (level {spell.spell_level}) {spell.description}")
        self.set_room_view(*lines)

    def prepare_spell(self, args: list[str]) -> None:
        if not args:
            self.emit_self_event("Prepare which spell?")
            return
        if not self.player.spellbook:
            self.emit_self_event("You have no spellcasting tradition to prepare from.")
            return
        spell_name = " ".join(args)
        spell_id = self.find_known_spell(spell_name)
        if spell_id is None:
            self.emit_self_event(f"You do not know '{spell_name}'.")
            return
        spell = SPELLS[spell_id]
        level_key = str(spell.spell_level)
        available_slots = self.available_spell_slots().get(spell.spell_level, 0)
        if available_slots <= 0:
            self.emit_self_event(f"You cannot prepare level {spell.spell_level} spells.")
            return
        prepared = self.player.prepared_spells.setdefault(level_key, [])
        while len(prepared) < available_slots:
            prepared.append(spell_id)
        prepared[0] = spell_id
        self.player.spell_slots_used[level_key] = min(self.player.spell_slots_used.get(level_key, 0), available_slots)
        self.emit_self_event(f"You prepare {spell.name}.")

    def show_quests(self) -> None:
        lines = ["Quest Journal"]
        if not self.player.active_quests and not self.player.completed_quests:
            lines.append("You have not taken on any quests.")
            self.set_room_view(*lines)
            return
        if self.player.active_quests:
            lines.append("Active:")
            for quest_id in self.player.active_quests:
                quest = QUESTS.get(quest_id)
                if quest is not None:
                    lines.append(f"- {quest['name']}: {quest['summary']}")
        if self.player.completed_quests:
            lines.append("Completed:")
            for quest_id in self.player.completed_quests:
                quest = QUESTS.get(quest_id)
                if quest is not None:
                    lines.append(f"- {quest['name']}")
        self.set_room_view(*lines)

    def rest(self) -> None:
        if "safe" not in self.current_room().tags:
            self.emit_self_event("This is no place to let down your guard.")
            return
        self.player.hp = self.player.max_hp
        self.player.stamina = self.player.max_stamina
        self.reset_spell_preparation()
        self.emit_self_event("You take time to rest, recover, and gather yourself.")

    def current_room(self):
        return self.world.rooms[self.player.room_id]

    def available_spell_slots(self) -> dict[int, int]:
        return self.player_snapshot().spell_slots

    def spell_slot_summary_line(self) -> str:
        slots = self.available_spell_slots()
        if not slots:
            return "Slots: none"
        parts = []
        for slot_level in sorted(slots):
            used = int(self.player.spell_slots_used.get(str(slot_level), 0))
            total = slots[slot_level]
            parts.append(f"L{slot_level} {max(0, total - used)}/{total}")
        return "Slots: " + "  ".join(parts)

    def reset_spell_preparation(self) -> None:
        slots = self.available_spell_slots()
        self.player.spell_slots_used = {str(slot_level): 0 for slot_level in slots}
        if not self.player.spellbook:
            self.player.prepared_spells = {}
            return
        prepared: dict[str, list[str]] = {}
        for slot_level, slot_count in slots.items():
            candidates = [spell_id for spell_id in self.player.spellbook if SPELLS[spell_id].spell_level == slot_level]
            prepared[str(slot_level)] = [
                candidates[index % len(candidates)]
                for index in range(slot_count)
            ] if candidates else []
        self.player.prepared_spells = prepared

    def find_prepared_spell(self, target: str) -> str | None:
        lowered = target.lower()
        for spell_ids in self.player.prepared_spells.values():
            for spell_id in spell_ids:
                spell = SPELLS.get(spell_id)
                if spell is None:
                    continue
                if lowered == spell_id or lowered == spell.name.lower() or lowered in spell.name.lower():
                    return spell_id
        return None

    def consume_prepared_spell(self, spell) -> bool:
        level_key = str(spell.spell_level)
        total_slots = self.available_spell_slots().get(spell.spell_level, 0)
        used = int(self.player.spell_slots_used.get(level_key, 0))
        if used >= total_slots:
            return False
        prepared = self.player.prepared_spells.get(level_key, [])
        if spell.id not in prepared:
            return False
        self.player.spell_slots_used[level_key] = used + 1
        return True

    def restore_spell_use(self, spell) -> None:
        level_key = str(spell.spell_level)
        self.player.spell_slots_used[level_key] = max(0, int(self.player.spell_slots_used.get(level_key, 0)) - 1)

    def cast_spell(self, args: list[str]) -> None:
        if not args:
            self.emit_self_event("Cast what?")
            return
        if not self.can_take_action(in_combat_message="You have no action left for spellcasting right now."):
            return
        spell_name = " ".join(args)
        spell_id = self.find_prepared_spell(spell_name)
        if spell_id is None:
            self.emit_self_event(f"You do not have '{spell_name}' prepared.")
            return
        spell = SPELLS[spell_id]
        if not self.consume_prepared_spell(spell):
            self.emit_self_event(f"You have no level {spell.spell_level} slots remaining.")
            return

        self.improve_proficiency(self.spell_skill_id(), 1)
        if spell.targeting == "self":
            healed = roll_spell_healing(spell)
            healed = min(healed, self.player.max_hp - self.player.hp)
            self.player.hp += healed
            self.spend_action()
            self.emit_self_event(f"You cast {spell.name}.")
            self.emit_self_event(f"{spell.description}")
            if healed > 0:
                self.emit_self_event(f"You recover {healed} hp.")
            else:
                self.emit_self_event("The magic washes over you, but you were already at full strength.")
            if self.combat is not None:
                self.end_player_turn()
            return

        monster = self.current_combatant() or next(iter(self.world.monsters_in_room(self.player.room_id)), None)
        if monster is None:
            self.emit_self_event("There is no worthy target here.")
            self.restore_spell_use(spell)
            return
        if self.combat is None:
            self.combat = CombatState(monster_id=monster.id, player_turn=False)
        self.resolve_player_spell(spell, monster)

    def resolve_player_spell(self, spell, monster: Monster) -> None:
        monster_stats = self.monster_snapshot(monster)
        self.spend_action()
        self.emit_self_event(f"You cast {spell.name} at {monster.name}.", kind="combat")
        self.emit_self_event(f"{spell.description}", kind="combat")
        if spell.attack_type == "auto":
            damage = max(1, roll_spell_damage(spell) + self.spellcasting_modifier(spell.id))
            monster.current_hp -= damage
            self.emit_self_event(f"The spell strikes true for {damage} damage.", kind="combat")
        elif spell.attack_type == "ranged_touch":
            attack_roll = roll_d20() + self.ranged_spell_attack_bonus()
            target_ac = monster_stats.touch_armor_class
            if attack_roll < target_ac:
                self.emit_self_event(f"{monster.name} twists aside from the spell.", kind="combat")
                if self.combat is not None:
                    self.combat.player_turn = False
                    self.resolve_monster_turn(monster)
                return
            damage = max(1, roll_spell_damage(spell) + self.spellcasting_modifier(spell.id))
            monster.current_hp -= damage
            self.emit_self_event(f"The spell hits for {damage} damage.", kind="combat")
        elif spell.saving_throw is not None:
            damage = max(1, roll_spell_damage(spell) + self.spellcasting_modifier(spell.id))
            dc = self.spell_save_dc(spell)
            save_total = self.monster_save_throw(monster, spell.saving_throw)
            if save_total >= dc:
                damage = max(1, damage // 2)
                self.emit_self_event(f"{monster.name} partially resists the spell.", kind="combat")
            monster.current_hp -= damage
            self.emit_self_event(f"The spell deals {damage} damage.", kind="combat")
        else:
            damage = max(1, roll_spell_damage(spell) + self.spellcasting_modifier(spell.id))
            monster.current_hp -= damage
            self.emit_self_event(f"The spell deals {damage} damage.", kind="combat")

        if monster.current_hp <= 0:
            self.defeat_monster(monster)
            return
        self.emit_self_event(wound_status_line(monster.name, monster.current_hp, monster_stats.max_hp), kind="combat")
        if self.combat is not None:
            self.end_player_turn()

    def player_has_item(self, item_id: str) -> bool:
        if item_id in self.player.inventory:
            return True
        if item_id in [equipped for equipped in self.player.equipment.values() if equipped]:
            return True
        return self.player.wielded_item_id == item_id

    def remove_item_by_id(self, item_id: str) -> None:
        if item_id in self.player.inventory:
            self.player.inventory.remove(item_id)
        if self.player.wielded_item_id == item_id:
            self.player.wielded_item_id = None
        self.clear_equipped_item(item_id)

    def sit_down(self) -> None:
        if self.player.posture == "sitting":
            self.emit_self_event("You are already sitting.")
            return
        self.player.posture = "sitting"
        self.player.stamina = min(self.player.max_stamina, self.player.stamina + 5)
        self.emit_self_event("You sit down.")
        self.emit_room_event(self.player.room_id, f"{self.player.name} sits down.", kind="posture")

    def stand_up(self) -> None:
        if self.player.posture == "standing":
            self.emit_self_event("You are already standing.")
            return
        self.player.posture = "standing"
        self.emit_self_event("You stand up.")
        self.emit_room_event(self.player.room_id, f"{self.player.name} stands up.", kind="posture")

    def recover_stamina(self) -> None:
        recovery = 3 if self.player.posture == "sitting" else 1
        self.player.stamina = min(self.player.max_stamina, self.player.stamina + recovery)

    def take_item(self, args: list[str]) -> None:
        if not args:
            self.emit_self_event("Get what?")
            return

        target = " ".join(args)
        item = self.find_item(target, include_inventory=False)
        if item is None or item.room_id != self.player.room_id:
            self.emit_self_event(f"You do not see '{target}' here.")
            return
        if not item.portable:
            self.emit_self_event(f"You cannot take the {item.name}.")
            return

        item.room_id = None
        self.player.inventory.append(item.id)
        self.emit_self_event(f"You pick up {item.name}.")
        self.emit_room_event(self.player.room_id, f"{self.player.name} picks up {item.name}.", kind="item")

    def drop_item(self, args: list[str]) -> None:
        if not args:
            self.emit_self_event("Drop what?")
            return

        target = " ".join(args)
        for item_id in list(self.player.inventory):
            item = self.world.items[item_id]
            if matches(target, item.name, item.keywords):
                self.player.inventory.remove(item_id)
                if self.player.wielded_item_id == item_id:
                    self.player.wielded_item_id = None
                self.clear_equipped_item(item_id)
                item.room_id = self.player.room_id
                self.emit_self_event(f"You drop {item.name}.")
                self.emit_room_event(self.player.room_id, f"{self.player.name} drops {item.name}.", kind="item")
                return

        self.emit_self_event(f"You are not carrying '{target}'.")

    def equip_item(self, args: list[str]) -> None:
        if not args:
            if self.player.wielded_item_id and self.player.wielded_item_id in self.world.items:
                item = self.world.items[self.player.wielded_item_id]
                self.emit_self_event(f"You have {item.name} readied.")
            else:
                self.emit_self_event("You have nothing readied.")
            return

        target = " ".join(args)
        for item_id in self.player.inventory:
            item = self.world.items[item_id]
            if not matches(target, item.name, item.keywords):
                continue
            if item.kind == "weapon":
                self.player.wielded_item_id = item_id
                self.emit_self_event(f"You wield {item.name}.")
                self.emit_room_event(self.player.room_id, f"{self.player.name} readies {item.name}.", kind="equipment")
                return
            slot = choose_equipment_slot(item, self.player.equipment)
            if slot is not None:
                current = self.player.equipment.get(slot)
                if current == item_id:
                    self.emit_self_event(f"You are already using {item.name}.")
                    return
                self.player.equipment[slot] = item_id
                self.emit_self_event(f"You wear {item.name}.")
                self.emit_room_event(self.player.room_id, f"{self.player.name} adjusts {item.name}.", kind="equipment")
                return
            self.emit_self_event(f"You cannot make use of the {item.name} that way.")
            return

        self.emit_self_event(f"You are not carrying '{target}'.")

    def wear_item(self, args: list[str]) -> None:
        self.equip_item(args)

    def remove_item(self, args: list[str]) -> None:
        if not args:
            self.emit_self_event("Remove what?")
            return

        target = " ".join(args)
        if target in self.player.equipment:
            item_id = self.player.equipment[target]
            if item_id and item_id in self.world.items:
                self.player.equipment[target] = None
                self.emit_self_event(f"You remove {self.world.items[item_id].name}.")
                self.emit_room_event(self.player.room_id, f"{self.player.name} removes {self.world.items[item_id].name}.", kind="equipment")
            else:
                self.emit_self_event(f"You are wearing nothing on your {target}.")
            return

        for slot, item_id in self.player.equipment.items():
            if not item_id or item_id not in self.world.items:
                continue
            item = self.world.items[item_id]
            if matches(target, item.name, item.keywords):
                self.player.equipment[slot] = None
                self.emit_self_event(f"You remove {item.name}.")
                self.emit_room_event(self.player.room_id, f"{self.player.name} removes {item.name}.", kind="equipment")
                return

        self.emit_self_event(f"You are not wearing '{target}'.")

    def talk(self, args: list[str]) -> None:
        if not args:
            self.emit_self_event("Talk to whom?")
            return

        target = " ".join(args)
        npc = self.find_npc(target)
        if npc is None:
            self.emit_self_event(f"No one named '{target}' is here.")
            return

        if npc.id == "brother_nim":
            self.handle_brother_nim_dialogue()
            return

        if npc.id == "elis_baker" and "applehill_stolen_token" in self.player.active_quests:
            self.emit_self_event('Elis says, "If the temple token is with the goblins, their camp will be deeper in among the trees."')
            self.emit_self_event("He dusts flour from his hands and nods toward the orchard.")
            return

        if npc.id == "halfen_orchard_keeper" and "applehill_stolen_token" in self.player.active_quests:
            self.emit_self_event('Halfen says, "Look for the worst of the damage. Goblins nest where they can spoil the most."')
            return

        self.emit_self_event(f"{npc.name} says, \"{npc.dialogue[0]}\"")
        if npc.quest_hint:
            self.emit_self_event(f"You gather this much: {npc.quest_hint}")

    def say(self, args: list[str]) -> None:
        if not args:
            self.emit_self_event("Say what?")
            return
        spoken = format_spoken_text(" ".join(args))
        self.emit_self_event(f"You say, '{spoken}'", kind="social")
        self.emit_room_event(self.player.room_id, f"{self.player.name} says, '{spoken}'", kind="social")

    def say_to(self, args: list[str]) -> None:
        if len(args) < 2:
            self.emit_self_event("Say to whom what?")
            return
        target, message = self.resolve_character_target_and_message(args)
        if target is None or not message:
            self.emit_self_event("Say to whom what?")
            return
        spoken = format_spoken_text(message)
        self.emit_self_event(f"You say to {target.name}, '{spoken}'", kind="social")
        self.emit_target_event(target.id, f"{self.player.name} says to you, '{spoken}'", kind="social")
        self.emit_room_event(self.player.room_id, f"{self.player.name} says to {target.name}, '{spoken}'", kind="social")

    def perform_social(self, social_id: str, args: list[str]) -> None:
        social = SOCIALS[social_id]
        if not args:
            self.emit_self_event(social["no_target"]["self"], kind="social")
            self.emit_room_event(
                self.player.room_id,
                social["no_target"]["room"].format(actor=self.player.name),
                kind="social",
            )
            return
        target = self.find_room_character(" ".join(args))
        if target is None:
            self.emit_self_event(f"No one named '{' '.join(args)}' is here.")
            return
        self.emit_self_event(
            social["target"]["self"].format(target=target.name),
            kind="social",
        )
        self.emit_target_event(
            target.id,
            social["target"]["target"].format(actor=self.player.name),
            kind="social",
        )
        self.emit_room_event(
            self.player.room_id,
            social["target"]["room"].format(actor=self.player.name, target=target.name),
            kind="social",
        )

    def handle_brother_nim_dialogue(self) -> None:
        quest_id = "applehill_stolen_token"
        quest = QUESTS[quest_id]
        if quest_id in self.player.completed_quests:
            self.emit_self_event('Brother Nim says, "Applehill still speaks well of your help in the orchard."')
            return
        if self.player_has_item(str(quest["required_item_id"])):
            for line in quest["complete_text"]:
                self.emit_self_event(line)
            self.remove_item_by_id(str(quest["required_item_id"]))
            reward_item_id = str(quest["reward_item_id"])
            if reward_item_id not in self.player.inventory:
                reward_item = self.world.items.get(reward_item_id)
                if reward_item is not None:
                    reward_item.room_id = None
                    self.player.inventory.append(reward_item_id)
                    self.emit_self_event(f"You receive {reward_item.name}.")
            self.gain_experience(int(quest["reward_xp"]))
            self.player.active_quests.pop(quest_id, None)
            self.player.completed_quests.append(quest_id)
            return
        if quest_id not in self.player.active_quests:
            self.player.active_quests[quest_id] = "active"
            for line in quest["accept_text"]:
                self.emit_self_event(line)
            return
        for line in quest["progress_text"]:
            self.emit_self_event(line)

    def attack(self, args: list[str]) -> None:
        if self.combat is None:
            if not args:
                self.emit_self_event("Kill what?")
                return
            target = " ".join(args)
            monster = self.find_monster(target)
            if monster is None:
                self.emit_self_event(f"No foe named '{target}' is here.")
                return
            self.start_combat(monster)
            return

        monster = self.current_combatant()
        if monster is None:
            self.combat = None
            self.emit_self_event("The fight is already over.")
            return
        if not self.can_take_action(in_combat_message="You have already committed yourself this turn."):
            return
        self.resolve_player_attack(monster)

    def defeat_monster(self, monster: Monster) -> None:
        room_id = monster.room_id
        self.emit_self_event(f"{monster.name} is DEAD!", kind="combat")
        for item_id in monster.loot_table:
            item = self.world.items.get(item_id)
            if item is None:
                continue
            if item.room_id is None:
                item.room_id = room_id
        monster.room_id = "__defeated__"
        self.emit_self_event("The corpse collapses, leaving loot behind.", kind="combat")
        self.combat = None
        self.gain_experience(monster_experience_value(monster))

    def eat(self, args: list[str]) -> None:
        if not args:
            self.emit_self_event("Eat what?")
            return
        if not self.can_take_action(in_combat_message="You cannot manage that right now."):
            return

        target = " ".join(args)
        for item_id in list(self.player.inventory):
            item = self.world.items[item_id]
            if not matches(target, item.name, item.keywords):
                continue
            if item.kind != "food":
                self.emit_self_event(f"You cannot eat the {item.name}.")
                return

            self.player.inventory.remove(item_id)
            if self.player.wielded_item_id == item_id:
                self.player.wielded_item_id = None
            self.clear_equipped_item(item_id)
            healed = min(3, self.player.max_hp - self.player.hp)
            self.player.hp += healed
            self.player.stamina = min(self.player.max_stamina, self.player.stamina + 10)
            self.emit_self_event(f"You eat {item.name}.")
            if healed > 0:
                self.emit_self_event(f"You recover {healed} hp. ({self.player.hp}/{self.player.max_hp} hp)")
            else:
                self.emit_self_event("You feel full, if not any healthier.")
            if self.combat is not None:
                self.spend_action()
                self.end_player_turn()
            return

        self.emit_self_event(f"You are not carrying '{target}'.")

    def show_help(self) -> None:
        self.emit_self_event(
            "Use n s e w u d to move, look or l to inspect, get/drop for items, "
            "inv/i for inventory, eq for equipment, score for your sheet, "
            "wear/wield/equip <item>, remove <item>, talk <name>, quests, kill <target>, "
            "say <message>, sayto <target> <message>, socials like wave/smile/hug, "
            "eat <food>, rest, spells, prepare <spell>, cast <spell>, save, and quit to leave."
        )

    def start_combat(self, monster: Monster) -> None:
        player_init = roll_d20() + self.player_snapshot().ability_modifiers["dexterity"]
        monster_init = roll_d20() + self.monster_snapshot(monster).initiative_bonus
        player_turn = player_init >= monster_init
        self.combat = CombatState(monster_id=monster.id, player_turn=player_turn)
        self.emit_self_event(f"You approach {monster.name} and prepare to engage in combat!", kind="combat")
        self.emit_self_event(f"Initiative: you {player_init}, {monster.name} {monster_init}.", kind="combat")
        if player_turn:
            self.begin_player_turn(opening=True)
        else:
            self.emit_self_event(f"{monster.name} lunges first.", kind="combat")
            self.resolve_monster_turn(monster)

    def begin_player_turn(self, *, opening: bool = False) -> None:
        if self.combat is None:
            return
        self.combat.player_turn = True
        self.combat.turn_actions_remaining = 1
        self.combat.turn_movement_remaining = 1
        if opening:
            self.emit_self_event("You seize the first opening.", kind="combat")
        else:
            self.emit_self_event("A brief opening appears. You may act.", kind="combat")
        self.emit_self_event(self.action_summary_line(), kind="combat")

    def end_player_turn(self) -> None:
        if self.combat is None:
            return
        self.combat.player_turn = False
        self.combat.turn_actions_remaining = 0
        self.combat.turn_movement_remaining = 0
        monster = self.current_combatant()
        if monster is not None:
            self.resolve_monster_turn(monster)

    def current_combatant(self) -> Monster | None:
        if self.combat is None:
            return None
        monster = self.world.monsters.get(self.combat.monster_id)
        if monster is None or monster.room_id != self.player.room_id:
            return None
        return monster

    def resolve_player_attack(self, monster: Monster) -> None:
        player_stats = self.player_snapshot()
        monster_stats = self.monster_snapshot(monster)
        attack_roll = roll_d20() + player_stats.melee_attack_bonus
        target_ac = monster_stats.armor_class
        weapon = self.wielded_weapon()
        self.improve_proficiency(weapon_skill_id(weapon), 1)
        self.emit_self_event(f"You press the attack against {monster.name}.", kind="combat")
        if attack_roll >= target_ac:
            damage = self.roll_player_damage(weapon)
            monster.current_hp -= damage
            self.player.stamina = max(0, self.player.stamina - 5)
            self.emit_self_event(player_hit_line(monster, weapon, damage), kind="combat")
            if monster.current_hp <= 0:
                self.defeat_monster(monster)
                return
            self.emit_self_event(
                wound_status_line(monster.name, monster.current_hp, monster_stats.max_hp),
                kind="combat",
            )
        else:
            self.player.stamina = max(0, self.player.stamina - 3)
            self.emit_self_event(player_miss_line(monster, weapon), kind="combat")

        if self.combat is not None:
            self.spend_action()
            self.end_player_turn()

    def resolve_monster_turn(self, monster: Monster) -> None:
        monster_stats = self.monster_snapshot(monster)
        player_stats = self.player_snapshot()
        attack_roll = roll_d20() + monster_stats.attack_bonus
        target_ac = player_stats.armor_class_breakdown["total"]
        self.emit_self_event(f"{monster.name} surges back into the fight.", kind="combat")
        if attack_roll >= target_ac:
            damage = roll_monster_damage(monster)
            self.player.hp = max(0, self.player.hp - damage)
            self.emit_self_event(monster_hit_line(monster, damage), kind="combat")
            self.emit_self_event(player_wound_line(self.player.hp, self.player.max_hp), kind="combat")
        else:
            self.emit_self_event(monster_miss_line(monster), kind="combat")

        if self.player.hp <= 0:
            self.handle_player_defeat()
            return
        if self.combat is not None:
            self.combat.round_number += 1
            self.begin_player_turn()

    def attempt_flee(self, direction: str) -> None:
        room = self.world.rooms[self.player.room_id]
        if direction not in room.exits:
            self.emit_self_event("You cannot flee that way.")
            return
        monster = self.current_combatant()
        if monster is None:
            self.combat = None
            self.move(direction)
            return
        if self.combat is not None and (not self.combat.player_turn or self.combat.turn_movement_remaining <= 0):
            self.emit_self_event("You have no opening to break away right now.")
            return
        flee_roll = roll_d20() + self.player_snapshot().ability_modifiers["dexterity"]
        hold_roll = roll_d20() + self.monster_snapshot(monster).attack_bonus
        if flee_roll >= hold_roll:
            old_room = self.player.room_id
            new_room = room.exits[direction]
            self.emit_room_event(old_room, departure_text(self.player.name, direction), kind="departure")
            self.emit_room_event(new_room, arrival_text(self.player.name, opposite_direction(direction)), kind="arrival")
            self.player.room_id = room.exits[direction]
            self.player.facing = direction if direction in {"north", "south", "east", "west"} else self.player.facing
            self.player.posture = "standing"
            self.spend_movement()
            self.combat = None
            self.set_room_view(f"You flee {direction}.")
            return
        self.emit_self_event(f"{monster.name} cuts off your escape!", kind="combat")
        if self.combat is not None:
            self.spend_action()
            self.spend_movement()
        self.resolve_monster_turn(monster)

    def handle_player_defeat(self) -> None:
        self.player.hp = self.player.max_hp
        self.player.stamina = self.player.max_stamina
        self.player.room_id = self.world.zone.starting_room
        self.player.facing = "north"
        self.player.posture = "standing"
        self.player.wielded_item_id = None
        for slot in self.player.equipment:
            self.player.equipment[slot] = None
        self.combat = None
        self.set_room_view("You collapse and later wake back in the village center, battered but alive.")

    def find_item(self, target: str, include_inventory: bool) -> Item | None:
        candidate_items = []
        candidate_items.extend(self.world.items_in_room(self.player.room_id))
        if include_inventory:
            candidate_items.extend(
                self.world.items[item_id] for item_id in self.player.inventory if item_id in self.world.items
            )
        for item in candidate_items:
            if matches(target, item.name, item.keywords):
                return item
        return None

    def find_npc(self, target: str) -> Npc | None:
        for npc in self.world.npcs_in_room(self.player.room_id):
            if matches(target, npc.name, npc.keywords):
                return npc
        return None

    def find_room_character(self, target: str):
        npc = self.find_npc(target)
        if npc is not None:
            return npc
        return None

    def resolve_character_target_and_message(self, args: list[str]):
        for index in range(len(args), 0, -1):
            candidate_target = " ".join(args[:index])
            target = self.find_room_character(candidate_target)
            if target is not None:
                message = " ".join(args[index:]).strip()
                return target, message
        return None, ""

    def find_monster(self, target: str) -> Monster | None:
        for monster in self.world.monsters_in_room(self.player.room_id):
            if matches(target, monster.name, monster.keywords):
                return monster
        return None

    def best_weapon(self) -> Item | None:
        weapons = [
            self.world.items[item_id]
            for item_id in self.player.inventory
            if item_id in self.world.items and self.world.items[item_id].kind == "weapon"
        ]
        if not weapons:
            return None
        weapons.sort(key=lambda item: (item.value, -item.weight), reverse=True)
        return weapons[0]

    def wielded_weapon(self) -> Item | None:
        item_id = self.player.wielded_item_id
        if item_id is None:
            return None
        if item_id not in self.world.items:
            self.player.wielded_item_id = None
            return None
        if item_id not in self.player.inventory:
            self.player.wielded_item_id = None
            return None
        item = self.world.items[item_id]
        if item.kind != "weapon":
            self.player.wielded_item_id = None
            return None
        return item

    def player_attack_power(self) -> int:
        return self.player_snapshot().attack_power

    def player_attack_bonus(self) -> int:
        return self.player_snapshot().melee_attack_bonus

    def player_defense_value(self) -> int:
        return max(1, self.player_ac_breakdown()["total"] - 10)

    def player_armor_class(self) -> int:
        return self.player_snapshot().armor_class_breakdown["total"]

    def monster_armor_class(self, monster: Monster) -> int:
        return self.monster_snapshot(monster).armor_class

    def roll_player_damage(self, weapon: Item | None) -> int:
        damage = roll_weapon_damage(weapon) + self.player_snapshot().ability_modifiers["strength"]
        return max(1, damage)

    def clear_equipped_item(self, item_id: str) -> None:
        for slot, equipped_item_id in self.player.equipment.items():
            if equipped_item_id == item_id:
                self.player.equipment[slot] = None

    def inventory_weight(self) -> float:
        return self.player_snapshot().carry_weight

    def load_label(self) -> str:
        return self.player_snapshot().load_label

    def player_size(self) -> str:
        return self.player_snapshot().size

    def base_attack_bonus(self) -> int:
        return self.player_snapshot().base_attack_bonus

    def melee_attack_ability_modifier(self) -> int:
        return self.player_snapshot().ability_modifiers["strength"]

    def ranged_attack_ability_modifier(self) -> int:
        return self.player_snapshot().ability_modifiers["dexterity"]

    def ranged_spell_attack_bonus(self) -> int:
        return self.player_snapshot().ranged_spell_attack_bonus

    def spellcasting_modifier_for_class(self) -> int:
        return self.player_snapshot().spellcasting_modifier

    def spell_save_dc(self, spell) -> int:
        return 10 + spell.spell_level + self.spellcasting_modifier_for_class()

    def max_carry_weight(self) -> float:
        return self.player_snapshot().max_carry_weight

    def player_save_throw(self, save_name: str) -> int:
        return self.player_snapshot().saves[save_name]

    def player_ac_breakdown(self) -> dict[str, int]:
        return self.player_snapshot().armor_class_breakdown

    def player_touch_armor_class(self) -> int:
        return self.player_snapshot().touch_armor_class

    def monster_touch_armor_class(self, monster: Monster) -> int:
        return self.monster_snapshot(monster).touch_armor_class

    def monster_save_throw(self, monster: Monster, save_name: str) -> int:
        return roll_d20() + getattr(self.monster_snapshot(monster), f"{save_name}_save")

    def find_known_spell(self, target: str) -> str | None:
        lowered = target.lower()
        for spell_id in self.player.spellbook:
            spell = SPELLS.get(spell_id)
            if spell is None:
                continue
            if lowered == spell_id or lowered == spell.name.lower():
                return spell_id
            if lowered in spell.name.lower():
                return spell_id
        return None

    def spellcasting_modifier(self, spell_id: str) -> int:
        spell = SPELLS[spell_id]
        class_def = CLASSES.get(self.player.class_id, CLASSES["fighter"])
        if class_def.spellcasting_ability is None:
            return 0
        if self.player.class_id not in spell.caster_lists:
            return 0
        return self.spellcasting_modifier_for_class()

    def spell_skill_id(self) -> str:
        if self.player.class_id == "wizard":
            return "arcane_magic"
        if self.player.class_id == "cleric":
            return "divine_magic"
        return "spellcasting"

    def improve_proficiency(self, skill_id: str, amount: int) -> None:
        entry = self.player.proficiencies.setdefault(
            skill_id,
            {"level": 1, "title": proficiency_title(1), "progress": 0},
        )
        progress = int(entry.get("progress", 0)) + amount
        level = int(entry.get("level", 1))
        threshold = max(3, level * 2)
        while progress >= threshold and level < 25:
            progress -= threshold
            level += 1
            threshold = max(3, level * 2)
            self.emit_self_event(f"Your {skill_id.replace('_', ' ')} rises to {proficiency_title(level)}.")
        entry["level"] = level
        entry["title"] = proficiency_title(level)
        entry["progress"] = progress

    def gain_experience(self, amount: int) -> None:
        if amount <= 0:
            return
        self.player.experience += amount
        self.emit_self_event(f"You gain {amount} experience.")
        self.check_level_up()

    def check_level_up(self) -> None:
        class_def = CLASSES.get(self.player.class_id, CLASSES["fighter"])
        while self.player.experience >= experience_to_next_level(self.player.level):
            self.player.experience -= experience_to_next_level(self.player.level)
            self.player.level += 1
            hp_gain = max(1, class_def.hit_die // 2 + ability_modifier(self.player.stats["constitution"]))
            self.player.max_hp += hp_gain
            self.player.hp = self.player.max_hp
            self.reset_spell_preparation()
            if self.player.level % 5 == 0:
                self.player.stat_points_available += 1
                self.player.feat_points += 1
            self.emit_self_event(f"You have reached level {self.player.level}!")
            self.emit_self_event(f"You gain {hp_gain} maximum hit points.")


def matches(target: str, name: str, keywords: list[str]) -> bool:
    lowered = target.lower()
    if lowered == name.lower():
        return True
    if lowered in {keyword.lower() for keyword in keywords}:
        return True
    return lowered in name.lower()


def weapon_bonus(item: Item) -> int:
    if "damage_bonus" in item.weapon_stats:
        return int(item.weapon_stats["damage_bonus"])
    name = item.name.lower()
    if "knife" in name or "dagger" in name:
        return 3
    if "club" in name:
        return 2
    if "sling" in name:
        return 2
    return 2


def weapon_accuracy_bonus(item: Item | None) -> int:
    if item is None:
        return 0
    if "attack_bonus" in item.weapon_stats:
        return int(item.weapon_stats["attack_bonus"])
    name = item.name.lower()
    if "knife" in name or "dagger" in name:
        return 1
    if "club" in name:
        return 0
    if "sling" in name:
        return 1
    return 0


def roll_weapon_damage(item: Item | None) -> int:
    if item is None:
        return 1 + random.randint(0, 1)
    if item.weapon_stats:
        dice_count = int(item.weapon_stats.get("dice_count", 1))
        dice_sides = int(item.weapon_stats.get("dice_sides", 4))
        flat_bonus = int(item.weapon_stats.get("damage_bonus", 0))
        return sum(random.randint(1, dice_sides) for _ in range(max(1, dice_count))) + flat_bonus
    name = item.name.lower()
    if "knife" in name or "dagger" in name:
        return random.randint(1, 4)
    if "club" in name:
        return random.randint(1, 6)
    if "sling" in name:
        return random.randint(1, 4)
    return random.randint(1, 4)


def roll_monster_damage(monster: Monster) -> int:
    profile = monster_combat_profile(monster)
    dice_count = max(1, profile["dice_count"])
    dice_sides = max(2, profile["dice_sides"])
    flat_bonus = profile["damage_bonus"]
    return max(1, sum(random.randint(1, dice_sides) for _ in range(dice_count)) + flat_bonus)


def roll_d20() -> int:
    return random.randint(1, 20)


def monster_attack_bonus(monster: Monster) -> int:
    return monster_combat_profile(monster)["attack_bonus"]


def monster_defense_bonus(monster: Monster) -> int:
    return monster_combat_profile(monster)["defense_bonus"]


def monster_initiative_bonus(monster: Monster) -> int:
    profile = monster_combat_profile(monster)
    return profile["initiative_bonus"]


def monster_armor_class_value(monster: Monster) -> int:
    profile = monster_combat_profile(monster)
    return 10 + profile["defense_bonus"] + profile["size_modifier"] + profile["deflection_bonus"]


def monster_max_hp(monster: Monster) -> int:
    return max(1, int(monster.stats.get("hp", 1)))


def monster_combat_profile(monster: Monster) -> dict[str, int]:
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
    return {
        "attack_bonus": attack_bonus,
        "defense_bonus": defense_bonus,
        "dexterity_modifier": dexterity_modifier,
        "size_modifier": size_modifier,
        "deflection_bonus": deflection_bonus,
        "fortitude_save": fortitude_save,
        "reflex_save": reflex_save,
        "will_save": will_save,
        "dice_count": dice_count,
        "dice_sides": dice_sides,
        "damage_bonus": damage_bonus,
        "initiative_bonus": initiative_bonus,
    }


def player_hit_line(monster: Monster, weapon: Item | None, damage: int) -> str:
    damage_type = weapon_damage_type(weapon)
    body_part = random.choice(["left arm", "right arm", "abdomen", "shoulder", "leg", "head", "chest"])
    verb = hit_verb(damage_type, damage)
    return f"Your {damage_type} {verb} {monster.name}'s {body_part}."


def player_miss_line(monster: Monster, weapon: Item | None) -> str:
    attack_name = attack_noun(weapon)
    return f"{monster.name} evades your {attack_name} attack."


def monster_hit_line(monster: Monster, damage: int) -> str:
    body_part = random.choice(["left arm", "right arm", "abdomen", "shoulder", "leg", "head", "side"])
    verb_choices = monster.combat.get("attack_verbs", []) if monster.combat else []
    if isinstance(verb_choices, list) and verb_choices:
        verb = random.choice([str(choice) for choice in verb_choices])
    else:
        verb = random.choice(["bites", "slashes", "clubs", "cuts", "stabs", "mauls"])
    return f"{monster.name}'s attack {verb} your {body_part}."


def monster_miss_line(monster: Monster) -> str:
    attack_name = random.choice(["wild", "lunging", "clumsy", "snapping"])
    return f"{monster.name} misses you with a {attack_name} attack."


def wound_status_line(name: str, current_hp: int, max_hp: int) -> str:
    ratio = current_hp / max_hp if max_hp else 0
    if ratio <= 0.1:
        return f"{name} is leaking heart-blood and will die soon if not aided."
    if ratio <= 0.25:
        return f"{name} is mortally wounded."
    if ratio <= 0.45:
        return f"{name} is grievously wounded."
    if ratio <= 0.7:
        return f"{name} is badly wounded."
    return f"{name} is wounded."


def player_wound_line(current_hp: int, max_hp: int) -> str:
    ratio = current_hp / max_hp if max_hp else 0
    if ratio <= 0:
        return "You are DEAD!"
    if ratio <= 0.1:
        return "You are leaking heart-blood and may die without aid."
    if ratio <= 0.25:
        return "You are mortally wounded."
    if ratio <= 0.45:
        return "You are grievously wounded."
    if ratio <= 0.7:
        return "You are badly wounded."
    return "You are wounded."


def weapon_damage_type(item: Item | None) -> str:
    if item is None:
        return "strike"
    if "damage_type" in item.weapon_stats:
        return str(item.weapon_stats["damage_type"])
    name = item.name.lower()
    if "knife" in name or "dagger" in name:
        return "pierce"
    if "sling" in name:
        return "shot"
    if "club" in name:
        return "crush"
    return "strike"


def hit_verb(damage_type: str, damage: int) -> str:
    if damage_type == "pierce":
        if damage >= 6:
            return "eviscerates"
        if damage >= 4:
            return "cuts"
        return "nicks"
    if damage_type == "shot":
        if damage >= 5:
            return "crushes"
        if damage >= 3:
            return "cracks"
        return "clips"
    if damage_type == "crush":
        if damage >= 6:
            return "beats"
        if damage >= 4:
            return "crushes"
        return "clips"
    if damage >= 6:
        return "smashes"
    if damage >= 4:
        return "strikes"
    return "clips"


def opposite_direction(direction: str) -> str:
    return {
        "north": "south",
        "south": "north",
        "east": "west",
        "west": "east",
        "up": "below",
        "down": "above",
    }.get(direction, "somewhere")


def arrival_text(name: str, from_direction: str) -> str:
    return f"{name} walks in from the {from_direction}."


def departure_text(name: str, direction: str) -> str:
    return f"{name} leaves {direction}."


def armor_bonus(item: Item) -> int:
    if item.armor_bonus_value:
        return item.armor_bonus_value
    name = item.name.lower()
    if "lid" in name:
        return 1
    if "cap" in name:
        return 1
    if item.kind == "armor":
        return 1
    return 0


def item_ac_bonus_types(item: Item) -> dict[str, int]:
    return derived_item_ac_bonus_types(item)


def wearable_slot(item: Item) -> str | None:
    if item.equip_slots:
        return item.equip_slots[0]
    name = item.name.lower()
    if "ring" in name:
        return "finger_1"
    if "glitter" in name or "mask" in name or "veil" in name:
        return "face"
    if "amulet" in name or "beads" in name:
        return "around_neck"
    if "pendant" in name or "holy symbol" in name or "symbol" in name:
        return "symbol"
    if item.kind == "armor":
        if "cap" in name or "helm" in name or "hat" in name:
            return "head"
        if "sleeve" in name or "bracer" in name:
            return "arms"
        if "glove" in name or "gauntlet" in name:
            return "hands"
        if "boot" in name or "shoe" in name or "sandal" in name:
            return "feet"
        if "trouser" in name or "legging" in name or "pants" in name:
            return "legs"
        if "belt" in name or "sash" in name:
            return "waist"
        if "bracelet" in name:
            return "wrist_1"
        if "lid" in name or "shield" in name:
            return "offhand"
        return "body"
    if item.kind == "trinket":
        if "token" in name or "charm" in name:
            return "neck"
        if "stone" in name:
            return "floating"
    if item.kind == "tool":
        if "spellbook" in name or "pouch" in name:
            return "belt_1"
    return None


def stat_bonus(score: int) -> int:
    return ability_modifier(score)


def carry_capacity_for_strength(score: int) -> tuple[int, int, int]:
    return strength_carry_limits(score)


def abbr(stat: str) -> str:
    return {
        "strength": "Str",
        "dexterity": "Dex",
        "constitution": "Con",
        "intelligence": "Int",
        "wisdom": "Wis",
        "charisma": "Cha",
    }[stat]


def weapon_skill_id(item: Item | None) -> str:
    if item is None:
        return "brawling"
    if item.weapon_skill:
        return item.weapon_skill
    skill = item.weapon_stats.get("skill_id") if isinstance(item.weapon_stats, dict) else None
    if skill:
        return str(skill)
    name = item.name.lower()
    if "knife" in name or "dagger" in name:
        return "short_blades"
    if "sling" in name:
        return "slings"
    if "staff" in name:
        return "staves"
    return "clubs"


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


def roll_spell_damage(spell) -> int:
    effects = spell.effects
    return sum(
        random.randint(1, int(effects.get("damage_dice_sides", 4)))
        for _ in range(max(1, int(effects.get("damage_dice_count", 1))))
    ) + int(effects.get("damage_bonus", 0))


def roll_spell_healing(spell) -> int:
    effects = spell.effects
    return sum(
        random.randint(1, int(effects.get("heal_dice_sides", 8)))
        for _ in range(max(1, int(effects.get("heal_dice_count", 1))))
    ) + int(effects.get("heal_bonus", 0))


def monster_experience_value(monster: Monster) -> int:
    profile = monster_combat_profile(monster)
    hp_value = monster_max_hp(monster) * 8
    pressure_value = profile["attack_bonus"] * 10 + profile["damage_bonus"] * 8
    resilience_value = profile["defense_bonus"] * 6 + profile["fortitude_save"] * 4 + profile["reflex_save"] * 4 + profile["will_save"] * 4
    return max(25, hp_value + pressure_value + resilience_value)


def format_spoken_text(text: str) -> str:
    cleaned = text.strip().strip("\"'")
    if not cleaned:
        return ""
    cleaned = cleaned[0].upper() + cleaned[1:]
    if cleaned[-1] not in ".!?":
        cleaned += "."
    return cleaned


EQUIPMENT_DISPLAY_ORDER = [
    "finger_1",
    "finger_2",
    "face",
    "around_neck",
    "neck",
    "symbol",
    "body",
    "head",
    "arms",
    "hands",
    "waist",
    "legs",
    "feet",
    "wrist_1",
    "wrist_2",
    "offhand",
    "belt_1",
    "belt_2",
    "floating",
]


def slot_display_label(slot: str) -> str:
    return {
        "finger_1": "<worn on finger>",
        "finger_2": "<worn on finger>",
        "face": "<worn around face>",
        "around_neck": "<worn around neck>",
        "neck": "<worn on neck>",
        "symbol": "<worn as symbol>",
        "body": "<worn on body>",
        "head": "<worn on head>",
        "legs": "<worn on legs>",
        "feet": "<worn on feet>",
        "hands": "<worn on hands>",
        "arms": "<worn on arms>",
        "waist": "<worn about waist>",
        "wrist_1": "<worn around wrist>",
        "wrist_2": "<worn around wrist>",
        "offhand": "<offhand>",
        "belt_1": "<worn on belt>",
        "belt_2": "<worn on belt>",
        "floating": "<floating around>",
        "weapon": "<both hands>",
    }[slot]


def choose_equipment_slot(item: Item, equipment: dict[str, str | None]) -> str | None:
    preferred_slots = item.equip_slots or ([wearable_slot(item)] if wearable_slot(item) is not None else [])
    if not preferred_slots:
        return None
    for preferred in preferred_slots:
        if preferred == "finger_1":
            if equipment["finger_1"] is None:
                return "finger_1"
            if equipment["finger_2"] is None:
                return "finger_2"
            continue
        if preferred == "wrist_1":
            if equipment["wrist_1"] is None:
                return "wrist_1"
            if equipment["wrist_2"] is None:
                return "wrist_2"
            continue
        if preferred == "belt_1":
            if equipment["belt_1"] is None:
                return "belt_1"
            if equipment["belt_2"] is None:
                return "belt_2"
            continue
        if equipment.get(preferred) is None:
            return preferred
    return None


def equipped_item_name(world: World, player: Player, slot: str) -> str:
    item_id = player.equipment.get(slot)
    if not item_id or item_id not in world.items:
        return "none"
    return world.items[item_id].name


def item_flags(item: Item) -> list[str]:
    if item.flags:
        return item.flags
    flags: list[str] = []
    name = item.name.lower()
    if item.kind in {"trinket", "quest"} or "prayer" in name or "token" in name:
        flags.append("Magical")
    if "gold" in name or "brass" in name or "sun" in name:
        flags.append("Glowing")
    if "bell" in name or "beads" in name:
        flags.append("Humming")
    return flags


def format_item_summary(item: Item) -> str:
    parts = [f"({flag})" for flag in item_flags(item)]
    parts.append(item.name)
    parts.append(f"({item.condition})")
    return " ".join(parts)


def weapon_damage_text(item: Item | None) -> str:
    if item is None:
        return "1d2"
    if item.weapon_stats:
        dice_count = int(item.weapon_stats.get("dice_count", 1))
        dice_sides = int(item.weapon_stats.get("dice_sides", 4))
        bonus = int(item.weapon_stats.get("damage_bonus", 0))
        return f"{dice_count}d{dice_sides}" + (f"+{bonus}" if bonus > 0 else "")
    name = item.name.lower()
    if "knife" in name or "dagger" in name:
        return "1d4"
    if "club" in name:
        return "1d6"
    if "sling" in name:
        return "1d4"
    return "1d4"


def attack_noun(item: Item | None) -> str:
    damage_type = weapon_damage_type(item)
    return {
        "pierce": "piercing",
        "shot": "ranged",
        "crush": "crushing",
        "strike": "striking",
    }[damage_type]
