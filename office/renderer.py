import curses
import time
from office.agent_state import AgentState


class Renderer:
    def __init__(self, stdscr):
        self.stdscr = stdscr

    def draw(self, scene, characters):
        self.stdscr.erase()
        max_h, max_w = self.stdscr.getmaxyx()

        if max_h < 24 or max_w < 80:
            self._draw_resize_message(max_h, max_w)
            self.stdscr.refresh()
            return

        # 1. Background (walls, borders)
        scene.draw_background(self.stdscr, max_h, max_w)

        # 2. Title with clock
        clock_str = time.strftime("%H:%M:%S")
        scene.draw_title(self.stdscr, max_w, clock_str)

        # 3. Furniture
        scene.draw_furniture(self.stdscr, max_h, max_w)

        # 4. Characters sorted by Y for depth
        sorted_chars = sorted(characters.values(), key=lambda c: c.y)
        for char in sorted_chars:
            if char.is_alive:
                char.render(self.stdscr)

        # 5. Speech bubbles (on top)
        for char in sorted_chars:
            if char.is_alive:
                char.render_bubble(self.stdscr)

        # 6. Status bar
        alive_chars = [c for c in characters.values() if c.is_alive]
        main_count = sum(1 for c in alive_chars if c.agent_type == "main")
        sub_count = sum(1 for c in alive_chars if c.agent_type != "main")
        active_count = sum(1 for c in alive_chars
                           if c.state == AgentState.WORKING)
        tools = [c.current_tool for c in alive_chars if c.current_tool]
        tools_str = ", ".join(tools[:4]) if tools else "--"

        scene.draw_status_bar(self.stdscr, max_h, max_w,
                              main_count, sub_count, active_count, tools_str)

        self.stdscr.refresh()

    def _draw_resize_message(self, max_h, max_w):
        msg = "Please resize terminal to at least 80x24"
        y = max_h // 2
        x = max(0, (max_w - len(msg)) // 2)
        try:
            self.stdscr.addstr(y, x, msg[:max_w], curses.A_BOLD)
        except curses.error:
            pass
