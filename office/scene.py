import curses
from office.colors import (
    COLOR_WALL, COLOR_DESK, COLOR_TITLE, COLOR_STATUS_BAR,
    COLOR_FURNITURE, COLOR_SEPARATOR, COLOR_WHITEBOARD,
    COLOR_COFFEE, COLOR_PLANT,
)

# Desk definitions: each desk has a position and a chair position below it
DESKS = [
    {"id": "desk_0", "x": 10, "y": 3, "chair_x": 12, "chair_y": 6},
    {"id": "desk_1", "x": 27, "y": 3, "chair_x": 29, "chair_y": 6},
    {"id": "desk_2", "x": 44, "y": 3, "chair_x": 46, "chair_y": 6},
    {"id": "desk_3", "x": 61, "y": 3, "chair_x": 63, "chair_y": 6},
]

# Lounge spawn area for idle characters (avoids furniture)
LOUNGE_AREA = {"x_min": 10, "x_max": 50, "y_min": 12, "y_max": 15}

# Walkway Y coordinate (characters cross this to go between desk and lounge)
WALKWAY_Y = 10

# Coffee spot -- where characters go to think
COFFEE_SPOT = {"x": 9, "y": 13}


class Scene:
    def __init__(self):
        self.width = 78
        self.height = 22
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
        self._safe_addstr(win, 1, 3, "CLAUDE CODE OFFICE", COLOR_TITLE,
                          curses.A_BOLD)
        clock_x = self.width - len(clock_str) - 1
        if clock_x > 0:
            self._safe_addstr(win, 1, clock_x, clock_str, COLOR_WALL)

    def draw_furniture(self, win, max_h, max_w):
        # Draw desks
        for desk in DESKS:
            x, y = desk["x"], desk["y"]
            self._safe_addstr(win, y, x, "\u250c\u2500\u2500\u2500\u2500\u2500\u2510", COLOR_DESK)
            self._safe_addstr(win, y + 1, x, "\u2502 \u2593\u2593\u2593 \u2502", COLOR_DESK)
            self._safe_addstr(win, y + 2, x, "\u2514\u2500\u2500\u252c\u2500\u2500\u2518", COLOR_DESK)
            # Chair indicator
            cx = desk["chair_x"]
            cy = desk["chair_y"]
            self._safe_addstr(win, cy, cx, "\u25c7", COLOR_DESK)

        # Walkway separator
        sep_y = WALKWAY_Y
        sep_str = " ".join(["\u2500"] * ((self.width - 4) // 2))
        self._safe_addstr(win, sep_y, 2, sep_str, COLOR_SEPARATOR)

        # Coffee machine
        self._safe_addstr(win, 12, 3, "\u250c\u2500\u2500\u2500\u2510", COLOR_COFFEE)
        self._safe_addstr(win, 13, 3, "\u2502 \u2668 \u2502", COLOR_COFFEE)
        self._safe_addstr(win, 14, 3, "\u2514\u2500\u2500\u2500\u2518", COLOR_COFFEE)
        self._safe_addstr(win, 15, 3, "coffee", COLOR_COFFEE)

        # Sofas
        self._safe_addstr(win, 16, 12, "\u250c\u2500\u2500\u2500\u2500\u2500\u2510", COLOR_FURNITURE)
        self._safe_addstr(win, 17, 12, "\u2502sofa \u2502", COLOR_FURNITURE)
        self._safe_addstr(win, 18, 12, "\u2514\u2500\u2500\u2500\u2500\u2500\u2518", COLOR_FURNITURE)

        self._safe_addstr(win, 16, 21, "\u250c\u2500\u2500\u2500\u2500\u2500\u2510", COLOR_FURNITURE)
        self._safe_addstr(win, 17, 21, "\u2502sofa \u2502", COLOR_FURNITURE)
        self._safe_addstr(win, 18, 21, "\u2514\u2500\u2500\u2500\u2500\u2500\u2518", COLOR_FURNITURE)

        # Plant (tucked next to whiteboard, out of walk area)
        wb_left = self.width - 21
        self._safe_addstr(win, 18, wb_left, "(_)", COLOR_PLANT)
        self._safe_addstr(win, 17, wb_left - 1, "/|\\", COLOR_PLANT)
        self._safe_addstr(win, 16, wb_left, "\\|", COLOR_PLANT)

        # Whiteboard
        wb_x = self.width - 18
        self._safe_addstr(win, 12, wb_x, "\u250c\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2510", COLOR_WHITEBOARD)
        self._safe_addstr(win, 13, wb_x, "\u2502 WHITEBOARD   \u2502", COLOR_WHITEBOARD)
        # Show recent tools on whiteboard
        for i in range(4):
            if i < len(self.whiteboard_tools):
                name = self.whiteboard_tools[i][0]
                tool_str = f"\u2502 > {name:<9}\u2502"
            else:
                tool_str = "\u2502             \u2502"
            self._safe_addstr(win, 14 + i, wb_x, tool_str, COLOR_WHITEBOARD)
        self._safe_addstr(win, 18, wb_x, "\u2514\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2518", COLOR_WHITEBOARD)

        # Lounge label
        self._safe_addstr(win, 13, 10, "LOUNGE", COLOR_FURNITURE,
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
