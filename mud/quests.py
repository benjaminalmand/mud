from __future__ import annotations


QUESTS: dict[str, dict[str, object]] = {
    "applehill_stolen_token": {
        "id": "applehill_stolen_token",
        "name": "The Stolen Prayer Token",
        "giver_npc_id": "brother_nim",
        "required_item_id": "stolen_prayer_token",
        "reward_xp": 120,
        "reward_item_id": "sunlit_candlestick",
        "summary": "Brother Nim wants the stolen prayer token recovered from the goblins in the orchard.",
        "accept_text": [
            "Brother Nim lowers his voice. \"One of Garl's prayer tokens was stolen from the temple.\"",
            "\"If you can recover it from the goblins troubling the orchard and bring it back, Applehill will owe you thanks.\"",
            "You accept the task of recovering the stolen prayer token."
        ],
        "progress_text": [
            "Brother Nim says, \"The goblins took a brass token stamped with Garl's laughing face.\"",
            "\"Bring it back to me, and perhaps we can turn ill luck aside before it deepens.\""
        ],
        "complete_text": [
            "Brother Nim receives the stolen token with a relieved breath and bows his head in thanks.",
            "\"You have done Applehill a kindness, and Garl sees the wit in timely courage.\"",
            "He presses a small temple treasure into your hand as reward."
        ],
    }
}
