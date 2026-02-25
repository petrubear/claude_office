#!/usr/bin/env python3
"""Claude Office -- Terminal ASCII agent visualizer for AI coding CLIs."""
import argparse
import curses
import sys


def main():
    parser = argparse.ArgumentParser(
        description="Watch AI coding agents in a terminal office"
    )
    parser.add_argument(
        "--project", "-p", type=str, default=None,
        help="Path to the project Claude Code is working on"
    )
    parser.add_argument(
        "--demo", action="store_true",
        help="Run in demo mode with simulated agent activity"
    )
    parser.add_argument(
        "--session", "-s", type=str, default=None,
        help="Specific session UUID to watch"
    )

    # Source selectors (mutually exclusive with --demo)
    source = parser.add_mutually_exclusive_group()
    source.add_argument(
        "--codex", action="store_true",
        help="Watch OpenAI Codex CLI sessions"
    )
    source.add_argument(
        "--kiro", action="store_true",
        help="Watch Kiro CLI sessions"
    )
    source.add_argument(
        "--opencode", action="store_true",
        help="Watch OpenCode sessions"
    )

    args = parser.parse_args()

    try:
        curses.wrapper(lambda stdscr: run(stdscr, args))
    except KeyboardInterrupt:
        pass


def run(stdscr, args):
    from office.app import App

    watcher = None
    if args.demo:
        from office.watchers.demo import DemoWatcher
        watcher = DemoWatcher()
    elif args.codex:
        from office.watchers.codex import CodexWatcher
        watcher = CodexWatcher()
    elif args.kiro:
        from office.watchers.kiro import KiroWatcher
        watcher = KiroWatcher()
    elif args.opencode:
        from office.watchers.opencode import OpenCodeWatcher
        watcher = OpenCodeWatcher()
    else:
        from office.watchers.claude import ClaudeWatcher
        watcher = ClaudeWatcher(args.project, args.session)

    app = App(stdscr, watcher=watcher)
    app.run()


if __name__ == "__main__":
    main()
