# Claude Office

A terminal-based ASCII animation that visualizes Claude Code agents as characters in a virtual office. Watch your agents walk to desks, type away, and show what tools they're using -- all in your terminal.

Inspired by [pixel-agents](https://github.com/pablodelucca/pixel-agents).

```
╔══════════════════════════════════════════════════════════════════════════════════╗
║  CLAUDE CODE OFFICE                                              14:32:05      ║
╠══════════════════════════════════════════════════════════════════════════════════╣
║    ┌─────────────┬─────────────┬─────────────┬─────────────┐                   ║
║    │    ▓▓▓▓▓    │    ▓▓▓▓▓    │    ▓▓▓▓▓    │    ▓▓▓▓▓    │                   ║
║    │   ═══════   │   ═══════   │   ═══════   │   ═══════   │                   ║
║    │  ┌──────┐◇  │      ◇     │      ◇      │      ◇      │                   ║
║    └──│[Read]│───┴─────────────┴─────────────┴─────────────┘                   ║
║       └──┬───┘                                                                 ║
║  ·   ·    o  ·   ·   ·   ·   ·   ·   ·   ·   ·   ·   ·   ·   ·   ·   ·      ║
║          \|/                                                                   ║
║  ┌───────────┐  _|_                                       ┌────────────────┐   ║
║  │  ♨  CAFÉ  │  main    o                                 │  WHITEBOARD    │   ║
║  │  ╭─────╮  │         /|\          L O U N G E           │  > Read        │   ║
║  │  │     │  │        / |                                 │  > Edit        │   ║
║  │  ╰─────╯  │       sub-1                                │  > Bash        │   ║
║  │           │                                            │                │   ║
║  └───────────┘  ╭━━━━━━╮  ◻  ╭━━━━━━╮                    └────────────────┘   ║
║                 ┃ ░░░░ ┃     ┃ ░░░░ ┃                                          ║
║                 ╰━━━━━━╯     ╰━━━━━━╯                                          ║
║                                                                                ║
║                                                                                ║
║  agents: 1 main + 1 sub  |  active: 1  |  tools: Read                         ║
╚══════════════════════════════════════════════════════════════════════════════════╝
```

## Requirements

- Python 3 (uses built-in `curses` -- no dependencies)
- A terminal with at least 80 columns and 24 rows

## Usage

```bash
# Demo mode -- simulated agents, no Claude Code needed
python3 claude_office.py --demo

# Watch real Claude Code activity (auto-detects the active session)
python3 claude_office.py

# Watch a specific project directory
python3 claude_office.py --project /path/to/your/project

# Watch a specific session by UUID
python3 claude_office.py --session abc123

# Watch other AI coding CLIs
python3 claude_office.py --codex      # OpenAI Codex CLI
python3 claude_office.py --kiro       # Kiro CLI
python3 claude_office.py --opencode   # OpenCode
```

Press `q` to quit.

### Running alongside Claude Code

Open two tmux panes side by side:

```bash
# Pane 1: Claude Code
claude

# Pane 2: Claude Office
python3 claude_office.py
```

Characters will react in real time as Claude reads files, edits code, runs commands, and spawns subagents.

## What you'll see

- **Main agent** (white, bold) -- represents your Claude Code session
- **Subagents** (colored) -- spawn when Claude uses the Task tool
  - Cyan: Explore / Bash agents
  - Green: general-purpose / code agents
  - Yellow: Plan / test agents
- **Cubicles** -- 4 workstations with monitors, desk surfaces, and chairs
- **Speech bubbles** show the active tool: `[Read]`, `[Edit]`, `[$ Bash]`, `[Grep]`, `[Glob]`, `[Task]`, `[thinking..]`, etc.
- **Whiteboard** (right wall) -- tracks recently used tools
- **Café** (left side) -- coffee break room with counter where agents go to think
- **Sofas** (center) -- rounded lounging area with cushions and a coffee table
- **Status bar** shows agent count, active workers, and current tools

## How it works

Claude Office tails the JSONL transcript files that Claude Code writes to `~/.claude/projects/`. It detects tool usage, subagent spawns, and turn completions, then maps those events to character animations:

1. Agent generates text -- character walks to their desk and "thinks"
2. Agent uses a tool -- character starts typing, speech bubble shows tool name
3. Tool finishes -- character takes a coffee break
4. Turn ends -- character walks back to the lounge
5. Subagent spawns -- new character appears
6. Subagent finishes -- character fades out

## Project structure

```
claude_office.py              # Entry point
office/
  app.py                      # Main loop (10 FPS curses)
  scene.py                    # Office layout and furniture
  character.py                # ASCII sprites, state machine, movement
  renderer.py                 # Draws scene to terminal
  speech_bubble.py            # Tool name bubbles
  agent_state.py              # State enum
  colors.py                   # ANSI color pairs
  watchers/
    __init__.py               # BaseWatcher interface
    claude.py                 # Claude Code JSONL file watcher
    codex.py                  # OpenAI Codex CLI watcher
    kiro.py                   # Kiro CLI watcher
    opencode.py               # OpenCode watcher
    demo.py                   # Simulated events for demo mode
```
