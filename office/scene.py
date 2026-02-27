import curses
from office.colors import (
    COLOR_WALL, COLOR_DESK, COLOR_TITLE, COLOR_STATUS_BAR,
    COLOR_FURNITURE, COLOR_SEPARATOR, COLOR_WHITEBOARD,
    COLOR_COFFEE, COLOR_PLANT,
)

# Desk definitions: each desk has a position and a chair position below it
# Cubicles at x=5, x=21, x=37, x=53 (15 wide each)
# Chair centered in each cubicle
DESKS = [
    {"id": "desk_0", "x": 5,  "y": 3, "chair_x": 12, "chair_y": 6},
    {"id": "desk_1", "x": 21, "y": 3, "chair_x": 28, "chair_y": 6},
    {"id": "desk_2", "x": 37, "y": 3, "chair_x": 44, "chair_y": 6},
    {"id": "desk_3", "x": 53, "y": 3, "chair_x": 60, "chair_y": 6},
]

# Lounge spawn area for idle characters (avoids furniture)
LOUNGE_AREA = {"x_min": 16, "x_max": 52, "y_min": 11, "y_max": 16}

# Walkway Y coordinate (characters cross this to go between desk and lounge)
WALKWAY_Y = 9

# Coffee spot -- where characters go to think
COFFEE_SPOT = {"x": 7, "y": 14}


class Scene:
    def __init__(self, source_name="CLAUDE CODE"):
        self.width = 78
        self.height = 22
        self.source_name = source_name
        self.whiteboard_tools = []  # (tool_name, expire_time)

    def update_whiteboard(self, tool_name):
        import time
        expire = time.monotonic() + 15.0  # show for 15 seconds
        # Update existing entry or add new
        for i, (name, _) in enumerate(self.whiteboard_tools):
            if name == tool_name:
                self.whiteboard_tools[i] = (tool_name, expire)
                return
        self.whiteboard_tools.append((tool_name, expire))
        if len(self.whiteboard_tools) > 4:
            self.whiteboard_tools = self.whiteboard_tools[-4:]

    def tick_whiteboard(self):
        import time
        now = time.monotonic()
        self.whiteboard_tools = [(n, t) for n, t in self.whiteboard_tools
                                 if t > now]

    def draw_background(self, win, max_h, max_w):
        # Outer border
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
        title = f"{self.source_name} OFFICE"
        self._safe_addstr(win, 1, 3, title, COLOR_TITLE,
                          curses.A_BOLD)
        clock_x = self.width - len(clock_str) - 1
        if clock_x > 0:
            self._safe_addstr(win, 1, clock_x, clock_str, COLOR_WALL)

    def draw_furniture(self, win, max_h, max_w):
        # === CUBICLES (y=3 to y=7) ===
        cubicle_xs = [5, 21, 37, 53]
        cw = 15  # cubicle width

        # Top wall: ┌─────┬─────┬─────┬─────┐
        top_row = "┌" + "─" * (cw - 2) + "┐"
        for i, cx in enumerate(cubicle_xs):
            if i == 0:
                self._safe_addstr(win, 3, cx, "┌" + "─" * (cw - 2), COLOR_DESK)
            else:
                self._safe_addstr(win, 3, cx, "┬" + "─" * (cw - 2), COLOR_DESK)
        self._safe_addstr(win, 3, cubicle_xs[-1] + cw - 1, "┐", COLOR_DESK)

        # Monitors row (y=4): │ ▓▓▓ │
        for cx in cubicle_xs:
            self._safe_addstr(win, 4, cx, "│", COLOR_DESK)
            self._safe_addstr(win, 4, cx + 5, "▓▓▓▓▓", COLOR_DESK)
            self._safe_addstr(win, 4, cx + cw - 1, "│", COLOR_DESK)

        # Desk surface row (y=5): │ ═══ │
        for cx in cubicle_xs:
            self._safe_addstr(win, 5, cx, "│", COLOR_DESK)
            self._safe_addstr(win, 5, cx + 4, "═══════", COLOR_DESK)
            self._safe_addstr(win, 5, cx + cw - 1, "│", COLOR_DESK)

        # Chair row (y=6): │  ◇  │
        for i, cx in enumerate(cubicle_xs):
            self._safe_addstr(win, 6, cx, "│", COLOR_DESK)
            self._safe_addstr(win, 6, cx + cw - 1, "│", COLOR_DESK)
            # Chair centered
            self._safe_addstr(win, 6, DESKS[i]["chair_x"], "◇", COLOR_DESK)

        # Bottom wall (y=7): └─────┴─────┴─────┴─────┘
        for i, cx in enumerate(cubicle_xs):
            if i == 0:
                self._safe_addstr(win, 7, cx, "└" + "─" * (cw - 2), COLOR_DESK)
            else:
                self._safe_addstr(win, 7, cx, "┴" + "─" * (cw - 2), COLOR_DESK)
        self._safe_addstr(win, 7, cubicle_xs[-1] + cw - 1, "┘", COLOR_DESK)

        # === WALKWAY (y=9) ===
        dots = "·   " * 19
        self._safe_addstr(win, WALKWAY_Y, 2, dots[:self.width - 4], COLOR_SEPARATOR)

        # === COFFEE / CAFÉ (x=2, y=11 to y=17) ===
        self._safe_addstr(win, 11, 2, "┌───────────┐", COLOR_COFFEE)
        self._safe_addstr(win, 12, 2, "│  ♨  CAFÉ  │", COLOR_COFFEE)
        self._safe_addstr(win, 13, 2, "│  ╭─────╮  │", COLOR_COFFEE)
        self._safe_addstr(win, 14, 2, "│  │     │  │", COLOR_COFFEE)
        self._safe_addstr(win, 15, 2, "│  ╰─────╯  │", COLOR_COFFEE)
        self._safe_addstr(win, 16, 2, "│           │", COLOR_COFFEE)
        self._safe_addstr(win, 17, 2, "└───────────┘", COLOR_COFFEE)

        # === SOFAS (center, y=16 to y=18) ===
        # Sofa 1
        self._safe_addstr(win, 16, 18, "╭━━━━━━╮", COLOR_FURNITURE)
        self._safe_addstr(win, 17, 18, "┃ ░░░░ ┃", COLOR_FURNITURE)
        self._safe_addstr(win, 18, 18, "╰━━━━━━╯", COLOR_FURNITURE)

        # Coffee table between sofas
        self._safe_addstr(win, 17, 27, "◻", COLOR_FURNITURE)

        # Sofa 2
        self._safe_addstr(win, 16, 32, "╭━━━━━━╮", COLOR_FURNITURE)
        self._safe_addstr(win, 17, 32, "┃ ░░░░ ┃", COLOR_FURNITURE)
        self._safe_addstr(win, 18, 32, "╰━━━━━━╯", COLOR_FURNITURE)

        # === WHITEBOARD (right side, y=11 to y=18, flush with right wall) ===
        wb_x = self.width - 17  # 18-char wide strings end at x=78, flush with wall
        self._safe_addstr(win, 11, wb_x, "┌────────────────┐", COLOR_WHITEBOARD)
        self._safe_addstr(win, 12, wb_x, "│  WHITEBOARD    │", COLOR_WHITEBOARD)
        # Show recent tools on whiteboard
        for i in range(4):
            if i < len(self.whiteboard_tools):
                name = self.whiteboard_tools[i][0]
                tool_str = f"│  > {name:<11} │"
            else:
                tool_str = "│                │"
            self._safe_addstr(win, 13 + i, wb_x, tool_str, COLOR_WHITEBOARD)
        self._safe_addstr(win, 17, wb_x, "│                │", COLOR_WHITEBOARD)
        self._safe_addstr(win, 18, wb_x, "└────────────────┘", COLOR_WHITEBOARD)

        # === LOUNGE label ===
        self._safe_addstr(win, 13, 30, "L O U N G E", COLOR_FURNITURE,
                          curses.A_DIM)

    def draw_status_bar(self, win, max_h, max_w, agent_count, sub_count,
                        active_count, tools_str):
        bar_y = self.height
        bar = (f"  agents: {agent_count} main + {sub_count} sub  |"
               f"  active: {active_count}  |"
               f"  tools: {tools_str}")
        bar = bar[:self.width]
        self._safe_addstr(win, bar_y, 1, bar.ljust(self.width),
                          COLOR_STATUS_BAR, curses.A_BOLD)

    def _safe_addstr(self, win, y, x, s, color_pair, attrs=0):
        max_h, max_w = win.getmaxyx()
        if y < 0 or y >= max_h or x >= max_w:
            return
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
