from __future__ import annotations

import socket
import socketserver

from mud.game import Game
from mud.session import GameSession, SessionResult
from mud.startup import StartupIO, StartupPromptResult, login_and_choose_character


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
        game.run_session(session)


class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True
    daemon_threads = True


def serve(host: str = "0.0.0.0", port: int = 4000) -> None:
    with ThreadedTCPServer((host, port), MudRequestHandler) as server:
        print(f"Applehill server listening on {host}:{port}")
        server.serve_forever()
