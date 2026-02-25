# AGENTS.md -- Claude Office Developer Guide

## Overview

Claude Office is a zero-dependency Python 3 terminal application (curses) that visualizes Claude Code agent activity as animated ASCII characters in a virtual office. It runs at 10 FPS in any terminal (80x24 minimum) and reads Claude Code's JSONL transcript files to drive the animation in real time.

## Architecture

```
claude_office.py          Entry point (argparse, curses.wrapper)
      |
      v
  office/app.py           Main loop: poll events -> tick characters -> render
      |
      +-- office/transcript_watcher.py   Reads ~/.claude/projects/ JSONL files
      |       or
      +-- demo/demo_mode.py              Generates fake events for demo mode
      |
      +-- office/scene.py                Office layout, furniture, whiteboard
      +-- office/character.py            Character sprites, state machine, movement
      +-- office/renderer.py             Composites scene + characters to curses
      +-- office/speech_bubble.py        Tool name bubbles above characters
      +-- office/agent_state.py          State enum
      +-- office/colors.py               16-color ANSI pairs
```

### Data flow

```
JSONL files --> TranscriptWatcher.poll() --> events list
                                               |
                                               v
                                     App._handle_event()
                                               |
                        +----------------------+----------------------+
                        |                      |                      |
                  tool_start             spawn_subagent          turn_end
                        |                      |                      |
                  Character.on_tool_start()    App._spawn_agent()    Character.on_turn_end()
                        |                      |                      |
                  walk to desk           new Character()        return to lounge
                  show bubble            SPAWNING state
```

## Character State Machine

```
SPAWNING -----> IDLE <-----> WANDERING
  |               |               ^
  | pending       | tool          | arrive
  | tool          | start         | at lounge
  v               v               |
WALKING ------> WORKING ------> THINKING (coffee break)
  arrive          |    tool_end     walk to coffee -> sip -> return
  at desk         |
                  v
               WAITING (needs permission)
                  | 15s timeout or next tool
                  v
               WANDERING (return to lounge)

EXITING (subagent done) --> removed from scene
```

### States

| State | Sprite | Behavior |
|-------|--------|----------|
| SPAWNING | `. : .` | Materializing, 1s duration. Queues incoming tools. |
| IDLE | ` o /|\\ / \\` | Standing in lounge. Wander timer (2-6s) triggers WANDERING. |
| WANDERING | walk animation | Walking to random point in lounge area. |
| WALKING | walk animation | Moving to assigned desk. Triggered by tool_start. |
| SITTING | ` o /|\\ _\|_` | Brief 0.5s pause at desk before WORKING. |
| WORKING | typing animation | At desk, using a tool. Speech bubble shows tool name. 10s timeout returns to lounge. |
| THINKING | coffee animation | Walks to coffee machine, sips (3-6s), then returns to lounge. |
| WAITING | `\\o/ \| / \\` | Arms raised, flashing red. Persistent bubble "HELP! {tool}?". 15s auto-timeout. |
| EXITING | `* * *` | Fading out, 1.5s. Character removed after. |

### Transitions triggered by events

| Event | Method | Effect |
|-------|--------|--------|
| `tool_start` | `Character.on_tool_start(name)` | Walk to desk, show tool bubble. If SPAWNING, queues tool. |
| `tool_end` | `Character.on_tool_end()` | Go get coffee (THINKING). |
| `turn_end` | `Character.on_turn_end()` | Return to lounge immediately. |
| `AskUserQuestion` | `Character.on_waiting(name)` | Enter WAITING state with red flashing "HELP!" bubble. |
| `spawn_subagent` | `App._spawn_agent()` | New character in SPAWNING state. |
| subagent `turn_end` | `Character.on_exit()` | Enter EXITING state, removed after 1.5s. |

## Transcript Watcher

`office/transcript_watcher.py` bridges Claude Code's JSONL files to visualization events.

### Session file location

Claude Code stores transcripts at:
```
~/.claude/projects/-{path-with-slashes-replaced-by-hyphens}/{session-uuid}.jsonl
```

Subagent files:
```
~/.claude/projects/-{path}/​{session-uuid}/subagents/agent-{hash}.jsonl
```

### Path resolution

The watcher resolves the working directory to a project folder using three strategies:
1. **Exact match** -- `/foo/bar` becomes `-foo-bar`
2. **Fuzzy match** -- normalizes underscores to hyphens, case-insensitive comparison
3. **Most recent** -- falls back to the project dir with the most recently modified `.jsonl`

### JSONL record parsing

| Record type | Detected field | Emitted event |
|------------|---------------|---------------|
| `"assistant"` with `tool_use` content | `block.name` | `tool_start` with tool name |
| `"assistant"` with `tool_use` name=`"Task"` | `block.input.subagent_type` | `spawn_subagent` |
| `"result"` | -- | `tool_end` |
| `"system"` subtype `"turn_duration"` | -- | `turn_end` |

### Polling

- Seeks to last-read byte position each poll (no inotify)
- Scans for new subagent files every 2 seconds
- On first encounter of a file, skips to end (no history replay)

## Scene Layout

Defined in `office/scene.py`. The office is 78x22 characters inside an 80x24 border.

### Zones

| Zone | Y range | Contents |
|------|---------|----------|
| Title bar | 0-2 | "CLAUDE CODE OFFICE" + clock |
| Desk area | 3-7 | 4 workstations with chairs |
| Walkway | 10 | Dashed separator line |
| Lounge | 12-19 | Coffee machine, sofas, plant, whiteboard |
| Status bar | 22 | Agent count, active count, tools |

### Key coordinates

| Object | Position |
|--------|----------|
| Desk 0 chair | (12, 6) |
| Desk 1 chair | (29, 6) |
| Desk 2 chair | (46, 6) |
| Desk 3 chair | (63, 6) |
| Coffee spot | (9, 13) |
| Lounge walk area | x: 10-50, y: 12-15 |
| Whiteboard | right edge, y: 12-18 |

## Sprites

All sprites are 3 lines tall, 3 characters wide. Defined in `office/character.py` `SPRITES` dict.

```
idle:     walk_1:   walk_2:   typing_1: typing_2: sitting:
 o         o         o         o         o         o
/|\       /|\       /|\       \|/        |\       /|\
/ \       / |       | \       _|_       _|_       _|_

waiting_1: waiting_2: coffee_1: coffee_2: spawning: exiting:
\o/        o          o         o>        .         *
 |        /|\        /|>       /|          :         *
/ \       / \        / \       / \         .         *
```

## Color Scheme

16-color ANSI pairs defined in `office/colors.py`:

| Pair | Foreground | Background | Usage |
|------|-----------|------------|-------|
| COLOR_MAIN_AGENT (3) | white | default | Main agent character |
| COLOR_SUB_CYAN (4) | cyan | default | Explore / Bash subagents |
| COLOR_SUB_GREEN (5) | green | default | general-purpose / code subagents |
| COLOR_SUB_YELLOW (6) | yellow | default | Plan / test subagents |
| COLOR_SPEECH (7) | white | blue | Normal speech bubbles |
| COLOR_WAITING (17) | red | default | Waiting character blink |
| COLOR_WAITING_BUBBLE (18) | white | red | "HELP!" bubble |
| COLOR_STATUS_BAR (8) | black | white | Bottom status bar |

## Timing Constants

| Constant | Value | Location |
|----------|-------|----------|
| FPS | 10 | `app.py:11` |
| WALK_SPEED | 16 cols/sec | `character.py:87` |
| Spawn duration | 1.0s | `app.py:153` |
| Exit duration | 1.5s | `character.py:198` |
| Sit pause | 0.5s | `character.py:255` |
| Think (coffee) | 3.0-6.0s | `character.py:179` |
| Wander pause | 2.0-6.0s | `character.py:238` |
| Desk timeout | 10.0s | `character.py:266` |
| Wait timeout | 15.0s | `character.py:290` |
| Whiteboard expiry | 15.0s | `scene.py:31` |
| File scan interval | 2.0s | `transcript_watcher.py:14` |
| Speech bubble | 50 frames (5s) | `speech_bubble.py:75` |

## Demo Mode

`demo/demo_mode.py` generates random events at 0.8-3.0s intervals without needing an active Claude Code session. It simulates tool usage, subagent spawning, and turn completions. Max 3 concurrent subagents.

## Adding New Features

### New tool type
1. Add display name to `TOOL_ICONS` in `speech_bubble.py`
2. If it needs special handling (like `AskUserQuestion`), add logic in `App._handle_event()`

### New agent type / color
1. Add color pair in `colors.py` (increment the ID)
2. Register it in `init_colors()`
3. Add mapping in `AGENT_COLORS` dict in `character.py`

### New sprite / animation
1. Add sprite frames to `SPRITES` dict in `character.py` (3 lines, ~3 chars wide)
2. Add state to `AgentState` enum in `agent_state.py`
3. Add tick logic in `Character.tick()`
4. Add sprite selection in `Character.get_current_sprite()`

### New furniture
1. Add draw calls in `Scene.draw_furniture()` in `scene.py`
2. Adjust `LOUNGE_AREA` bounds if needed to avoid overlap with walkable area

## Running

```bash
python3 claude_office.py              # Auto-detect active session
python3 claude_office.py --demo       # Simulated agents
python3 claude_office.py --project .  # Specific project directory
```

Press `q` to quit. Requires Python 3 with built-in `curses` (no pip dependencies).
