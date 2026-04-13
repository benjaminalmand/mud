from __future__ import annotations

from dataclasses import dataclass
from threading import Lock

from mud.models import Character, Player


@dataclass(slots=True)
class PresenceView(Character):
    account_id: str = ""


@dataclass(slots=True)
class ActiveConnection:
    player_id: str
    account_id: str
    game: object


class SessionRegistry:
    def __init__(self) -> None:
        self._lock = Lock()
        self._connections: dict[str, ActiveConnection] = {}

    def register(self, game) -> None:
        with self._lock:
            self._connections[game.player.id] = ActiveConnection(
                player_id=game.player.id,
                account_id=game.player.account_id,
                game=game,
            )

    def unregister(self, player_id: str) -> None:
        with self._lock:
            self._connections.pop(player_id, None)

    def room_characters(self, room_id: str, exclude_player_id: str) -> list[PresenceView]:
        with self._lock:
            result = []
            for connection in self._connections.values():
                game = connection.game
                player = game.player
                if player.id == exclude_player_id or player.room_id != room_id:
                    continue
                result.append(
                    PresenceView(
                        id=player.id,
                        account_id=player.account_id,
                        name=player.name,
                        keywords=player_keywords(player),
                        description=player_description(player),
                        room_id=player.room_id,
                        posture=player.posture,
                    )
                )
            return result

    def broadcast_room(self, room_id: str, exclude_player_id: str, text: str, kind: str = "room") -> None:
        with self._lock:
            recipients = [
                connection.game
                for connection in self._connections.values()
                if connection.player_id != exclude_player_id and connection.game.player.room_id == room_id
            ]
        for game in recipients:
            game.receive_external_event(text, kind=kind)

    def send_target(self, recipient_id: str, text: str, kind: str = "social") -> None:
        with self._lock:
            recipient = self._connections.get(recipient_id)
            game = recipient.game if recipient is not None else None
        if game is not None:
            game.receive_external_event(text, kind=kind)

    def transfer_item(self, giver_id: str, recipient_id: str, item_id: str) -> bool:
        with self._lock:
            giver = self._connections.get(giver_id)
            recipient = self._connections.get(recipient_id)
            if giver is None or recipient is None:
                return False
            giver_game = giver.game
            recipient_game = recipient.game
            if giver_game.player.room_id != recipient_game.player.room_id:
                return False
            if item_id in recipient_game.player.inventory:
                return False
            recipient_game.player.inventory.append(item_id)
            return True


def player_keywords(player: Player) -> list[str]:
    return list({part.lower() for part in player.name.replace("-", " ").replace("'", " ").split() if part})


def player_description(player: Player) -> str:
    return f"{player.name} looks ready for the road, a {player.race.replace('_', ' ')} {player.class_id} with an eye on the next turn of fortune."


RUNTIME_REGISTRY = SessionRegistry()
