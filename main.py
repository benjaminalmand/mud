from __future__ import annotations

from mud.game import Game
from mud.startup import TerminalStartupIO, login_and_choose_character


def main() -> None:
    player = login_and_choose_character(TerminalStartupIO())
    if player is None:
        raise SystemExit(0)
    game = Game(player=player)
    game.run()


if __name__ == "__main__":
    main()
