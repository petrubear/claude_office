"""Watcher plugins for different AI coding CLI tools."""


class BaseWatcher:
    """Base class for transcript/session watchers.

    Each watcher polls a tool-specific data source and returns a list of
    normalised event dicts understood by the App event loop.

    Event format::

        {"event": "tool_start",      "agent_id": "main", "tool": "Read"}
        {"event": "tool_end",        "agent_id": "main"}
        {"event": "spawn_subagent",  "agent_id": "main", "subagent_type": "Explore"}
        {"event": "turn_end",        "agent_id": "main"}
    """

    # Human-readable source name shown in the title bar.
    SOURCE_NAME: str = "UNKNOWN"

    def poll(self) -> list[dict]:
        """Return new events since the last call."""
        raise NotImplementedError

    def get_status(self) -> str:
        """Return a short status string for the status bar."""
        raise NotImplementedError
