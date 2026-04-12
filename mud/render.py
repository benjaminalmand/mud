from __future__ import annotations

import re
from shutil import get_terminal_size
from textwrap import wrap

from mud.models import Item, Player, Room, World


DIRECTION_GLYPHS = {
    "north": "^",
    "east": ">",
    "south": "v",
    "west": "<",
}

ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")
COLOR_GREEN = "\x1b[38;5;28m"
COLOR_RED = "\x1b[38;5;88m"
COLOR_PURPLE = "\x1b[38;5;54m"
COLOR_YELLOW = "\x1b[38;5;220m"
COLOR_CYAN = "\x1b[38;5;117m"
COLOR_GOLD = "\x1b[38;5;179m"
COLOR_ORANGE = "\x1b[38;5;214m"
COLOR_MAGENTA = "\x1b[38;5;176m"
COLOR_BLUE = "\x1b[38;5;39m"
COLOR_DIM = "\x1b[38;5;244m"
BG_BLUE = "\x1b[48;5;18m"
COLOR_RESET = "\x1b[0m"


def clear_screen() -> str:
    return "\x1b[2J\x1b[H"


def render_screen(world: World, player: Player, message_log: list[str], combat_status: str = "") -> str:
    width, height = get_terminal_size((120, 36))
    room = world.rooms[player.room_id]
    header_height = 9
    body_width = max(60, width)
    footer_height = 1

    header_lines = render_header(world, player, room, width, header_height)
    body_height = max(10, height - header_height - footer_height - 1)
    body_lines = render_body_panel(
        world,
        player,
        room,
        message_log,
        body_width,
        body_height,
    )
    footer_lines = render_footer(world, player, room, width, combat_status)

    content_lines = body_lines + [""] * max(0, body_height - len(body_lines))
    return clear_screen() + "\n".join(header_lines + content_lines + footer_lines)


def render_header(world: World, player: Player, room: Room, width: int, height: int) -> list[str]:
    grouped = grouped_people(world, player, room.id)
    others = others_in_room(world, player, room.id)
    ground = [item.name for item in world.items_in_room(room.id)]

    box_gap = 1
    inner_total = width - (box_gap * 4)
    base_width = inner_total // 5
    widths = [base_width, base_width, base_width, base_width, inner_total - (base_width * 4)]

    boxes = [
        render_box("Health", health_box_lines(player), widths[0], height),
        render_box("Group", grouped or ["none"], widths[1], height),
        render_box("Others", others or ["none"], widths[2], height),
        render_box("Ground", ground or ["nothing"], widths[3], height),
        render_box("Map", map_box_lines(world, player, room), widths[4], height),
    ]

    combined: list[str] = []
    for row_index in range(height):
        parts = [pad_ansi(box[row_index], widths[idx]) for idx, box in enumerate(boxes)]
        combined.append((" " * box_gap).join(parts))
    return combined


def render_body_panel(
    world: World,
    player: Player,
    room: Room,
    room_events: list[str],
    width: int,
    height: int,
) -> list[str]:
    lines: list[str] = []
    if is_overlay_view(room_events):
        for entry in room_events:
            append_wrapped(lines, entry, width)
        return lines[:height]

    header = f"{COLOR_CYAN}{room.name}{COLOR_RESET}"
    append_wrapped(lines, header, width)
    exits_line = format_room_exits(world, room)
    append_wrapped(lines, exits_line, width)
    lines.append(f"{COLOR_DIM}" + ("=" * min(width, max(10, visible_len(header)))) + f"{COLOR_RESET}")
    append_justified(lines, room.long_description, width, COLOR_GOLD)

    for person_line in room_people_lines(world, player, room.id):
        append_wrapped(lines, person_line, width)
    for item_line in room_item_lines(world, room.id):
        append_wrapped(lines, item_line, width)

    lines.append("")
    for entry in room_events:
        append_wrapped(lines, entry, width)
    return lines[:height]


def render_box(title: str, content_lines: list[str], width: int, height: int) -> list[str]:
    inner_width = max(4, width - 2)
    content_height = max(1, height - 4)
    lines = [f"{COLOR_BLUE}+" + "-" * inner_width + f"+{COLOR_RESET}"]
    lines.append(f"{COLOR_BLUE}|{COLOR_RESET}" + color_center(title, inner_width, COLOR_YELLOW) + f"{COLOR_BLUE}|{COLOR_RESET}")
    lines.append(f"{COLOR_BLUE}|{'-' * inner_width}|{COLOR_RESET}")

    expanded: list[str] = []
    for content in content_lines:
        if visible_len(content) <= inner_width:
            expanded.append(content)
        else:
            expanded.extend(wrap(content, width=max(1, inner_width)) or [""])

    for index in range(content_height):
        content = expanded[index] if index < len(expanded) else ""
        lines.append(f"{COLOR_BLUE}|{COLOR_RESET}" + pad_ansi(content, inner_width) + f"{COLOR_BLUE}|{COLOR_RESET}")
    lines.append(f"{COLOR_BLUE}+" + "-" * inner_width + f"+{COLOR_RESET}")
    return lines


def health_box_lines(player: Player) -> list[str]:
    parts = colored_stick_figure(player)
    return [
        f"{COLOR_YELLOW}HP{COLOR_RESET} {player.hp}/{player.max_hp}",
        parts[0],
        parts[1],
        parts[2],
        f"{COLOR_YELLOW}Face{COLOR_RESET} {player.facing}",
    ]


def map_box_lines(world: World, player: Player, room: Room) -> list[str]:
    radius = 2
    canvas_size = (radius * 4) + 1
    center = canvas_size // 2
    canvas = [[" " for _ in range(canvas_size)] for _ in range(canvas_size)]

    visible_rooms = [
        candidate
        for candidate in world.rooms.values()
        if abs(candidate.map_x - room.map_x) <= radius and abs(candidate.map_y - room.map_y) <= radius
    ]
    points: dict[str, tuple[int, int]] = {}
    for candidate in visible_rooms:
        draw_x = center + ((candidate.map_x - room.map_x) * 2)
        draw_y = center + ((candidate.map_y - room.map_y) * 2)
        if 0 <= draw_x < canvas_size and 0 <= draw_y < canvas_size:
            points[candidate.id] = (draw_x, draw_y)

    for candidate in visible_rooms:
        start = points.get(candidate.id)
        if start is None:
            continue
        start_x, start_y = start
        for direction, target_id in candidate.exits.items():
            end = points.get(target_id)
            if end is None:
                continue
            end_x, end_y = end
            if direction in {"east", "west"}:
                step = 1 if end_x > start_x else -1
                for x in range(start_x + step, end_x, step):
                    canvas[start_y][x] = "-"
            elif direction in {"north", "south"}:
                step = 1 if end_y > start_y else -1
                for y in range(start_y + step, end_y, step):
                    canvas[y][start_x] = "|"
            elif direction == "up":
                canvas[max(0, start_y - 1)][start_x] = "^"
            elif direction == "down":
                canvas[min(canvas_size - 1, start_y + 1)][start_x] = "v"

    for candidate in visible_rooms:
        point = points.get(candidate.id)
        if point is None:
            continue
        draw_x, draw_y = point
        if candidate.id == player.room_id:
            canvas[draw_y][draw_x] = DIRECTION_GLYPHS.get(player.facing, "@")
        else:
            canvas[draw_y][draw_x] = "o"

    lines = []
    for row in canvas:
        rendered = []
        for char in row:
            if char in {"-", "|", "^", "v"}:
                rendered.append(f"{COLOR_BLUE}{char}{COLOR_RESET}")
            elif char == "o":
                rendered.append(f"{COLOR_DIM}{char}{COLOR_RESET}")
            elif char in DIRECTION_GLYPHS.values() or char == "@":
                rendered.append(f"{COLOR_YELLOW}{char}{COLOR_RESET}")
            else:
                rendered.append(char)
        lines.append("".join(rendered).rstrip())
    lines.append(f"{COLOR_YELLOW}Face{COLOR_RESET} {player.facing}")
    lines.append(f"{COLOR_CYAN}Area{COLOR_RESET} {world.zone.name}")
    return lines


def colored_stick_figure(player: Player) -> list[str]:
    ratio = player.hp / player.max_hp if player.max_hp else 0
    if ratio > 0.66:
        color = COLOR_GREEN
    elif ratio > 0.33:
        color = COLOR_RED
    else:
        color = COLOR_PURPLE

    return [
        f"  {color}O{COLOR_RESET}  ",
        f" {color}/{COLOR_RESET}{color}|{COLOR_RESET}{color}\\{COLOR_RESET} ",
        f" {color}/{COLOR_RESET} {color}\\{COLOR_RESET} ",
    ]


def grouped_people(world: World, player: Player, room_id: str) -> list[str]:
    names: list[str] = []
    for npc in world.npcs_in_room(room_id):
        if npc.id in player.group_members:
            names.append(npc.name)
    return names


def others_in_room(world: World, player: Player, room_id: str) -> list[str]:
    names: list[str] = []
    for npc in world.npcs_in_room(room_id):
        if npc.id not in player.group_members:
            names.append(npc.name)
    for monster in world.monsters_in_room(room_id):
        names.append(monster.name)
    return names


def room_people_lines(world: World, player: Player, room_id: str) -> list[str]:
    lines: list[str] = []
    for npc in world.npcs_in_room(room_id):
        posture = npc.posture
        if npc.id in player.group_members:
            lines.append(f"     {COLOR_GREEN}{npc.name}{COLOR_RESET} is {posture} here, with your group.")
        else:
            lines.append(f"     {COLOR_MAGENTA}{npc.name}{COLOR_RESET} is {posture} here.")
    for monster in world.monsters_in_room(room_id):
        lines.append(f"     {COLOR_RED}{monster.name}{COLOR_RESET} is here.")
    return lines


def room_item_lines(world: World, room_id: str) -> list[str]:
    return [
        f"     {COLOR_GREEN}{item_display_name(item)}{COLOR_RESET} is here. {COLOR_DIM}({item.condition}){COLOR_RESET}"
        for item in world.items_in_room(room_id)
    ]


def append_wrapped(lines: list[str], text: str, width: int) -> None:
    lines.extend(wrap(text, width=width) or [""])


def append_justified(lines: list[str], text: str, width: int, color: str = "") -> None:
    wrapped = wrap(text, width=max(20, width)) or [""]
    for index, raw_line in enumerate(wrapped):
        line = justify_line(raw_line, width) if index < len(wrapped) - 1 else raw_line
        if color:
            lines.append(f"{color}{line}{COLOR_RESET}")
        else:
            lines.append(line)


def pad_ansi(text: str, width: int) -> str:
    visible = visible_len(text)
    if visible >= width:
        return text
    return text + (" " * (width - visible))


def visible_len(text: str) -> int:
    return len(ANSI_RE.sub("", text))


def render_footer(world: World, player: Player, room: Room, width: int, combat_status: str = "") -> list[str]:
    hp_pct = int((player.hp / player.max_hp) * 100) if player.max_hp else 0
    stamina_pct = int((player.stamina / player.max_stamina) * 100) if player.max_stamina else 0
    exits = ", ".join(room.exits.keys()) or "none"
    combat_segment = f" Combat {combat_status} " if combat_status else ""
    content = f" Health {hp_pct}%  Stamina {stamina_pct}%  Exits {exits}{combat_segment}"
    visible = visible_len(content)
    if visible < width:
        content = content + (" " * (width - visible))
    else:
        content = content[:width]
    return [f"{BG_BLUE}{COLOR_YELLOW}{content}{COLOR_RESET}"]


def color_center(text: str, width: int, color: str) -> str:
    visible = visible_len(text)
    if visible >= width:
        return f"{color}{text}{COLOR_RESET}"
    left = (width - visible) // 2
    right = width - visible - left
    return (" " * left) + f"{color}{text}{COLOR_RESET}" + (" " * right)


def justify_line(text: str, width: int) -> str:
    words = text.split()
    if len(words) <= 1:
        return text
    chars = sum(len(word) for word in words)
    spaces_needed = max(0, width - chars)
    gaps = len(words) - 1
    base_space = spaces_needed // gaps
    extra = spaces_needed % gaps
    parts: list[str] = []
    for index, word in enumerate(words[:-1]):
        gap_width = max(1, base_space + (1 if index < extra else 0))
        parts.append(word + (" " * gap_width))
    parts.append(words[-1])
    return "".join(parts)


def format_room_exits(world: World, room: Room) -> str:
    ordered = [("north", "N"), ("east", "E"), ("south", "S"), ("west", "W"), ("up", "U"), ("down", "D")]
    parts = []
    for direction, abbrev in ordered:
        target_id = room.exits.get(direction)
        if not target_id:
            continue
        target_name = world.rooms[target_id].name if target_id in world.rooms else target_id.replace("_", " ").title()
        parts.append(f"{COLOR_YELLOW}{abbrev}{COLOR_RESET}-{target_name}")
    return " ".join(parts) if parts else f"{COLOR_DIM}No obvious exits.{COLOR_RESET}"


def item_display_name(item: Item) -> str:
    parts = [f"({flag})" for flag in inferred_item_flags(item)]
    parts.append(item.name)
    return " ".join(parts)


def inferred_item_flags(item: Item) -> list[str]:
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


def is_overlay_view(room_events: list[str]) -> bool:
    if not room_events:
        return False
    first = room_events[0]
    return first == "You are using:" or first.startswith("-")
