from __future__ import print_function

import sys
import re

COLORS = dict(black=0, red=1, green=2, yellow=3, blue=4, magenta=5, cyan=6, white=7, default=9)

def write(s):
    sys.stdout.write(s)
    sys.stdout.flush()

def up(n=1):
    write("\x1b[%dA" % n)

def down(n=1):
    write("\x1b[%dB" % n)

def forward(n=1):
    write("\x1b[%dC" % n)

def back(n=1):
    write("\x1b[%dD" % n)

def move_horizontal(column=1):
    write("\x1b[%dG" % column)

def move(row, column):
    write("\x1b[%d;%dH" % (row, column))

def clear_screen():
    write("\x1b[2J")

def clear_eol():
    write("\x1b[0K")

def clear_line():
    write("\x1b[2K")

def save_position():
    write("\x1b[s")

def restore_position():
    write("\x1b[u")

def hide_cursor():
    write("\x1b[?25l")

def show_cursor():
    write("\x1b[?25h")

def colorize(string, color, background=None, bright=False):
    color = 30 + COLORS.get(color, COLORS["default"])
    background = 40 + COLORS.get(background, COLORS["default"])
    return "\x1b[0;%d;%d;%dm%s\x1b[0;m" % (int(bright), color, background, string)

def highlight(string, background):
    # adds background to a string, even if it's already colorized
    background = 40 + COLORS.get(background, COLORS["default"])
    bkcmd = "\x1b[%dm" % background
    stopcmd = "\x1b[m"
    return bkcmd + string.replace(stopcmd, stopcmd + bkcmd) + stopcmd

ANSI_COLOR_REGEX = "\x1b\[(\d+)?(;\d+)*;?m"

def decolorize(string):
    return re.sub(ANSI_COLOR_REGEX, "", string)

class ansistr(str):
    def __init__(self, s):
        if not isinstance(s, str):
            s = str(s)
        self.__str = s
        self.__parts = [m.span() for m in re.finditer("(%s)|(.)" % ANSI_COLOR_REGEX, s)]
        self.__len = sum(1 if p[1]-p[0]==1 else 0 for p in self.__parts)

    def __len__(self):
        return self.__len

    def __getslice__(self, i, j):
        parts = []
        count = 0
        for start, end in self.__parts:
            if end - start == 1:
                count += 1
                if i <= count < j:
                    parts.append(self.__str[start:end])
            else:
                parts.append(self.__str[start:end])
        return ansistr("".join(parts))

    def __add__(self, s):
        return ansistr(self.__str + s)

    def decolorize(self):
        return decolorize(self.__str)

if __name__ == "__main__":
    # Print all colors
    colors = [name for name, color in sorted(COLORS.items(), key=lambda v: v[1])]
    for bright in [False, True]:
        for background in colors:
            for color in colors:
                print(colorize("Hello World!", color, background, bright))