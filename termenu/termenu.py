#!/usr/bin/python
import sys
import ansi

# Get the size of the current terminal
# (http://stackoverflow.com/questions/566746/how-to-get-console-window-width-in-python)
def get_terminal_size():
    import fcntl, termios, struct
    h, w, hp, wp = struct.unpack('HHHH', fcntl.ioctl(sys.stdin,
        termios.TIOCGWINSZ, struct.pack('HHHH', 0, 0, 0, 0)))
    return w, h

class Menu(object):
    """
    An interactive one line menu to be used in console scripts.

    Example:
        menu = Menu("Select: ", ["item one", "item two", "item three"])
        result = menu.show()
        print result
    """

    MARGIN = 5
    def __init__(self, title, options, default=None, clearOnExit=True, separator="  "):
        self.title = title
        self.options = list(options)
        if default is None:
            default = 0
        elif isinstance(default, str):
            try:
                default = options.index(default)
            except ValueError:
                default = 0
        self.clearOnExit = clearOnExit
        self.separator = separator
        self.selected = max(0, default % len(self.options))
        self.slices = lambda: self._paginate(options, get_terminal_size()[0])

    def _print(self, data):
        sys.stdout.write(data)
        sys.stdout.flush()

    def _print_menu(self):
        [(first, last)] = [(start, end) for start, end in self.slices() if start <= self.selected < end]
        optionsCopy = list(self.options)
        optionsCopy[self.selected] = ansi.colorize(optionsCopy[self.selected], "black", "white")
        optionsStr = self.separator.join(optionsCopy[first:last])
        if first > 0:
            optionsStr = ansi.colorize("< ", "white", bright=True) + optionsStr
        if last < len(self.options):
            optionsStr = optionsStr + ansi.colorize(" >", "white", bright=True)
        ansi.clear_line()
        self._print("\r")
        self._print(ansi.colorize(self.title, "white", bright=True) + optionsStr)

    def _paginate(self, options, maxWidth):
        slices = []
        start = 0
        contents = []
        for i, option in enumerate(options):
            contents.append(option)
            if len(self.title) + len(self.separator.join(contents)) + self.MARGIN > maxWidth:
                slices.append((start, i))
                start = i
                contents = [option]
        slices.append((start, len(options)))
        return slices

    def show(self):
        """
        Show the menu and run the keyboard loop. The return value is the text of the chosen option
        if Enter was pressed and None is Esc was pressed.
        """
        import keyboard
        ansi.hide_cursor()
        try:
            self._print_menu()
            for key in keyboard.keyboard_listener():
                if key == "right":
                    if self.selected < len(self.options)-1:
                        self.selected += 1
                elif key == "left":
                    if self.selected > 0:
                        self.selected -= 1
                elif key == "enter":
                    return self.options[self.selected]
                elif key == "esc":
                    return None
                self._print_menu()
        finally:
            if self.clearOnExit:
                ansi.clear_line()
                self._print("\r")
            else:
                self._print("\n")
            ansi.show_cursor()

class VerticalMenu(object):
    """
    An interactive vertical menu to be used in console scripts.

    Example:
        menu = VerticalMenu("Select: ", ["item one", "item two", "item three"])
        result = menu.show()
        print result
    """
    def __init__(self, title, options, default=None, clearOnExit=True, height=None, multiSelect=False):
        self.title = title
        self.options = options
        if default is None:
            default = 0
        elif isinstance(default, str):
            try:
                default = options.index(default)
            except ValueError:
                default = 0
        self.selected = max(0, default % len(self.options))
        self.width = max(len(option) for option in self.options)
        self.clearOnExit = clearOnExit
        maxHeight = get_terminal_size()[1]-2
        if not height or height > maxHeight:
            height = maxHeight
        self.height = min(len(options), height)
        self.first = self.selected - self.selected % self.height
        self.multiSelect = multiSelect
        if multiSelect:
            self.selectedItems = set()

    def _print(self, data):
        sys.stdout.write(data)
        sys.stdout.flush()

    def _print_menu(self, redraw=False):
        if redraw:
            ansi.restore_position() # go to bottom of menu
            ansi.up(self.height) # go to top of menu
        options = self.options[self.first:self.first+self.height]
        options += [""] * (self.height - len(options))
        for i, option in enumerate(options):
            if i == 0 and self.first != 0:
                marker = ansi.colorize("^", "white", bright=True)
            elif i == self.height-1 and self.first + self.height < len(self.options):
                marker = ansi.colorize("v", "white", bright=True)
            else:
                marker = " "
            multiSelected = self.multiSelect and (self.first + i) in self.selectedItems
            marker += "*" if multiSelected else " "
            line = option + " " * (self.width - len(option))
            if self.first + i == self.selected:
                if multiSelected:
                    line = ansi.colorize(line, "black", "cyan")
                else:
                    line = ansi.colorize(line, "black", "white")
            elif multiSelected:
                    line = ansi.colorize(line, "black", "blue")
            line = marker + line + "\n"
            self._print(line)

    def show(self):
        """
        Show the menu and run the keyboard loop. The return value is the text of the chosen option
        if Enter was pressed and None is Esc was pressed.
        """
        import keyboard
        if self.title:
            self._print(ansi.colorize(self.title, "white", bright=True) + "\n")
        self._print_menu(False)
        ansi.save_position() # save bottom-of-menu position for future reference
        ansi.hide_cursor()
        try:
            for key in keyboard.keyboard_listener():
                if key == "down":
                    self.selected += 1
                elif key == "up":
                    self.selected -= 1
                elif key == "pageDown":
                    if self.selected % self.height < self.height-1:
                        self.selected = self.selected - self.selected % self.height + self.height - 1
                    else:
                        self.selected += self.height
                elif key == "pageUp":
                    if self.selected % self.height > 0:
                        self.selected = self.selected - self.selected % self.height
                    else:
                        self.selected -= self.height
                elif key == "home":
                    self.selected = 0
                elif key == "end":
                    self.selected = len(self.options)-1
                elif key == "enter":
                    if self.multiSelect:
                        if not self.selectedItems:
                            self.selectedItems.add(self.selected)
                        return [self.options[i] for i in sorted(self.selectedItems)]
                    else:
                        return self.options[self.selected]
                elif key == "esc":
                    return None
                elif key == " ":
                    if self.multiSelect:
                        if self.selected in self.selectedItems:
                            self.selectedItems.remove(self.selected)
                        else:
                            self.selectedItems.add(self.selected)
                if self.selected < 0:
                    self.selected = 0
                if self.selected > len(self.options)-1:
                    self.selected = len(self.options)-1
                self.first = self.selected - self.selected % self.height
                self._print_menu(True)
        finally:
            if self.clearOnExit:
                ansi.restore_position()
                lines = self.height
                if self.title:
                    lines += 1
                ansi.up(lines)
                for i in xrange(lines):
                    ansi.clear_line()
                    ansi.down()
                ansi.up(lines)
            ansi.show_cursor()

def show_menu(title, options, default=None, clearOnExit=True):
    menu = Menu(title, options, default, clearOnExit)
    return menu.show()

def show_vertical_menu(title, options, default=None, clearOnExit=True, height=None, multiSelect=False):
    menu = VerticalMenu(title, options, default, clearOnExit, height, multiSelect)
    return menu.show()
