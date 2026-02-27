import curses
from office.colors import (
    COLOR_WALL, COLOR_DESK, COLOR_TITLE, COLOR_STATUS_BAR,
    COLOR_FURNITURE, COLOR_SEPARATOR, COLOR_WHITEBOARD,
    COLOR_COFFEE, COLOR_PLANT, COLOR_ENTRANCE, COLOR_DESK_LABEL,
)

# Desk definitions: each desk has a position and a chair position below it
# 4 cubicles evenly spaced across the top
DESKS = [
    {"id": "desk_0", "x": 5,  "y": 3, "chair_x": 12, "chair_y": 6},
    {"id": "desk_1", "x": 21, "y": 3, "chair_x": 28, "chair_y": 6},
    {"id": "desk_2", "x": 37, "y": 3, "chair_x": 44, "chair_y": 6},
    {"id": "desk_3", "x": 53, "y": 3, "chair_x": 60, "chair_y": 6},
]

# Lounge area for idle characters
LOUNGE_AREA = {"x_min": 18, "x_max": 50, "y_min": 11, "y_max": 16}

# Walkway Y coordinate
WALKWAY_Y = 9

# Coffee spot
COFFEE_SPOT = {"x": 7, "y": 14}


class Scene:
    def __init__(self, source_name="CLAUDE CODE"):
        self.width = 78
        self.height = 22
        self.source_name = source_name
        self.whiteboard_tools = []  # (tool_name, expire_time)
        self.desk_agents = {}  # desk_id -> agent_name (for labels)

    def set_desk_agent(self, desk_id, agent_name):
        self.desk_agents[desk_id] = agent_name

    def clear_desk_agent(self, desk_id):
        self.desk_agents.pop(desk_id, None)

    def update_whiteboard(self, tool_name):
        import time
        expire = time.monotonic() + 15.0
        for i, (name, _) in enumerate(self.whiteboard_tools):
            if name == tool_name:
                self.whiteboard_tools[i] = (tool_name, expire)
                return
        self.whiteboard_tools.append((tool_name, expire))
        if len(self.whiteboard_tools) > 5:
            self.whiteboard_tools = self.whiteboard_tools[-5:]

    def tick_whiteboard(self):
        import time
        now = time.monotonic()
        self.whiteboard_tools = [(n, t) for n, t in self.whiteboard_tools
                                 if t > now]

    def draw_background(self, win, max_h, max_w):
        # Double-line outer border
        for y in range(min(self.height + 2, max_h)):
            for x in range(min(self.width + 2, max_w)):
                if y == 0 and x == 0:
                    self._safe_addch(win, y, x, "\u2554", COLOR_WALL)
                elif y == 0 and x == self.width + 1:
                    self._safe_addch(win, y, x, "\u2557", COLOR_WALL)
                elif y == self.height + 1 and x == 0:
                    self._safe_addch(win, y, x, "\u255a", COLOR_WALL)
                elif y == self.height + 1 and x == self.width + 1:
                    self._safe_addch(win, y, x, "\u255d", COLOR_WALL)
                elif y == 0 or y == self.height + 1:
                    self._safe_addch(win, y, x, "\u2550", COLOR_WALL)
                elif x == 0 or x == self.width + 1:
                    self._safe_addch(win, y, x, "\u2551", COLOR_WALL)

        # Title bar separator
        self._safe_addstr(win, 2, 0, "\u2560", COLOR_WALL)
        for x in range(1, min(self.width + 1, max_w)):
            self._safe_addstr(win, 2, x, "\u2550", COLOR_WALL)
        if self.width + 1 < max_w:
            self._safe_addstr(win, 2, self.width + 1, "\u2563", COLOR_WALL)

    def draw_title(self, win, max_w, clock_str):
        title = f" {self.source_name} OFFICE "
        # Center the title in the title bar
        pad = self.width - len(title) - len(clock_str) - 2
        self._safe_addstr(win, 1, 2, title, COLOR_TITLE, curses.A_BOLD)
        clock_x = self.width - len(clock_str)
        if clock_x > 0:
            self._safe_addstr(win, 1, clock_x, clock_str, COLOR_WALL,
                              curses.A_DIM)

    def draw_furniture(self, win, max_h, max_w):
        self._draw_cubicles(win)
        self._draw_walkway(win)
        self._draw_cafe(win)
        self._draw_plants(win)
        self._draw_sofas(win)
        self._draw_whiteboard(win)
        self._draw_lounge_label(win)
        self._draw_entrance(win)

    def _draw_cubicles(self, win):
        cubicle_xs = [5, 21, 37, 53]
        cw = 15  # cubicle width

        # Top wall
        for i, cx in enumerate(cubicle_xs):
            if i == 0:
                self._safe_addstr(win, 3, cx, "┌" + "─" * (cw - 2), COLOR_DESK)
            else:
                self._safe_addstr(win, 3, cx, "┬" + "─" * (cw - 2), COLOR_DESK)
        self._safe_addstr(win, 3, cubicle_xs[-1] + cw - 1, "┐", COLOR_DESK)

        # Monitors row (y=4)
        for cx in cubicle_xs:
            self._safe_addstr(win, 4, cx, "│", COLOR_DESK)
            self._safe_addstr(win, 4, cx + 4, "░▓▓▓▓▓░", COLOR_DESK)
            self._safe_addstr(win, 4, cx + cw - 1, "│", COLOR_DESK)

        # Desk surface row (y=5)
        for cx in cubicle_xs:
            self._safe_addstr(win, 5, cx, "│", COLOR_DESK)
            self._safe_addstr(win, 5, cx + 3, "═════════", COLOR_DESK)
            self._safe_addstr(win, 5, cx + cw - 1, "│", COLOR_DESK)

        # Chair row (y=6) with agent labels
        for i, cx in enumerate(cubicle_xs):
            self._safe_addstr(win, 6, cx, "│", COLOR_DESK)
            self._safe_addstr(win, 6, cx + cw - 1, "│", COLOR_DESK)
            # Chair
            self._safe_addstr(win, 6, DESKS[i]["chair_x"], "◇", COLOR_DESK)

        # Bottom wall (y=7)
        for i, cx in enumerate(cubicle_xs):
            if i == 0:
                self._safe_addstr(win, 7, cx, "└" + "─" * (cw - 2), COLOR_DESK)
            else:
                self._safe_addstr(win, 7, cx, "┴" + "─" * (cw - 2), COLOR_DESK)
        self._safe_addstr(win, 7, cubicle_xs[-1] + cw - 1, "┘", COLOR_DESK)

        # Desk number labels (y=8)
        for i, cx in enumerate(cubicle_xs):
            label = self.desk_agents.get(DESKS[i]["id"], f"desk-{i}")
            label = label[:10].center(cw - 2)
            self._safe_addstr(win, 8, cx + 1, label, COLOR_DESK_LABEL,
                              curses.A_DIM)

    def _draw_walkway(self, win):
        # Decorative dotted walkway
        pattern = "· · · · · · · · · · · · · · · · · · · "
        self._safe_addstr(win, WALKWAY_Y, 2, pattern[:self.width - 4],
                          COLOR_SEPARATOR, curses.A_DIM)

    def _draw_cafe(self, win):
        self._safe_addstr(win, 11, 2, "┌───────────┐", COLOR_COFFEE)
        self._safe_addstr(win, 12, 2, "│  ♨  CAFÉ  │", COLOR_COFFEE)
        self._safe_addstr(win, 13, 2, "│ ╭───────╮ │", COLOR_COFFEE)
        self._safe_addstr(win, 14, 2, "│ │ ♨ tea │ │", COLOR_COFFEE)
        self._safe_addstr(win, 15, 2, "│ ╰───────╯ │", COLOR_COFFEE)
        self._safe_addstr(win, 16, 2, "│  ·  ·  ·  │", COLOR_COFFEE)
        self._safe_addstr(win, 17, 2, "└───────────┘", COLOR_COFFEE)

    def _draw_plants(self, win):
        # Plants near the café and between areas
        self._safe_addstr(win, 10, 3, "}{", COLOR_PLANT)
        self._safe_addstr(win, 10, 13, "}{", COLOR_PLANT)
        self._safe_addstr(win, 19, 15, "}{", COLOR_PLANT)
        self._safe_addstr(win, 19, 42, "}{", COLOR_PLANT)

    def _draw_sofas(self, win):
        # Sofa 1
        self._safe_addstr(win, 16, 19, "╭━━━━━━╮", COLOR_FURNITURE)
        self._safe_addstr(win, 17, 19, "┃ ░░░░ ┃", COLOR_FURNITURE)
        self._safe_addstr(win, 18, 19, "╰━━━━━━╯", COLOR_FURNITURE)

        # Coffee table
        self._safe_addstr(win, 17, 28, "◻", COLOR_FURNITURE)

        # Sofa 2
        self._safe_addstr(win, 16, 33, "╭━━━━━━╮", COLOR_FURNITURE)
        self._safe_addstr(win, 17, 33, "┃ ░░░░ ┃", COLOR_FURNITURE)
        self._safe_addstr(win, 18, 33, "╰━━━━━━╯", COLOR_FURNITURE)

    def _draw_whiteboard(self, win):
        wb_x = self.width - 18
        self._safe_addstr(win, 10, wb_x, "╔══════════════════╗", COLOR_WHITEBOARD)
        self._safe_addstr(win, 11, wb_x, "║   WHITEBOARD     ║", COLOR_WHITEBOARD,
                          curses.A_BOLD)
        self._safe_addstr(win, 12, wb_x, "║──────────────────║", COLOR_WHITEBOARD)
        # Tool entries (up to 5)
        for i in range(5):
            if i < len(self.whiteboard_tools):
                name = self.whiteboard_tools[i][0]
                tool_str = f"║  ▸ {name:<13} ║"
            else:
                tool_str = "║                  ║"
            self._safe_addstr(win, 13 + i, wb_x, tool_str, COLOR_WHITEBOARD)
        self._safe_addstr(win, 18, wb_x, "╚══════════════════╝", COLOR_WHITEBOARD)

    def _draw_lounge_label(self, win):
        self._safe_addstr(win, 13, 28, "L O U N G E", COLOR_FURNITURE,
                          curses.A_DIM)

    def _draw_entrance(self, win):
        # Entrance/door at bottom center
        door_x = 35
        self._safe_addstr(win, 20, door_x, "╔════════╗", COLOR_ENTRANCE)
        self._safe_addstr(win, 21, door_x, "║ DOOR ▸ ║", COLOR_ENTRANCE)

    def draw_status_bar(self, win, max_h, max_w, agent_count, sub_count,
                        active_count, tools_str):
        bar_y = self.height
        # Build status sections
        agents_sec = f" Agents: {agent_count}+{sub_count}sub"
        active_sec = f"  Active: {active_count}"
        tools_sec = f"  Tools: {tools_str}"
        bar = f"{agents_sec} │{active_sec} │{tools_sec}"
        bar = bar[:self.width]
        self._safe_addstr(win, bar_y, 1, bar.ljust(self.width),
                          COLOR_STATUS_BAR, curses.A_BOLD)

    def _safe_addstr(self, win, y, x, s, color_pair, attrs=0):
        max_h, max_w = win.getmaxyx()
        if y < 0 or y >= max_h or x >= max_w:
            return
        # Truncate string to fit within window width
        available = max_w - x
        if available <= 0:
            return
        s = s[:available]
        try:
            win.addstr(y, x, s, curses.color_pair(color_pair) | attrs)
        except curses.error:
            pass

    def _safe_addch(self, win, y, x, ch, color_pair, attrs=0):
        max_h, max_w = win.getmaxyx()
        if y < 0 or y >= max_h or x >= max_w:
            return
        try:
            win.addstr(y, x, ch, curses.color_pair(color_pair) | attrs)
        except curses.error:
            pass
