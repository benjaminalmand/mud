from __future__ import annotations

import sys
import time
from dataclasses import dataclass

from mud.render import render_screen


@dataclass(slots=True)
class SessionResult:
    command: str | None
    should_continue: bool = True


class GameSession:
    def render(self, game) -> str:
        return render_screen(
            game.world,
            game.player,
            game.visible_room_events(),
            game.combat_footer_text(),
            game.other_room_characters(),
        )

    def display(self, screen: str) -> None:
        raise NotImplementedError

    def read_command(self, game) -> SessionResult:
        raise NotImplementedError


class LocalTerminalSession(GameSession):
    def display(self, screen: str) -> None:
        print(screen)

    def read_command(self, game) -> SessionResult:
        if game.combat is not None and game.combat.player_turn:
            return SessionResult(command=self._combat_prompt(game))
        return SessionResult(command=input("\n> ").strip())

    def _combat_prompt(self, game) -> str:
        monster = game.current_combatant()
        if monster is None:
            return ""
        if game.combat.turn_actions_remaining <= 0:
            time.sleep(0.2)
            return ""

        if not sys.stdin.isatty():
            time.sleep(0.4)
            return game.default_combat_action(monster)

        try:
            import msvcrt  # type: ignore
        except ImportError:
            time.sleep(0.6)
            return game.default_combat_action(monster)

        print("\n(combat) ", end="", flush=True)
        typed: list[str] = []
        deadline = time.time() + 0.9
        while time.time() < deadline:
            if msvcrt.kbhit():
                char = msvcrt.getwche()
                if char in {"\r", "\n"}:
                    print()
                    return "".join(typed).strip() or game.default_combat_action(monster)
                if char == "\b":
                    if typed:
                        typed.pop()
                    continue
                typed.append(char)
            time.sleep(0.03)
        print()
        return "".join(typed).strip() or game.default_combat_action(monster)
