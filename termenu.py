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
    An interactive vertical menu to be used in console scripts.

    Example:
        menu = Menu("Select: ", ["item one", "item two", "item three"])
        result = menu.show()
        print result
    """
    MAX_COLUMNS = 5
    def __init__(self, title, options, default=None, height=None, columns=None):
        self.title = title
        self.options = options
        self.width = max(len(option) for option in self.options)
        self.columns = self._compute_columns(columns)
        self.selected = self._compute_default(default)
        self.height = self._compute_height(height)
        self.first = self.selected - self.selected % self.height
        self.result = None
        
    def _compute_height(self, height):
        maxHeight = get_terminal_size()[1]-2 
        if height is None:
            height = maxHeight
        return min(len(self.options), height, maxHeight)

    def _compute_columns(self, columns):
        if columns is None:
            columns = self.MAX_COLUMNS
        return min(columns, get_terminal_size()[0] / (self.width + 1))

    def _compute_default(self, default):
        if default is None:
            default = 0
        else:
            try:
                default = self.options.index(default)
            except ValueError:
                default = 0
        return max(0, default % len(self.options))

    def _print(self, data):
        sys.stdout.write(data)
        sys.stdout.flush()

    def _print_menu(self):
        page = self.options[self.first:self.first+self.height*self.columns]
        for row in xrange(self.height):
            lineItemIndexes = range(row, row+len(page), self.height)
            items = []
            for index in lineItemIndexes:
                if index < len(page):
                    items.append(self._build_menu_item(self.first + index, page[index]))
            self._print(" ".join(items))
            ansi.clear_eol()
            self._print("\n")

    def _build_menu_item(self, index, option):
        item = option + " " * (self.width - len(option))
        item = self._colorize_item(index, item, )
        item = self._build_left_marker(index) + item + self._build_right_marker(index)
        return item

    def _build_left_marker(self, index):
        if index > 0 and index == self._top_left():
            marker = ansi.colorize("^", "white", bright=True)
        elif self._top_left() <= index <= self._bottom_left():
            marker = " "
        else:
            marker = ""
        return marker

    def _build_right_marker(self, index):
        if index < len(self.options) - 1 and index == self._bottom_right():
            marker = ansi.colorize("v", "white", bright=True)
        elif self._top_right() <= index <= self._bottom_right():
            marker = " "
        else:
            marker = ""
        return marker

    def _colorize_item(self, index, item):
        if index == self.selected:
            item = ansi.colorize(item, "black", "white")
        return item

    def _items_in_page(self):
        return min(self.height * self.columns, len(self.options))

    def _top_right(self):
        return self.first + self.height * (self.columns - 1)

    def _bottom_right(self):
        return self.first + self.height * self.columns - 1

    def _top_left(self):
        return self.first

    def _bottom_left(self):
        return self.first + self.height - 1

    def _on_down(self):
        if self.selected == self.first + self._items_in_page() - 1:
            self.first += 1
        self.selected += 1
        self._adjust_selected()

    def _on_up(self):
        if self.selected == self.first:
            self.first -= 1
        self.selected -= 1
        self._adjust_selected()

    def _on_right(self):
        if self.selected >= self._top_right():
            if self.selected < self._bottom_right():
                self.selected = self._bottom_right()
            elif self.selected == self._bottom_right():
                self.first += self.height
                self.selected += self.height
        else:
            self.selected += self.height
        self._adjust_selected()

    def _on_left(self):
        if self.selected <= self._bottom_left():
            if self.selected > self._top_left():
                self.selected = self._top_left()
            elif self.selected == self._top_left():
                self.first -= self.height
                self.selected -= self.height
        else:
            self.selected -= self.height
        self._adjust_selected()

    def _on_pageDown(self):
        if self.selected == self.first + self._items_in_page() - 1:
            self.selected += self._items_in_page()
            self.first += self._items_in_page()
        else:
            self.selected = self.first + self._items_in_page() - 1
        self._adjust_selected()

    def _on_pageUp(self):
        if self.selected == self.first:
            self.selected -= self._items_in_page()
            self.first -= self._items_in_page()
        else:
            self.selected = self.first
        self._adjust_selected()

    def _on_home(self):
        self.selected = 0
        self.first = 0
        self._adjust_selected()

    def _on_end(self):
        self.selected = len(self.options)-1
        self.first = self.selected - self._items_in_page() + 1
        self._adjust_selected()

    def _on_enter(self):
        self.result = self.options[self.selected]
        return True

    def _on_esc(self):
        self.result = None
        return True

    def _dispatch_key(self, key):
        handler = "_on_" + key
        if hasattr(self, handler):
            return getattr(self, handler)()

    def _adjust_selected(self):
        if self.selected < 0:
            self.selected = 0
        if self.selected > len(self.options)-1:
            self.selected = len(self.options)-1
        if self.first < 0:
            self.first = 0
        if self.first > (len(self.options) - self._items_in_page()):
            self.first = len(self.options) - self._items_in_page()

    def _clear_menu(self):
        ansi.restore_position()
        lines = self.height
        if self.title:
            lines += 1
        ansi.up(lines)
        for i in xrange(lines):
            ansi.clear_line()
            ansi.down()
        ansi.clear_line()
        ansi.up(lines)

    def show(self):
        """
        Show the menu and run the keyboard loop. The return value is the text of the chosen option
        if Enter was pressed and None is Esc was pressed.
        """
        import keyboard
        if self.title:
            self._print(ansi.colorize(self.title, "white", bright=True) + "\n")
        self._print_menu()
        ansi.save_position() # save bottom-of-menu position for future reference
        ansi.hide_cursor()
        try:
            for key in keyboard.keyboard_listener():
                ret = self._dispatch_key(key)
                if ret:
                    return self.result
                ansi.restore_position() # go to bottom of menu
                ansi.up(self.height) # go to top of menu
                self._print_menu()
        finally:
            self._clear_menu()
            ansi.show_cursor()

class SearchMixin(object):
    def __init__(self, *args, **kwargs):
        super(SearchMixin, self).__init__(*args, **kwargs)
        self.searchMode = False
        self.searchText = ""
        self._allOptions = self.options
        self._fullHeight = self.height
        self._refilter()

    def _print_menu(self):
        if self.options:
            super(SearchMixin, self)._print_menu()
        else:
            for i in xrange(self.height):
                ansi.clear_line()
                ansi.down()
        ansi.clear_line()
        if self.searchMode:
            self._print("/" + self.searchText)

    def _start_search(self):
        if not self.searchMode:
            self.searchText = ""
            self.searchMode = True
            ansi.show_cursor()

    def _stop_search(self):
        if self.searchMode:
            self.searchMode = False
            ansi.hide_cursor()
            self._refilter()

    def _refilter(self):
        if self.searchMode:
            filtered = [(i, o) for i, o in enumerate(self._allOptions) if self.searchText.lower() in o.lower()]
            self.options = [o for i,o in filtered]
            self._indexes = [i for i,o in filtered]
        else:
            self.options = self._allOptions
            self._indexes = xrange(len(self._allOptions))
        self.selected = 0
        self.first = 0

    def _on_backspace(self):
        if self.searchMode and self.searchText:
            self.searchText = self.searchText[:-1]
            self._refilter()

    def _on_esc(self):
        if self.searchMode:
            self._stop_search()
            return False
        else:
            return super(SearchMixin, self)._on_esc()

    def _dispatch_key(self, key):
        if len(key) == 1 and 32 < ord(key) < 127:
            self._start_search()
            self.searchText += key
            self._refilter()
        else:
            return super(SearchMixin, self)._dispatch_key(key)

class MultiSelectMixin(object):
    def __init__(self, *args, **kwargs):
        super(MultiSelectMixin, self).__init__(*args, **kwargs)
        self.selectedItems = set()

    def _build_marker(self, index):
        marker = super(MultiSelectMixin, self)._build_marker(index)
        marker += "*" if self._is_multi_selected(index) else " "
        return marker

    def _colorize_item(self, index, item):
        multiSelected = self._is_multi_selected(index)
        if index == self.selected:
            if multiSelected:
                item = ansi.colorize(item, "red", "white")
            else:
                item = ansi.colorize(item, "black", "white")
        elif multiSelected:
                item = ansi.colorize(item, "red")
        return item

    def _is_multi_selected(self, index):
        return index < len(self.options) and self.options[index] in self.selectedItems

    def _on_enter(self):
        if not self.selectedItems:
            self.selectedItems.add(self.options[self.selected])
        self.result = list(sorted(self.selectedItems))
        return True

    def _on_esc(self):
        self.result = []
        return super(MultiSelectMixin, self)._on_esc()

    def _on_space(self):
        option = self.options[self.selected]
        if option in self.selectedItems:
            self.selectedItems.remove(option)
        else:
            self.selectedItems.add(option)
        self._on_down()


def show_menu(title, options, default=None, height=None, multiSelect=False):
    if multiSelect:
        class MenuClass(MultiSelectMixin, SearchMixin, Menu):
            pass
    else:
        class MenuClass(SearchMixin, Menu):
            pass
    menu = MenuClass(title, options, default, height)
    return menu.show()
