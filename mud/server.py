from __future__ import annotations

import socket
import socketserver

from mud.game import Game
from mud.persistence import save_player
from mud.render import render_transcript
from mud.runtime import RUNTIME_REGISTRY
from mud.session import GameSession, SessionResult
from mud.startup import StartupIO, StartupPromptResult, login_and_choose_character


class NetworkSession(GameSession):
    def __init__(self, reader, writer) -> None:
        self.reader = reader
        self.writer = writer
        self.last_room_id: str | None = None
        self.last_event_count: dict[str, int] = {}
        self.first_render = True

    def display(self, screen: str) -> None:
        payload = screen.replace("\n", "\r\n")
        self.writer.write(payload.encode("utf-8", errors="replace"))
        self.writer.write(b"\r\n")
        self.writer.flush()

    def render(self, game) -> str:
        room_id = game.player.room_id
        events = game.visible_room_events()
        include_room = self.first_render or self.last_room_id != room_id or is_overlay(events)
        if include_room:
            lines = render_transcript(
                game.world,
                game.player,
                events,
                game.combat_footer_text(),
                game.other_room_characters(),
                include_room=True,
            )
            self.last_event_count[room_id] = len(events)
            self.last_room_id = room_id
            self.first_render = False
            return "\n".join(lines)

        start = self.last_event_count.get(room_id, 0)
        new_events = events[start:]
        self.last_event_count[room_id] = len(events)
        if not new_events:
            return ""
        lines = render_transcript(
            game.world,
            game.player,
            new_events,
            game.combat_footer_text(),
            game.other_room_characters(),
            include_room=False,
        )
        return "\n".join(lines)

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


class NetworkStartupIO(StartupIO):
    def __init__(self, session: NetworkSession) -> None:
        self.session = session

    def write_line(self, text: str = "") -> None:
        self.session.write_line(text)

    def prompt(self, text: str, *, secret: bool = False) -> StartupPromptResult:
        value = self.session.prompt(f"{text}: ")
        if value is None:
            return StartupPromptResult(None, should_continue=False)
        return StartupPromptResult(value)


class MudRequestHandler(socketserver.StreamRequestHandler):
    def handle(self) -> None:
        try:
            self.request.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        except OSError:
            pass
        session = NetworkSession(self.rfile, self.wfile)
        player = login_and_choose_character(NetworkStartupIO(session))
        if player is None:
            return
        game = Game(player=player)
        game.room_character_provider = RUNTIME_REGISTRY.room_characters
        game.room_event_sink = RUNTIME_REGISTRY.broadcast_room
        game.target_event_sink = RUNTIME_REGISTRY.send_target
        game.player_transfer_sink = RUNTIME_REGISTRY.transfer_item
        game.player_lookup_provider = RUNTIME_REGISTRY.lookup_player
        game.session_end_hook = self.on_session_end
        RUNTIME_REGISTRY.register(game)
        RUNTIME_REGISTRY.broadcast_room(game.player.room_id, game.player.id, f"{game.player.name} has entered the room.", "arrival")
        game.run_session(session)

    def on_session_end(self, game: Game) -> None:
        save_player(game.player)
        RUNTIME_REGISTRY.broadcast_room(game.player.room_id, game.player.id, f"{game.player.name} has left the room.", "departure")
        RUNTIME_REGISTRY.unregister(game.player.id)


class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True
    daemon_threads = True


def serve(host: str = "0.0.0.0", port: int = 4000) -> None:
    with ThreadedTCPServer((host, port), MudRequestHandler) as server:
        print(f"Applehill server listening on {host}:{port}")
        server.serve_forever()


def is_overlay(events: list[str]) -> bool:
    if not events:
        return False
    first = events[0]
    return first == "You are using:" or first.startswith("-") or first.startswith("Quest Journal")
