import os
import json
import glob
import time


class TranscriptWatcher:
    def __init__(self, project_path=None, session_id=None):
        self.project_dir = self._resolve_project_dir(project_path)
        self.session_id = session_id
        self.file_positions = {}
        self.known_agents = set()
        self._last_scan = 0
        self._scan_interval = 2.0
        self._tracked_files = []

    def _resolve_project_dir(self, project_path):
        if project_path is None:
            project_path = os.getcwd()
        project_path = os.path.abspath(project_path)
        projects_root = os.path.expanduser("~/.claude/projects")

        # Try exact encoding first (slash -> hyphen)
        encoded = project_path.replace("/", "-")
        candidate = os.path.join(projects_root, encoded)
        if os.path.isdir(candidate):
            return candidate

        # Claude Code may also replace underscores with hyphens or
        # normalize differently. Try matching against existing dirs.
        if os.path.isdir(projects_root):
            # Build a normalized version for fuzzy matching
            # e.g. /Users/edison/foo_bar -> users-edison-foo-bar (lowercase)
            norm = project_path.replace("/", "-").replace("_", "-").lower()
            for entry in os.listdir(projects_root):
                entry_norm = entry.replace("_", "-").lower()
                if entry_norm == norm:
                    return os.path.join(projects_root, entry)

            # Last resort: find the most recently modified project dir
            # that contains a .jsonl file (catches any encoding mismatch)
            best_dir = None
            best_mtime = 0
            for entry in os.listdir(projects_root):
                entry_path = os.path.join(projects_root, entry)
                if not os.path.isdir(entry_path):
                    continue
                jsonls = glob.glob(os.path.join(entry_path, "*.jsonl"))
                if jsonls:
                    mtime = max(os.path.getmtime(f) for f in jsonls)
                    if mtime > best_mtime:
                        best_mtime = mtime
                        best_dir = entry_path
            if best_dir:
                return best_dir

        return candidate

    def _find_latest_session(self):
        pattern = os.path.join(self.project_dir, "*.jsonl")
        files = glob.glob(pattern)
        if not files:
            return None
        return max(files, key=os.path.getmtime)

    def _find_subagent_files(self, session_base):
        pattern = os.path.join(session_base, "subagents", "*.jsonl")
        return glob.glob(pattern)

    def _scan_files(self):
        now = time.monotonic()
        if now - self._last_scan < self._scan_interval:
            return
        self._last_scan = now

        self._tracked_files = []

        if self.session_id:
            session_file = os.path.join(self.project_dir,
                                        f"{self.session_id}.jsonl")
            if os.path.exists(session_file):
                self._tracked_files.append(("main", session_file))
                session_base = os.path.join(self.project_dir, self.session_id)
                for sf in self._find_subagent_files(session_base):
                    agent_id = os.path.basename(sf).replace(".jsonl", "")
                    self._tracked_files.append((agent_id, sf))
        else:
            session_file = self._find_latest_session()
            if session_file:
                self._tracked_files.append(("main", session_file))
                session_id = os.path.basename(session_file).replace(
                    ".jsonl", "")
                session_base = os.path.join(self.project_dir, session_id)
                for sf in self._find_subagent_files(session_base):
                    agent_id = os.path.basename(sf).replace(".jsonl", "")
                    self._tracked_files.append((agent_id, sf))

    def poll(self):
        self._scan_files()
        events = []
        for agent_id, filepath in self._tracked_files:
            events.extend(self._read_new_lines(filepath, agent_id))
        return events

    def _read_new_lines(self, filepath, agent_id):
        events = []
        pos = self.file_positions.get(filepath, 0)

        # On first encounter, skip to end (don't replay history)
        if filepath not in self.file_positions:
            try:
                self.file_positions[filepath] = os.path.getsize(filepath)
            except OSError:
                self.file_positions[filepath] = 0
            return events

        try:
            with open(filepath, "r") as f:
                f.seek(pos)
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        record = json.loads(line)
                        event = self._parse_record(record, agent_id)
                        if event:
                            events.append(event)
                    except json.JSONDecodeError:
                        pass
                self.file_positions[filepath] = f.tell()
        except (FileNotFoundError, OSError):
            pass
        return events

    def _parse_record(self, record, agent_id):
        rec_type = record.get("type")

        if rec_type == "assistant":
            content = record.get("message", {}).get("content", [])
            for block in content:
                if isinstance(block, dict) and block.get("type") == "tool_use":
                    tool_name = block.get("name", "unknown")
                    if tool_name == "Task":
                        sub_type = (block.get("input", {})
                                    .get("subagent_type", "agent"))
                        desc = (block.get("input", {})
                                .get("description", "subtask"))
                        return {
                            "event": "spawn_subagent",
                            "agent_id": agent_id,
                            "subagent_type": sub_type,
                            "description": desc,
                        }
                    return {
                        "event": "tool_start",
                        "agent_id": agent_id,
                        "tool": tool_name,
                    }

        elif rec_type == "result":
            return {
                "event": "tool_end",
                "agent_id": agent_id,
            }

        elif (rec_type == "system"
              and record.get("subtype") == "turn_duration"):
            return {
                "event": "turn_end",
                "agent_id": agent_id,
            }

        return None

    def get_status(self):
        if not self._tracked_files:
            return "No active session found"
        main_file = None
        sub_count = 0
        for agent_id, fp in self._tracked_files:
            if agent_id == "main":
                main_file = fp
            else:
                sub_count += 1
        if main_file:
            session = os.path.basename(main_file)[:8]
            return f"Session: {session}... (+{sub_count} sub)"
        return "Scanning..."
