import os
import json
import time
from office.watchers import BaseWatcher

# Map OpenCode tool names to Claude Office display names
TOOL_NAME_MAP = {
    "read": "Read",
    "edit": "Edit",
    "write": "Write",
    "bash": "Bash",
    "glob": "Glob",
    "grep": "Grep",
    "list": "Glob",
    "webfetch": "WebFetch",
    "todowrite": "Write",
    "context7_resolve-library-id": "Docs",
    "context7_query-docs": "Docs",
    "invalid": "unknown",
}


class OpenCodeWatcher(BaseWatcher):
    """Watch OpenCode SQLite database for session activity.

    OpenCode stores data across ``session``, ``message``, and ``part`` tables.
    The ``part`` table contains granular events:
      - type=tool   with state.status in {pending, running, completed, error}
      - type=step-start / step-finish  (turn boundaries)

    Subagents are spawned via ``tool: "task"`` and run in their own session
    (recorded in ``state.metadata.sessionId``).  We track those child sessions
    so subagent tool activity is also visualised.
    """

    SOURCE_NAME = "OPENCODE"

    DB_PATH = os.path.expanduser("~/.local/share/opencode/opencode.db")

    def __init__(self, db_path=None):
        self.db_path = db_path or self.DB_PATH
        self._initialized = False
        self._last_poll = 0
        self._poll_interval = 0.5
        self._session_id = None
        self._session_scan = 0
        # Track which callIDs we've already emitted tool_start for
        self._active_calls = {}  # callID -> agent_id
        # Per-session high-water-mark for part rowids
        self._row_ids = {}  # session_id -> last_rowid
        # Subagent sessions: child_session_id -> agent_id
        self._sub_sessions = {}
        self._sub_counter = 0
        # Deferred tool_end events for single-record tool completions.
        # When OpenCode writes only a completed record (no prior pending),
        # we emit tool_start immediately and queue tool_end for next poll.
        self._deferred_ends = []  # list of {"event": "tool_end", ...}

    def _get_connection(self):
        import sqlite3
        if not os.path.exists(self.db_path):
            return None
        try:
            conn = sqlite3.connect(
                f"file:{self.db_path}?mode=ro", uri=True,
                check_same_thread=False,
            )
            conn.row_factory = sqlite3.Row
            return conn
        except sqlite3.Error:
            return None

    def _find_latest_session(self, conn):
        """Find the most recently updated session ID."""
        now = time.monotonic()
        if self._session_id and now - self._session_scan < 5.0:
            return self._session_id
        self._session_scan = now
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT id FROM session ORDER BY time_updated DESC LIMIT 1"
            )
            row = cur.fetchone()
            if row:
                self._session_id = row["id"]
        except Exception:
            pass
        return self._session_id

    def _skip_to_end(self, conn, session_id):
        """Set high-water mark to the current max rowid for a session."""
        cur = conn.cursor()
        cur.execute(
            "SELECT MAX(rowid) FROM part WHERE session_id = ?",
            (session_id,),
        )
        row = cur.fetchone()
        self._row_ids[session_id] = (row[0] or 0) if row else 0

    def poll(self):
        now = time.monotonic()
        if now - self._last_poll < self._poll_interval:
            return []
        self._last_poll = now

        conn = self._get_connection()
        if conn is None:
            return []

        events = []

        # Flush any deferred tool_end events from the previous poll
        if self._deferred_ends:
            events.extend(self._deferred_ends)
            self._deferred_ends = []

        try:
            session_id = self._find_latest_session(conn)
            if not session_id:
                return events

            if not self._initialized:
                self._skip_to_end(conn, session_id)
                self._initialized = True
                return events

            # Poll main session + all tracked subagent sessions
            sessions_to_poll = [(session_id, "main")]
            for sub_sid, agent_id in list(self._sub_sessions.items()):
                sessions_to_poll.append((sub_sid, agent_id))

            cur = conn.cursor()
            for sid, agent_id in sessions_to_poll:
                last_row = self._row_ids.get(sid, 0)
                cur.execute(
                    "SELECT rowid, data FROM part "
                    "WHERE session_id = ? AND rowid > ? ORDER BY rowid",
                    (sid, last_row),
                )
                rows = cur.fetchall()
                for row in rows:
                    self._row_ids[sid] = row["rowid"]
                    try:
                        data = json.loads(row["data"])
                    except (json.JSONDecodeError, TypeError):
                        continue
                    parsed = self._parse_part(data, agent_id)
                    if parsed:
                        events.extend(parsed)
        except Exception:
            pass
        finally:
            conn.close()
        return events

    def _parse_part(self, data, agent_id):
        """Parse a part row and return a list of events (usually 0 or 1)."""
        part_type = data.get("type", "")

        if part_type == "tool":
            call_id = data.get("callID", "")
            tool_raw = data.get("tool", "unknown")
            status = (data.get("state") or {}).get("status", "")

            # Handle subagent spawning via task tool
            if tool_raw == "task":
                return self._handle_task_tool(data, call_id, agent_id, status)

            tool = TOOL_NAME_MAP.get(tool_raw, tool_raw.capitalize())

            if status in ("pending", "running"):
                if call_id not in self._active_calls:
                    self._active_calls[call_id] = agent_id
                    return [{"event": "tool_start", "agent_id": agent_id,
                             "tool": tool}]
            elif status in ("completed", "error"):
                if call_id in self._active_calls:
                    # We already emitted tool_start for this call
                    self._active_calls.pop(call_id, None)
                    return [{"event": "tool_end", "agent_id": agent_id}]
                else:
                    # OpenCode often writes a single record with
                    # status=completed (no prior pending/running).
                    # Emit tool_start now and defer tool_end to next
                    # poll so the animation has time to play.
                    self._deferred_ends.append(
                        {"event": "tool_end", "agent_id": agent_id})
                    return [{"event": "tool_start", "agent_id": agent_id,
                             "tool": tool}]

        elif part_type == "step-finish":
            reason = data.get("reason", "")
            if reason == "stop":
                return [{"event": "turn_end", "agent_id": agent_id}]

        return []

    def _handle_task_tool(self, data, call_id, agent_id, status):
        """Handle task tool calls -- spawn / finish subagents."""
        state = data.get("state") or {}
        events = []

        if status in ("pending", "running"):
            if call_id not in self._active_calls:
                self._active_calls[call_id] = agent_id
                inp = state.get("input", {})
                sub_type = inp.get("subagent_type", "agent")
                desc = inp.get("description", "subtask")

                # Register the child session if available
                meta = state.get("metadata") or {}
                child_sid = meta.get("sessionId")

                self._sub_counter += 1
                sub_agent_id = f"sub-{self._sub_counter}"

                if child_sid:
                    self._sub_sessions[child_sid] = sub_agent_id
                    # Start tracking from the beginning of the child session
                    self._row_ids.setdefault(child_sid, 0)

                events.append({
                    "event": "spawn_subagent",
                    "agent_id": agent_id,
                    "subagent_type": sub_type,
                    "description": desc,
                })

        elif status in ("completed", "error"):
            self._active_calls.pop(call_id, None)

            # Find which subagent this task maps to via child session
            meta = state.get("metadata") or {}
            child_sid = meta.get("sessionId")
            sub_agent_id = None
            if child_sid:
                sub_agent_id = self._sub_sessions.pop(child_sid, None)

            if sub_agent_id:
                events.append({
                    "event": "turn_end",
                    "agent_id": sub_agent_id,
                })
            # Also signal tool_end on the parent
            events.append({"event": "tool_end", "agent_id": agent_id})

        return events

    def get_status(self):
        if os.path.exists(self.db_path):
            if self._session_id:
                subs = len(self._sub_sessions)
                extra = f" +{subs} sub" if subs else ""
                return f"OpenCode: {self._session_id[:12]}...{extra}"
            return "OpenCode: scanning..."
        return "OpenCode: DB not found"
