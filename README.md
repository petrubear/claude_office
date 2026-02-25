# Claude Office

A terminal-based ASCII animation that visualizes Claude Code agents as characters in a virtual office. Watch your agents walk to desks, type away, and show what tools they're using -- all in your terminal.

Inspired by [pixel-agents](https://github.com/pablodelucca/pixel-agents).

```
╔══════════════════════════════════════════════════════════════════════════════╗
║  CLAUDE CODE OFFICE                                        14:32:05       ║
╠══════════════════════════════════════════════════════════════════════════════╣
║         ┌───────┐        ┌───────┐        ┌───────┐        ┌───────┐     ║
║         │ ▓▓▓   │        │ ▓▓▓   │        │ ▓▓▓   │        │ ▓▓▓   │     ║
║         └───┬───┘        └───┬───┘        └───┬───┘        └───┬───┘     ║
║          ┌──────┐            ◇               ◇               ◇           ║
║          │[Read]│                                                         ║
║          └──┬───┘                                                         ║
║              o                                                            ║
║             \|/            ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─        ║
║             _|_                                                           ║
║             main           o                                              ║
║                           /|\                                             ║
║  ┌───┐                   / |          ┌──────────────┐                    ║
║  │ ♨ │  LOUNGE          sub-1         │ WHITEBOARD   │                    ║
║  └───┘                                │ > Read       │                    ║
║                                       │ > Edit       │                    ║
║         ┌───────┐  ┌───────┐          │ > Bash       │                    ║
║         │sofa   │  │sofa   │          └──────────────┘                    ║
║         └───────┘  └───────┘                                              ║
║  agents: 1 main + 1 sub  |  active: 1  |  tools: Read                    ║
╚══════════════════════════════════════════════════════════════════════════════╝
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
- **Speech bubbles** show the active tool: `[Read]`, `[Edit]`, `[$ Bash]`, `[Grep]`, `[Glob]`, `[Task]`, etc.
- **Whiteboard** tracks recently used tools
- **Status bar** shows agent count, active workers, and current tools

## How it works

Claude Office tails the JSONL transcript files that Claude Code writes to `~/.claude/projects/`. It detects tool usage, subagent spawns, and turn completions, then maps those events to character animations:

1. Agent uses a tool -- character walks to their desk and starts typing
2. Tool finishes -- character pauses briefly (thinking)
3. Turn ends -- character walks back to the lounge
4. Subagent spawns -- new character appears
5. Subagent finishes -- character fades out

## Project structure

```
claude_office.py              # Entry point
office/
  app.py                      # Main loop (10 FPS curses)
  scene.py                    # Office layout and furniture
  character.py                # ASCII sprites, state machine, movement
  renderer.py                 # Draws scene to terminal
  speech_bubble.py            # Tool name bubbles
  transcript_watcher.py       # Claude Code JSONL file watcher
  agent_state.py              # State enum
  colors.py                   # ANSI color pairs
demo/
  demo_mode.py                # Simulated events for standalone demo
```
