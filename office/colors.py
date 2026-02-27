import curses

COLOR_WALL = 1
COLOR_DESK = 2
COLOR_MAIN_AGENT = 3
COLOR_SUB_CYAN = 4
COLOR_SUB_GREEN = 5
COLOR_SUB_YELLOW = 6
COLOR_SPEECH = 7
COLOR_STATUS_BAR = 8
COLOR_FLOOR = 9
COLOR_TITLE = 10
COLOR_WHITEBOARD = 11
COLOR_COFFEE = 12
COLOR_FURNITURE = 13
COLOR_SEPARATOR = 14
COLOR_PLANT = 15
COLOR_AGENT_NAME = 16
COLOR_WAITING = 17
COLOR_WAITING_BUBBLE = 18
COLOR_ENTRANCE = 19
COLOR_HEADER = 20
COLOR_DESK_LABEL = 21
COLOR_SUB_MAGENTA = 22


def init_colors():
    curses.use_default_colors()
    curses.init_pair(COLOR_WALL, curses.COLOR_BLUE, -1)
    curses.init_pair(COLOR_DESK, curses.COLOR_YELLOW, -1)
    curses.init_pair(COLOR_MAIN_AGENT, curses.COLOR_WHITE, -1)
    curses.init_pair(COLOR_SUB_CYAN, curses.COLOR_CYAN, -1)
    curses.init_pair(COLOR_SUB_GREEN, curses.COLOR_GREEN, -1)
    curses.init_pair(COLOR_SUB_YELLOW, curses.COLOR_YELLOW, -1)
    curses.init_pair(COLOR_SPEECH, curses.COLOR_WHITE, curses.COLOR_BLUE)
    curses.init_pair(COLOR_STATUS_BAR, curses.COLOR_BLACK, curses.COLOR_CYAN)
    curses.init_pair(COLOR_FLOOR, curses.COLOR_WHITE, -1)
    curses.init_pair(COLOR_TITLE, curses.COLOR_CYAN, -1)
    curses.init_pair(COLOR_WHITEBOARD, curses.COLOR_WHITE, -1)
    curses.init_pair(COLOR_COFFEE, curses.COLOR_RED, -1)
    curses.init_pair(COLOR_FURNITURE, curses.COLOR_MAGENTA, -1)
    curses.init_pair(COLOR_SEPARATOR, curses.COLOR_BLUE, -1)
    curses.init_pair(COLOR_PLANT, curses.COLOR_GREEN, -1)
    curses.init_pair(COLOR_AGENT_NAME, curses.COLOR_CYAN, -1)
    curses.init_pair(COLOR_WAITING, curses.COLOR_RED, -1)
    curses.init_pair(COLOR_WAITING_BUBBLE, curses.COLOR_WHITE, curses.COLOR_RED)
    curses.init_pair(COLOR_ENTRANCE, curses.COLOR_YELLOW, -1)
    curses.init_pair(COLOR_HEADER, curses.COLOR_WHITE, curses.COLOR_BLUE)
    curses.init_pair(COLOR_DESK_LABEL, curses.COLOR_WHITE, -1)
    curses.init_pair(COLOR_SUB_MAGENTA, curses.COLOR_MAGENTA, -1)
