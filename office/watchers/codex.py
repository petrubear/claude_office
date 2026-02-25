import os
import json
import glob
import time
from office.watchers import BaseWatcher


class CodexWatcher(BaseWatcher):
    """Watch OpenAI Codex CLI JSONL session transcripts."""

    SOURCE_NAME = "CODEX"

    def __init__(self):
        self.sessions_root = os.path.expanduser("~/.codex/sessions")
        self.file_position = 0
        self.current_file = None
        self._last_scan = 0
        self._scan_interval = 2.0

    def _find_latest_rollout(self):
        """Find the most recently modified rollout-*.jsonl file."""
        pattern = os.path.join(self.sessions_root, "**", "rollout-*.jsonl")
        files = glob.glob(pattern, recursive=True)
        if not files:
            return None
        return max(files, key=os.path.getmtime)

    def poll(self):
        now = time.monotonic()
        if now - self._last_scan > self._scan_interval:
            self._last_scan = now
            latest = self._find_latest_rollout()
            if latest and latest != self.current_file:
                self.current_file = latest
                # Skip to end on first encounter
                try:
                    self.file_position = os.path.getsize(latest)
                except OSError:
                    self.file_position = 0
                return []

        if not self.current_file:
            return []

        events = []
        try:
            with open(self.current_file, "r") as f:
                f.seek(self.file_position)
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        record = json.loads(line)
                        event = self._parse_record(record)
                        if event:
                            events.append(event)
                    except json.JSONDecodeError:
                        pass
                self.file_position = f.tell()
        except (FileNotFoundError, OSError):
            pass
        return events

    def _parse_record(self, record):
        rec_type = record.get("type", "")

        if rec_type == "item.started":
            item = record.get("item", {})
            item_type = item.get("type", "")
            if item_type == "command_execution":
                return {"event": "tool_start", "agent_id": "main",
                        "tool": "Bash"}
            elif item_type == "file_changes":
                return {"event": "tool_start", "agent_id": "main",
                        "tool": "Edit"}
            elif item_type == "mcp_tool_call":
                tool_name = item.get("name", "mcp-tool")
                return {"event": "tool_start", "agent_id": "main",
                        "tool": tool_name}
            # Generic fallback for other item types
            return {"event": "tool_start", "agent_id": "main",
                    "tool": item_type or "unknown"}

        elif rec_type == "item.completed":
            return {"event": "tool_end", "agent_id": "main"}

        elif rec_type == "turn.completed":
            return {"event": "turn_end", "agent_id": "main"}

        return None

    def get_status(self):
        if self.current_file:
            basename = os.path.basename(self.current_file)
            return f"Codex: {basename[:20]}"
        return "Codex: no session found"
