import math
import random
import curses
from office.agent_state import AgentState
from office.speech_bubble import SpeechBubble, PERMISSION_TOOLS
from office.colors import (
    COLOR_MAIN_AGENT, COLOR_SUB_CYAN, COLOR_SUB_GREEN, COLOR_SUB_YELLOW,
    COLOR_AGENT_NAME, COLOR_WAITING, COLOR_WAITING_BUBBLE,
)

# Sprites: each is 3 lines, ~3 chars wide
SPRITES = {
    "idle_down": [
        " o ",
        "/|\\",
        "/ \\",
    ],
    "walk_1": [
        " o ",
        "/|\\",
        "/ |",
    ],
    "walk_2": [
        " o ",
        "/|\\",
        "| \\",
    ],
    "sitting": [
        " o ",
        "/|\\",
        "_|_",
    ],
    "typing_1": [
        " o ",
        "\\|/",
        "_|_",
    ],
    "typing_2": [
        " o ",
        " |\\",
        "_|_",
    ],
    "waiting_1": [
        "\\o/",
        " | ",
        "/ \\",
    ],
    "waiting_2": [
        " o ",
        "/|\\",
        "/ \\",
    ],
    "coffee_1": [
        " o ",
        "/|>",
        "/ \\",
    ],
    "coffee_2": [
        " o>",
        "/| ",
        "/ \\",
    ],
    "spawning": [
        " . ",
        " : ",
        " . ",
    ],
    "exiting": [
        " * ",
        " * ",
        " * ",
    ],
}

# Color assignments for agent types
AGENT_COLORS = {
    "main": COLOR_MAIN_AGENT,
    "Explore": COLOR_SUB_CYAN,
    "general-purpose": COLOR_SUB_GREEN,
    "code": COLOR_SUB_GREEN,
    "Plan": COLOR_SUB_YELLOW,
    "test": COLOR_SUB_YELLOW,
    "Bash": COLOR_SUB_CYAN,
}

# Walk speed in columns per second
WALK_SPEED = 16.0


class Character:
    def __init__(self, agent_id, name, agent_type="main", desk=None):
        self.agent_id = agent_id
        self.name = name
        self.agent_type = agent_type
        self.color_pair = AGENT_COLORS.get(agent_type, COLOR_SUB_GREEN)
        self.state = AgentState.IDLE
        # Position (float for smooth movement)
        self.x = random.uniform(10, 50)
        self.y = random.uniform(12, 15)
        self.target_x = None
        self.target_y = None
        self.desk = desk
        self.sprite_frame = 0
        self.sprite_timer = 0
        self.speech_bubble = None
        self.wander_timer = random.uniform(2.0, 6.0)
        self.current_tool = None
        self.pending_tool = None  # queued tool if received during SPAWNING
        self.think_timer = 0
        self.spawn_timer = 0
        self.exit_timer = 0
        self.desk_timer = 0
        self.wait_timer = 0
        self._thinking_arrived = False
        self.idle_timer = 0  # tracks how long a subagent has been idle
        self.is_alive = True

    def _is_at_desk(self):
        """Check if character is at or near their desk chair."""
        if not self.desk:
            return False
        return (abs(self.x - self.desk["chair_x"]) < 1.0 and
                abs(self.y - self.desk["chair_y"]) < 1.0)

    def _walk_to_desk(self):
        """Start walking to assigned desk."""
        if self.desk:
            self.target_x = float(self.desk["chair_x"])
            self.target_y = float(self.desk["chair_y"])
            self.state = AgentState.WALKING
            self.sprite_timer = 0

    def on_tool_start(self, tool_name):
        self.current_tool = tool_name
        self.desk_timer = 0
        self.idle_timer = 0

        # Clear waiting state if a new tool comes in
        if self.state == AgentState.WAITING:
            self.speech_bubble = None

        # If spawning, queue the tool for when spawn finishes
        if self.state == AgentState.SPAWNING:
            self.pending_tool = tool_name
            return

        # If already at desk, just switch to working
        if self._is_at_desk() and self.state in (
            AgentState.IDLE, AgentState.WORKING, AgentState.SITTING,
            AgentState.THINKING, AgentState.WANDERING,
        ):
            self.state = AgentState.WORKING
            self.speech_bubble = SpeechBubble.for_tool(tool_name)
            return

        # If already walking to desk, just update the bubble
        if self.state == AgentState.WALKING:
            self.speech_bubble = SpeechBubble.for_tool(tool_name)
            return

        # From any other state (IDLE, WANDERING, etc.) -> walk to desk
        self.speech_bubble = SpeechBubble.for_tool(tool_name)
        self._walk_to_desk()

    def on_tool_end(self):
        prev_tool = self.current_tool
        self.current_tool = None
        self.speech_bubble = None
        if self.state == AgentState.WORKING:
            self._go_get_coffee()
        elif self.state == AgentState.WALKING:
            # Tool ended before agent reached desk (fast tools like WebSearch).
            # Let the walk finish -- arrival will see no current_tool and sit
            # briefly before returning to lounge.
            pass
        elif self.state == AgentState.WAITING:
            # Permission was granted, go back to working briefly
            self.state = AgentState.WORKING
            self.desk_timer = 0

    def _go_get_coffee(self):
        """Walk to the coffee machine to think."""
        from office.scene import COFFEE_SPOT
        self.target_x = float(COFFEE_SPOT["x"]) + random.uniform(-2, 4)
        self.target_y = float(COFFEE_SPOT["y"]) + random.uniform(0, 2)
        self.state = AgentState.THINKING
        self.think_timer = random.uniform(3.0, 6.0)
        self.sprite_timer = 0
        self._thinking_arrived = False

    def on_waiting(self, tool_name):
        """Agent needs permission or user input."""
        self.state = AgentState.WAITING
        self.speech_bubble = SpeechBubble.for_waiting(tool_name)
        self.sprite_timer = 0
        self.wait_timer = 0

    def on_turn_end(self):
        self.current_tool = None
        self.pending_tool = None
        self.speech_bubble = None
        self._return_to_lounge()

    def on_exit(self):
        self.state = AgentState.EXITING
        self.exit_timer = 1.5
        self.speech_bubble = None

    def tick(self, dt):
        if not self.is_alive:
            return

        # Tick speech bubble
        if self.speech_bubble:
            if not self.speech_bubble.tick():
                self.speech_bubble = None

        if self.state == AgentState.SPAWNING:
            self.spawn_timer -= dt
            if self.spawn_timer <= 0:
                # If a tool was queued during spawn, go work on it
                if self.pending_tool:
                    tool = self.pending_tool
                    self.pending_tool = None
                    self.current_tool = tool
                    self.speech_bubble = SpeechBubble.for_tool(tool)
                    self._walk_to_desk()
                else:
                    self.state = AgentState.IDLE
                    self.wander_timer = random.uniform(1.0, 3.0)

        elif self.state == AgentState.EXITING:
            self.exit_timer -= dt
            if self.exit_timer <= 0:
                self.is_alive = False

        elif self.state == AgentState.IDLE:
            self.wander_timer -= dt
            self.idle_timer += dt
            if self.agent_type != "main" and self.idle_timer > 20.0:
                # Subagent has been idle too long -- go home
                self.on_exit()
            elif self.wander_timer <= 0:
                self._start_wander()

        elif self.state == AgentState.WANDERING:
            self._move_toward_target(dt)
            self.idle_timer += dt
            if self.agent_type != "main" and self.idle_timer > 20.0:
                self.on_exit()
            elif self._at_target():
                self.state = AgentState.IDLE
                self.wander_timer = random.uniform(2.0, 6.0)

        elif self.state == AgentState.WALKING:
            self._move_toward_target(dt)
            if self._at_target():
                # Arrived at desk
                if self.current_tool:
                    self.state = AgentState.WORKING
                    self.desk_timer = 0
                    self.speech_bubble = SpeechBubble.for_tool(self.current_tool)
                else:
                    self.state = AgentState.SITTING
                self.sprite_timer = 0

        elif self.state == AgentState.SITTING:
            self.sprite_timer += dt
            self.desk_timer += dt
            if self.sprite_timer > 0.5:
                if self.current_tool:
                    self.state = AgentState.WORKING
                    self.desk_timer = 0
                else:
                    self.state = AgentState.THINKING
                    self.think_timer = random.uniform(2.0, 5.0)

        elif self.state == AgentState.WORKING:
            self.sprite_timer += dt
            self.desk_timer += dt
            if (self.desk_timer > 5.0
                    and self.current_tool in PERMISSION_TOOLS):
                # No new event for 5s on a permission-gated tool --
                # likely waiting for user approval.
                self.on_waiting(self.current_tool)
            elif self.desk_timer > 10.0:
                self.current_tool = None
                self.speech_bubble = None
                self._return_to_lounge()

        elif self.state == AgentState.THINKING:
            if not getattr(self, '_thinking_arrived', False):
                # Walking to coffee spot
                self._move_toward_target(dt)
                if self._at_target():
                    self._thinking_arrived = True
                    self.sprite_timer = 0
            else:
                # Sipping coffee
                self.sprite_timer += dt
                self.think_timer -= dt
                if self.think_timer <= 0:
                    self._return_to_lounge()

        elif self.state == AgentState.WAITING:
            # Blink animation timer
            self.sprite_timer += dt
            self.wait_timer += dt
            # Auto-clear after 15s if no resolution event
            if self.wait_timer > 15.0:
                self.speech_bubble = None
                self._return_to_lounge()

    def get_current_sprite(self):
        if self.state == AgentState.SPAWNING:
            return SPRITES["spawning"]
        if self.state == AgentState.EXITING:
            return SPRITES["exiting"]
        if self.state == AgentState.IDLE:
            return SPRITES["idle_down"]
        if self.state == AgentState.THINKING:
            if not getattr(self, '_thinking_arrived', False):
                # Walking to coffee
                frame = int(self.sprite_timer * 4) % 2
                return SPRITES["walk_1"] if frame == 0 else SPRITES["walk_2"]
            else:
                # Sipping coffee
                frame = int(self.sprite_timer * 1.5) % 2
                return SPRITES["coffee_1"] if frame == 0 else SPRITES["coffee_2"]
        if self.state in (AgentState.WANDERING, AgentState.WALKING):
            frame = int(self.sprite_timer * 4) % 2
            return SPRITES["walk_1"] if frame == 0 else SPRITES["walk_2"]
        if self.state == AgentState.SITTING:
            return SPRITES["sitting"]
        if self.state == AgentState.WORKING:
            frame = int(self.sprite_timer * 3) % 2
            return SPRITES["typing_1"] if frame == 0 else SPRITES["typing_2"]
        if self.state == AgentState.WAITING:
            # Arms up/down blinking animation
            frame = int(self.sprite_timer * 2) % 2
            return SPRITES["waiting_1"] if frame == 0 else SPRITES["waiting_2"]
        return SPRITES["idle_down"]

    def render(self, win):
        sprite = self.get_current_sprite()
        ix = int(self.x)
        iy = int(self.y)
        max_h, max_w = win.getmaxyx()

        # Use red color when waiting, normal color otherwise
        if self.state == AgentState.WAITING:
            blink = int(self.sprite_timer * 3) % 2
            if blink:
                color = curses.color_pair(COLOR_WAITING) | curses.A_BOLD
            else:
                color = curses.color_pair(self.color_pair) | curses.A_BOLD
        else:
            color = curses.color_pair(self.color_pair)
            if self.agent_type == "main":
                color |= curses.A_BOLD

        for row_offset, line in enumerate(sprite):
            sy = iy + row_offset
            sx = ix - 1
            if 0 <= sy < max_h and 0 <= sx < max_w - 3:
                try:
                    win.addstr(sy, sx, line, color)
                except curses.error:
                    pass

        # Name label below character
        name_y = iy + 3
        name_x = ix - len(self.name) // 2
        if 0 <= name_y < max_h and 0 <= name_x < max_w - len(self.name):
            try:
                win.addstr(name_y, name_x, self.name,
                           curses.color_pair(COLOR_AGENT_NAME) | curses.A_DIM)
            except curses.error:
                pass

    def render_bubble(self, win):
        """Render speech bubble separately (called after all characters)."""
        if not self.speech_bubble:
            return
        if self.state == AgentState.WAITING:
            self.speech_bubble.render(win, int(self.x), int(self.y),
                                      color_pair=COLOR_WAITING_BUBBLE)
        else:
            self.speech_bubble.render(win, int(self.x), int(self.y))

    def _return_to_lounge(self):
        from office.scene import LOUNGE_AREA
        self.target_x = random.uniform(LOUNGE_AREA["x_min"],
                                       LOUNGE_AREA["x_max"])
        self.target_y = random.uniform(LOUNGE_AREA["y_min"],
                                       LOUNGE_AREA["y_max"])
        self.state = AgentState.WANDERING
        self.sprite_timer = 0

    def _start_wander(self):
        from office.scene import LOUNGE_AREA
        self.target_x = random.uniform(LOUNGE_AREA["x_min"],
                                       LOUNGE_AREA["x_max"])
        self.target_y = random.uniform(LOUNGE_AREA["y_min"],
                                       LOUNGE_AREA["y_max"])
        self.state = AgentState.WANDERING
        self.sprite_timer = 0

    def _move_toward_target(self, dt):
        if self.target_x is None or self.target_y is None:
            return
        dx = self.target_x - self.x
        dy = self.target_y - self.y
        dist = math.hypot(dx, dy)
        if dist < 0.5:
            self.x = self.target_x
            self.y = self.target_y
            return
        step = WALK_SPEED * dt
        if step > dist:
            step = dist
        self.x += (dx / dist) * step
        self.y += (dy / dist) * step
        self.sprite_timer += dt

    def _at_target(self):
        if self.target_x is None or self.target_y is None:
            return True
        return (abs(self.x - self.target_x) < 0.5 and
                abs(self.y - self.target_y) < 0.5)
