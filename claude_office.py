#!/usr/bin/env python3
"""Claude Office -- Terminal ASCII agent visualizer for Claude Code."""
import argparse
import curses
import sys


def main():
    parser = argparse.ArgumentParser(
        description="Watch Claude Code agents in a terminal office"
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
    args = parser.parse_args()

    try:
        curses.wrapper(lambda stdscr: run(stdscr, args))
    except KeyboardInterrupt:
        pass


def run(stdscr, args):
    from office.app import App
    app = App(
        stdscr,
        project_path=args.project,
        demo=args.demo,
        session_id=args.session,
    )
    app.run()


if __name__ == "__main__":
    main()
