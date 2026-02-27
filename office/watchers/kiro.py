import os
import json
import time
from office.watchers import BaseWatcher

# Map Kiro tool names to Claude Office display names
TOOL_NAME_MAP = {
    "fs_read": "Read",
    "fs_write": "Write",
    "execute_bash": "Bash",
    "grep": "Grep",
    "glob": "Glob",
    "web_search": "WebSearch",
    "use_subagent": "Task",
    "resolvelibraryid": "WebSearch",
    "querydocs": "WebFetch",
    "dummy": "Read",
}


class KiroWatcher(BaseWatcher):
    """Watch Kiro CLI SQLite database for conversation activity.

    Kiro stores the entire conversation as a single JSON blob in the
    ``conversations_v2`` table, keyed by project path + conversation_id.
    The ``history`` array inside that blob grows as the conversation
    progresses, and ``updated_at`` changes on every write.

    We poll for the most-recently-updated row, compare history length
    to detect new entries, and convert them to normalised events.

    Subagent tool calls are opaque (not visible in history), so we emit
    spawn_subagent events and let App assign IDs.  Subagent characters
    exit naturally via the idle timeout in Character.
    """

    SOURCE_NAME = "KIRO"

    DB_PATH = os.path.expanduser(
        "~/Library/Application Support/kiro-cli/data.sqlite3"
    )

    def __init__(self, db_path=None):
        self.db_path = db_path or self.DB_PATH
        self._initialized = False
        self._last_poll = 0
        self._poll_interval = 0.5
        # Track which conversation we're watching and how far we've read
        self._conv_key = None
        self._conv_id = None
        self._history_len = 0
        self._last_updated = 0

    def _get_connection(self):
        import sqlite3
        if not os.path.exists(self.db_path):
            return None
        conn = sqlite3.connect(
            f"file:{self.db_path}?mode=ro", uri=True,
            check_same_thread=False,
        )
        conn.row_factory = sqlite3.Row
        return conn

    def poll(self):
        now = time.monotonic()
        if now - self._last_poll < self._poll_interval:
            return []
        self._last_poll = now

        conn = self._get_connection()
        if conn is None:
            return []

        events = []
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT key, conversation_id, updated_at, value "
                "FROM conversations_v2 ORDER BY updated_at DESC LIMIT 1"
            )
            row = cur.fetchone()
            if not row:
                conn.close()
                return []

            key = row["key"]
            conv_id = row["conversation_id"]
            updated_at = row["updated_at"]

            # Detect conversation switch
            if key != self._conv_key or conv_id != self._conv_id:
                self._conv_key = key
                self._conv_id = conv_id
                data = json.loads(row["value"])
                history = data.get("history", [])
                self._history_len = len(history)
                self._last_updated = updated_at
                self._initialized = True
                conn.close()
                return []

            # No update since last poll
            if updated_at == self._last_updated:
                conn.close()
                return []

            self._last_updated = updated_at
            data = json.loads(row["value"])
            history = data.get("history", [])
            new_entries = history[self._history_len:]
            self._history_len = len(history)

            for entry in new_entries:
                events.extend(self._parse_entry(entry))

            conn.close()
        except Exception:
            try:
                conn.close()
            except Exception:
                pass
        return events

    def _parse_entry(self, entry):
        """Convert a history entry {user, assistant, ...} to events."""
        events = []
        user = entry.get("user", {})
        user_content = user.get("content", {})
        assistant = entry.get("assistant", {})

        # --- Handle ToolUseResults arriving (user side of entry) ---
        # This means results from the previous entry's tool calls arrived.
        if isinstance(user_content, dict) and "ToolUseResults" in user_content:
            # Tool results arrived — emit tool_end for the main agent.
            # Subagent characters exit naturally via idle timeout in
            # Character (idle_timer > 20s), so we don't emit events for them.
            events.append({"event": "tool_end", "agent_id": "main"})

        # --- Handle assistant response ---
        if "ToolUse" in assistant:
            tu = assistant["ToolUse"]
            tool_uses = tu.get("tool_uses", [])
            for tool in tool_uses:
                name = tool.get("name", "unknown")
                args = tool.get("args", {})
                command = args.get("command", "")

                if name == "use_subagent" and command == "InvokeSubagents":
                    subagents = (args.get("content", {})
                                 .get("subagents", []))
                    # Emit spawn_subagent for each sub; App assigns IDs.
                    # Subagent characters exit via idle timeout in Character.
                    for sub in subagents:
                        events.append({
                            "event": "spawn_subagent",
                            "agent_id": "main",
                            "subagent_type": "general-purpose",
                            "description": sub.get("query", "subtask")[:40],
                            "tool": "Task",
                        })

                elif name == "use_subagent":
                    events.append({
                        "event": "tool_start",
                        "agent_id": "main",
                        "tool": "Task",
                    })
                else:
                    display = TOOL_NAME_MAP.get(name, name.capitalize())
                    events.append({
                        "event": "tool_start",
                        "agent_id": "main",
                        "tool": display,
                    })

            # Emit tool_end for the main agent's tool calls
            events.append({"event": "tool_end", "agent_id": "main"})

        elif "Response" in assistant:
            events.append({"event": "turn_end", "agent_id": "main"})

        return events

    def get_status(self):
        if os.path.exists(self.db_path):
            if self._conv_id:
                return f"Kiro: {self._conv_id[:12]}..."
            return "Kiro: scanning..."
        return "Kiro: DB not found"
