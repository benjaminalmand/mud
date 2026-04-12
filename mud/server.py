from __future__ import annotations

import socket
import socketserver
from pathlib import Path

from mud.creation import build_default_player
from mud.game import Game
from mud.persistence import list_saves, load_player, save_path_for, save_player, slugify_name
from mud.rules import CLASSES, RACES
from mud.session import GameSession, SessionResult


class NetworkSession(GameSession):
    def __init__(self, reader, writer) -> None:
        self.reader = reader
        self.writer = writer

    def display(self, screen: str) -> None:
        payload = screen.replace("\n", "\r\n")
        self.writer.write(payload.encode("utf-8", errors="replace"))
        self.writer.write(b"\r\n")
        self.writer.flush()

    def read_command(self, game) -> SessionResult:
        self.writer.write(b"\r\n> ")
        self.writer.flush()
        data = self.reader.readline()
        if not data:
            return SessionResult(command=None, should_continue=False)
        return SessionResult(command=data.decode("utf-8", errors="replace").strip())

    def write_line(self, text: str = "") -> None:
        self.writer.write(text.encode("utf-8", errors="replace"))
        self.writer.write(b"\r\n")
        self.writer.flush()

    def prompt(self, text: str) -> str | None:
        self.writer.write(text.encode("utf-8", errors="replace"))
        self.writer.flush()
        data = self.reader.readline()
        if not data:
            return None
        return data.decode("utf-8", errors="replace").strip()


def select_or_create_player(session: NetworkSession):
    session.write_line("Applehill MUD")
    saves = list_saves()
    if saves:
        session.write_line("Saved characters:")
        for save in saves:
            session.write_line(f" - {save.stem}")
    choice = session.prompt("Enter a character name to load, or type new: ")
    if not choice:
        return None
    lowered = choice.strip().lower()
    if lowered != "new":
        path = save_path_for(slugify_name(choice))
        if path.exists():
            return load_player(path)
        session.write_line(f"No save named '{choice}' was found. Creating a new character instead.")
        name = choice.strip()
    else:
        name = session.prompt("Name: ")
        if not name:
            return None

    gender = session.prompt("Gender [unknown]: ") or "unknown"
    race = prompt_choice(session, "Race", list(RACES.keys()), default="human")
    class_id = prompt_choice(session, "Class", list(CLASSES.keys()), default="fighter")
    player = build_default_player(name=name, race_id=race, class_id=class_id, gender=gender)
    save_player(player)
    session.write_line(f"{player.name} the {CLASSES[class_id].name} is ready.")
    return player


def prompt_choice(session: NetworkSession, label: str, options: list[str], default: str) -> str:
    session.write_line(f"{label} options: {', '.join(options)}")
    while True:
        response = session.prompt(f"{label} [{default}]: ")
        if response is None:
            return default
        if not response:
            return default
        lowered = response.lower().replace("-", "_")
        for option in options:
            if lowered == option:
                return option
        session.write_line(f"Please choose one of: {', '.join(options)}")


class MudRequestHandler(socketserver.StreamRequestHandler):
    def handle(self) -> None:
        try:
            self.request.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        except OSError:
            pass
        session = NetworkSession(self.rfile, self.wfile)
        player = select_or_create_player(session)
        if player is None:
            return
        game = Game(player=player)
        game.run_session(session)


class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True
    daemon_threads = True


def serve(host: str = "0.0.0.0", port: int = 4000) -> None:
    with ThreadedTCPServer((host, port), MudRequestHandler) as server:
        print(f"Applehill server listening on {host}:{port}")
        server.serve_forever()
