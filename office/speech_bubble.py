import curses
from office.colors import COLOR_SPEECH

TOOL_ICONS = {
    "Read": "Read",
    "Edit": "Edit",
    "Write": "Write",
    "Bash": "$ Bash",
    "Grep": "Grep",
    "Glob": "Glob",
    "Task": "Task",
    "WebFetch": "Web",
    "WebSearch": "Search",
    "NotebookEdit": "Notebook",
    "AskUserQuestion": "Ask?",
    "EnterPlanMode": "Plan",
    "ExitPlanMode": "Plan OK",
    "Docs": "Docs",
    "TodoWrite": "Todo",
    "SendMessage": "Msg",
    "TaskCreate": "Task+",
    "TaskUpdate": "Task~",
    "unknown": "...",
}

# Tools that require user permission / approval
PERMISSION_TOOLS = {"Edit", "Write", "Bash", "NotebookEdit"}


class SpeechBubble:
    def __init__(self, text, duration_frames=40, persistent=False):
        self.text = text
        self.remaining = duration_frames
        self.width = len(text) + 4
        self.persistent = persistent

    def render(self, win, x, y, color_pair=None):
        if color_pair is None:
            color_pair = COLOR_SPEECH
        max_h, max_w = win.getmaxyx()
        bx = x - self.width // 2
        by = y - 3

        if by < 0:
            by = y + 4  # Show below character if too high
        if bx < 1:
            bx = 1
        if bx + self.width >= max_w - 1:
            bx = max_w - self.width - 1

        if by < 0 or bx < 0:
            return

        top = "\u250c" + "\u2500" * (self.width - 2) + "\u2510"
        mid = "\u2502 " + self.text.ljust(self.width - 4) + " \u2502"
        pointer_pos = self.width // 2
        bot_parts = list("\u2514" + "\u2500" * (self.width - 2) + "\u2518")
        if 0 < pointer_pos < len(bot_parts) - 1:
            bot_parts[pointer_pos] = "\u252c"
        bot = "".join(bot_parts)

        try:
            color = curses.color_pair(color_pair)
            if by < max_h:
                win.addstr(by, bx, top, color)
            if by + 1 < max_h:
                win.addstr(by + 1, bx, mid, color)
            if by + 2 < max_h:
                win.addstr(by + 2, bx, bot, color)
        except curses.error:
            pass

    def tick(self):
        if self.persistent:
            return True
        self.remaining -= 1
        return self.remaining > 0

    @staticmethod
    def for_tool(tool_name):
        text = TOOL_ICONS.get(tool_name, tool_name[:12])
        return SpeechBubble(text, duration_frames=50)

    @staticmethod
    def for_waiting(tool_name):
        text = f"HELP! {tool_name}?"
        return SpeechBubble(text, persistent=True)
