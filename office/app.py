import curses
import time
import random
from office.colors import init_colors
from office.scene import Scene, DESKS, LOUNGE_AREA
from office.renderer import Renderer
from office.character import Character
from office.agent_state import AgentState


FPS = 10
FRAME_MS = 1000 // FPS

# Default tool to assign subagents so they walk to a desk and work,
# even when their JSONL events are missed (first-encounter file skip).
_TYPE_DEFAULT_TOOLS = {
    "Explore": "Grep",
    "general-purpose": "Edit",
    "Plan": "Read",
    "Bash": "Bash",
    "docs-helper": "WebFetch",
    "test": "Bash",
    "code": "Edit",
}


def _default_tool_for_type(agent_type):
    return _TYPE_DEFAULT_TOOLS.get(agent_type, "Read")


class App:
    def __init__(self, stdscr, watcher=None, project_path=None, demo=False,
                 session_id=None):
        self.stdscr = stdscr
        self.characters = {}
        self.desk_assignments = {}  # agent_id -> desk
        self.sub_counter = 0

        # Build watcher from explicit param or legacy args
        if watcher is not None:
            self.watcher = watcher
        elif demo:
            from office.watchers.demo import DemoWatcher
            self.watcher = DemoWatcher()
        else:
            from office.watchers.claude import ClaudeWatcher
            self.watcher = ClaudeWatcher(project_path, session_id)

        source_name = getattr(self.watcher, "SOURCE_NAME", "CLAUDE CODE")
        self.scene = Scene(source_name=source_name)
        self.renderer = Renderer(stdscr)

        # Create main agent
        desk = self._assign_desk("main")
        if desk:
            self.scene.set_desk_agent(desk["id"], "main")
        main_char = Character("main", "main", "main", desk)
        main_char.x = random.uniform(LOUNGE_AREA["x_min"],
                                     LOUNGE_AREA["x_max"])
        main_char.y = random.uniform(LOUNGE_AREA["y_min"],
                                     LOUNGE_AREA["y_max"])
        self.characters["main"] = main_char

    def _assign_desk(self, agent_id):
        if agent_id in self.desk_assignments:
            return self.desk_assignments[agent_id]
        # Find a free desk (not assigned to any living agent)
        used_desks = set()
        for aid, desk in self.desk_assignments.items():
            if aid in self.characters and self.characters[aid].is_alive:
                used_desks.add(desk["id"])
        for desk in DESKS:
            if desk["id"] not in used_desks:
                self.desk_assignments[agent_id] = desk
                return desk
        return None

    def _reclaim_desks(self, dead_ids):
        """Free desk assignments for dead agents."""
        for agent_id in dead_ids:
            desk = self.desk_assignments.pop(agent_id, None)
            if desk:
                self.scene.clear_desk_agent(desk["id"])

    def run(self):
        curses.curs_set(0)
        self.stdscr.nodelay(True)
        init_colors()

        last_time = time.monotonic()

        while True:
            now = time.monotonic()
            dt = now - last_time
            last_time = now

            # Input
            key = self.stdscr.getch()
            if key == ord('q') or key == ord('Q'):
                break
            if key == curses.KEY_RESIZE:
                self.stdscr.clear()

            # Poll for events
            events = self.watcher.poll()
            for event in events:
                self._handle_event(event)

            # Tick scene (whiteboard expiry)
            self.scene.tick_whiteboard()

            # Tick characters
            dead = []
            for agent_id, char in self.characters.items():
                char.tick(dt)
                if not char.is_alive:
                    dead.append(agent_id)
            if dead:
                self._reclaim_desks(dead)
                for agent_id in dead:
                    del self.characters[agent_id]

            # Render
            self.renderer.draw(self.scene, self.characters)

            # Frame timing
            elapsed = time.monotonic() - now
            sleep_ms = max(1, FRAME_MS - int(elapsed * 1000))
            curses.napms(sleep_ms)

    def _handle_event(self, event):
        ev_type = event["event"]
        agent_id = event.get("agent_id", "main")

        if ev_type == "tool_start":
            tool = event.get("tool", "unknown")
            self.scene.update_whiteboard(tool)
            if agent_id not in self.characters:
                # Auto-detected subagent from JSONL -- give clean name
                if agent_id != "main":
                    self.sub_counter += 1
                    name = f"agent-{self.sub_counter}"
                else:
                    name = "main"
                self._spawn_agent(agent_id, name, "general-purpose")
            char = self.characters[agent_id]
            # AskUserQuestion = agent needs help / waiting for user
            if tool == "AskUserQuestion":
                char.on_waiting(tool)
            else:
                char.on_tool_start(tool)

        elif ev_type == "waiting":
            tool = event.get("tool", "permission")
            if agent_id in self.characters:
                self.characters[agent_id].on_waiting(tool)

        elif ev_type == "tool_end":
            if agent_id in self.characters:
                self.characters[agent_id].on_tool_end()

        elif ev_type == "turn_end":
            if agent_id in self.characters:
                if agent_id == "main":
                    self.characters[agent_id].on_turn_end()
                else:
                    # Subagent done -- exit animation
                    self.characters[agent_id].on_exit()

        elif ev_type == "spawn_subagent":
            self.sub_counter += 1
            sub_type = event.get("subagent_type", "agent")
            sub_id = f"sub-{self.sub_counter}"
            # Use short type-based name like "explore-1", "plan-2"
            short_type = sub_type.lower().split("-")[0][:7]
            name = f"{short_type}-{self.sub_counter}"
            self._spawn_agent(sub_id, name, sub_type)
            # Give the subagent an initial tool to work on.
            # Subagent JSONL files are often skipped (first-encounter skip),
            # so without this the character would just idle in the lounge.
            tool = event.get("tool")
            if not tool:
                tool = _default_tool_for_type(sub_type)
            if tool and sub_id in self.characters:
                self.scene.update_whiteboard(tool)
                self.characters[sub_id].on_tool_start(tool)

    def _spawn_agent(self, agent_id, name, agent_type):
        if agent_id in self.characters:
            return
        desk = self._assign_desk(agent_id)
        if desk:
            self.scene.set_desk_agent(desk["id"], name)
        char = Character(agent_id, name, agent_type, desk)
        # Spawn near the entrance door (bottom center)
        char.x = random.uniform(36, 44)
        char.y = 19
        char.state = AgentState.SPAWNING
        char.spawn_timer = 1.0
        self.characters[agent_id] = char
