import random
import time
from office.watchers import BaseWatcher

DEMO_TOOLS = ["Read", "Edit", "Bash", "Grep", "Glob", "Write", "WebSearch",
              "WebFetch", "Task"]
SUB_TYPES = ["Explore", "general-purpose", "Plan", "Bash"]


class DemoWatcher(BaseWatcher):
    """Simulated agent activity for demo / testing."""

    SOURCE_NAME = "DEMO"

    def __init__(self):
        self.next_event = time.monotonic() + 1.5
        self.sub_count = 0
        self.max_subs = 3
        self.active_tools = {}  # agent_id -> tool
        self.sub_alive = set()

    def poll(self):
        now = time.monotonic()
        if now < self.next_event:
            return []

        events = []
        r = random.random()

        if r < 0.30:
            # Main agent uses a tool
            tool = random.choice(DEMO_TOOLS)
            if tool == "Task" and self.sub_count < self.max_subs:
                self.sub_count += 1
                sub_type = random.choice(SUB_TYPES)
                self.sub_alive.add(f"sub-{self.sub_count}")
                events.append({
                    "event": "spawn_subagent",
                    "agent_id": "main",
                    "subagent_type": sub_type,
                    "description": f"subtask-{self.sub_count}",
                })
            else:
                tool = random.choice([t for t in DEMO_TOOLS if t != "Task"])
                events.append({
                    "event": "tool_start",
                    "agent_id": "main",
                    "tool": tool,
                })
                self.active_tools["main"] = tool

        elif r < 0.48 and self.sub_alive:
            # A subagent uses a tool
            sub_id = random.choice(list(self.sub_alive))
            tool = random.choice([t for t in DEMO_TOOLS if t != "Task"])
            events.append({
                "event": "tool_start",
                "agent_id": sub_id,
                "tool": tool,
            })
            self.active_tools[sub_id] = tool

        elif r < 0.62 and self.active_tools:
            # A tool finishes
            agent_id = random.choice(list(self.active_tools.keys()))
            events.append({
                "event": "tool_end",
                "agent_id": agent_id,
            })
            del self.active_tools[agent_id]

        elif r < 0.72 and self.sub_alive and len(self.sub_alive) > 1:
            # A subagent finishes
            sub_id = random.choice(list(self.sub_alive))
            events.append({
                "event": "turn_end",
                "agent_id": sub_id,
            })
            self.sub_alive.discard(sub_id)
            self.active_tools.pop(sub_id, None)

        elif r < 0.78:
            # Agent needs help (waiting for user)
            agent_id = "main"
            if self.sub_alive and random.random() < 0.3:
                agent_id = random.choice(list(self.sub_alive))
            events.append({
                "event": "waiting",
                "agent_id": agent_id,
                "tool": random.choice(["Edit", "Bash", "permission"]),
            })

        elif r < 0.90:
            # Main agent idle moment
            if "main" in self.active_tools:
                events.append({
                    "event": "tool_end",
                    "agent_id": "main",
                })
                del self.active_tools["main"]

        self.next_event = now + random.uniform(0.8, 3.0)
        return events

    def get_status(self):
        return f"Demo mode ({self.sub_count} subs spawned)"
