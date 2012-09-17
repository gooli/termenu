from __future__ import with_statement
from __future__ import print_function

import os
import sys
import fcntl
import termios
import select
import errno

STDIN = sys.stdin.fileno()

ANSI_SEQUENCES = dict(
    up = '\x1b[A',
    down = '\x1b[B',
    right = '\x1b[C',
    left = '\x1b[D',
    home = '\x1bOH',
    end = '\x1bOF',
    insert = '\x1b[2~',
    delete = '\x1b[3~',
    pageUp = '\x1b[5~',
    pageDown = '\x1b[6~',
    F1 = '\x1bOP',
    F2 = '\x1bOQ',
    F3 = '\x1bOR',
    F4 = '\x1bOS',
    F5 = '\x1b[15~',
    F6 = '\x1b[17~',
    F7 = '\x1b[18~',
    F8 = '\x1b[19~',
    F9 = '\x1b[20~',
    F10 = '\x1b[21~',
    F11 = '\x1b[23~',
    F12 = '\x1b[24~',
)

KEY_NAMES = dict((v,k) for k,v in ANSI_SEQUENCES.items())
KEY_NAMES.update({
    '\x1b' : 'esc',
    '\n' : 'enter',
    ' ' : 'space',
    '\x7f' : 'backspace',
})

class RawTerminal(object):
    def __init__(self, blocking=True):
        self._blocking = blocking

    def open(self):
        # Set raw mode
        self._oldterm = termios.tcgetattr(STDIN)
        newattr = termios.tcgetattr(STDIN)
        newattr[3] = newattr[3] & ~termios.ICANON & ~termios.ECHO
        termios.tcsetattr(STDIN, termios.TCSANOW, newattr)

        # Set non-blocking IO on stdin
        self._old = fcntl.fcntl(STDIN, fcntl.F_GETFL)
        if not self._blocking:
            fcntl.fcntl(STDIN, fcntl.F_SETFL, self._old | os.O_NONBLOCK)

    def close(self):
        # Restore previous terminal mode
        termios.tcsetattr(STDIN, termios.TCSAFLUSH, self._oldterm)
        fcntl.fcntl(STDIN, fcntl.F_SETFL, self._old)

    def get(self):
        return sys.stdin.read(5)

    def wait(self):
        select.select([STDIN], [], [])

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, *args):
        self.close()

def keyboard_listener():
    with RawTerminal(blocking=False) as terminal:
        # return keys
        sequence = ""
        while True:
            # wait for keys to become available
            select.select([STDIN], [], [])
            # read all available keys
            while True:
                try:
                    sequence = sequence + terminal.get()
                    break
                except IOError as e:
                    if e.errno == errno.EAGAIN:
                        break
            # handle ANSI key sequences
            while sequence:
                for seq in ANSI_SEQUENCES.values():
                    if sequence[:len(seq)] == seq:
                        yield KEY_NAMES[seq]
                        sequence = sequence[len(seq):]
                        break
                # handle normal keys
                else:
                    for key in sequence:
                        yield KEY_NAMES.get(key, key)
                    sequence = ""
    
if __name__ == "__main__":
    for key in keyboard_listener():
        print(key)

