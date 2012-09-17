import sys
import ansi

try:
    xrange()
except:
    xrange = range

def pluggable(method):
    """
    Mark a class method as extendable with plugins.
    """
    def wrapped(self, *args, **kwargs):
        if hasattr(self, "_plugins"):
            # call the last plugin, it may call the previous via self.parent.method
            # creating a call call chain
            return getattr(self._plugins[-1], method.__name__)(*args, **kwargs)
        else:
            return method(self, *args, **kwargs)
    wrapped.original = method
    return wrapped

def register_plugin(host, plugin):
    """
    Register a plugin with a host object. Some @pluggable methods in the host
    will have their behaviour altered by the plugin.
    """
    class OriginalMethods(object):
        def __getattr__(self, name):
            return lambda *args, **kwargs: getattr(host, name).original(host, *args, **kwargs)
    if not hasattr(host, "_plugins"):
        host._plugins = [OriginalMethods()]
    plugin.parent = host._plugins[-1]
    plugin.host = host
    host._plugins.append(plugin)

class Plugin(object):
    def __getattr__(self, name):
        # allow calls to fall through to parent plugins if a method isn't defined
        return getattr(self.parent, name)

class Termenu(object):
    class _Option(object):
        def __init__(self, text, result, **attrs):
            self.text = text
            self.result = result
            self.selected = False
            self.attrs = attrs

    def __init__(self, options, results=None, default=None, height=None, width=None, multiselect=True, plugins=None):
        for plugin in plugins or []:
            register_plugin(self, plugin)
        self.options = self._make_option_objects(options, results)
        self.height = min(height or 10, len(self.options))
        self.width = self._compute_width(width, self.options)
        self.multiselect = multiselect
        self.cursor = 0
        self.scroll = 0
        self._aborted = False
        self._set_default(default)

    def get_result(self):
        if self._aborted:
            return None
        else:
            selected = [o.result for o in self.options if o.selected]
            if not selected:
                selected.append(self._get_active_option().result)
            return selected

    def show(self):
        import keyboard
        self._print_menu()
        ansi.save_position()
        ansi.hide_cursor()
        try:
            for key in keyboard.keyboard_listener():
                stop = self._on_key(key)
                if stop:
                    return self.get_result()
                self._goto_top()
                self._print_menu()
        finally:
            self._clear_menu()
            ansi.show_cursor()

    @pluggable
    def _goto_top(self):
        ansi.restore_position()
        ansi.up(self.height)

    @pluggable
    def _make_option_objects(self, options, results):
        return [self._Option(o, r) for o, r in zip(options, results or options)]

    @pluggable
    def _set_default(self, default):
        # handle default selection of multiple options
        if isinstance(default, list) and default:
            if not self.multiselect:
                raise ValueError("multiple defaults passed, but multiselect is False")
            for option in self.options:
                if option.text in default:
                    option.selected = True
            default = default[0]

        # handle default active option
        index = self._get_index(default)
        if index is not None:
            if index < self.height:
                self.cursor = index % self.height
                self.scroll = 0
            elif index + self.height < len(self.options) - 1:
                self.cursor = 0
                self.scroll = index
            else:
                self.cursor = index % self.height + 1
                self.scroll = len(self.options) - self.height

    def _compute_width(self, width, options):
        termwidth = get_terminal_size()[0]
        decorations = len(self._decorate(""))
        if width:
            maxwidth = min(width, termwidth)
        else:
            maxwidth = termwidth
        maxwidth -= decorations
        maxoption = max(len(o.text) for o in options)
        return min(maxoption, maxwidth)

    def _get_index(self, s):
        matches = [i for i, o in enumerate(self.options) if o.text == s]
        if matches:
            return matches[0]
        else:
            return None

    def _get_active_option(self):
        return self.options[self.scroll+self.cursor] if self.options else None

    def _get_window(self):
        return self.options[self.scroll:self.scroll+self.height]

    def _get_debug_view(self):
        options = []
        for i, option in enumerate(self._get_window()):
            options.append(("(%s)" if i == self.cursor else "%s") % option.text)
        return " ".join(options)

    @pluggable
    def _on_key(self, key):
        func = "_on_" + key
        if hasattr(self, func):
            return getattr(self, func)()

    def _on_down(self):
        height = min(self.height, len(self.options))
        if self.cursor < height - 1:
            self.cursor += 1
        elif self.scroll + height < len(self.options):
            self.scroll += 1

    def _on_up(self):
        if self.cursor > 0:
            self.cursor -= 1
        elif self.scroll > 0:
            self.scroll -= 1

    def _on_pageDown(self):
        height = min(self.height, len(self.options))
        if self.cursor < height - 1:
            self.cursor = height - 1
        elif self.scroll + height * 2 < len(self.options):
            self.scroll += height
        else:
            self.scroll = len(self.options) - height

    def _on_pageUp(self):
        height = min(self.height, len(self.options))
        if self.cursor > 0:
            self.cursor = 0
        elif self.scroll - height >= 0:
            self.scroll -= height
        else:
            self.scroll = 0

    def _on_home(self):
        self.cursor = 0
        self.scroll = 0

    def _on_end(self):
        self.scroll = len(self.options) - self.height
        self.cursor = self.height - 1

    @pluggable
    def _on_space(self):
        if not self.multiselect:
            return
        option = self._get_active_option()
        option.selected = not option.selected
        self._on_down()

    def _on_esc(self):
        self._aborted = True
        return True # stop loop

    @pluggable
    def _on_enter(self):
        return True # stop loop

    @pluggable
    def _clear_menu(self):
        ansi.restore_position()
        for i in xrange(self.height):
            ansi.clear_eol()
            ansi.up()
        ansi.clear_eol()

    @pluggable
    def _print_menu(self):
        ansi.write("\r")
        for index, option in enumerate(self._get_window()):
            option = option.text
            option = self._adjust_width(option)
            ansi.write(self._decorate(option, **self._decorate_flags(index)) + "\n")
            ansi.clear_eol()

    @pluggable
    def _adjust_width(self, option):
        if len(option) > self.width:
            option = shorten(option, self.width)
        if len(option) < self.width:
            option = option + " " * (self.width - len(option))
        return option

    @pluggable
    def _decorate_flags(self, index):
        return dict(
            active = (self.cursor == index),
            selected = (self.options[self.scroll+index].selected),
            moreAbove = (self.scroll > 0 and index == 0),
            moreBelow = (self.scroll + self.height < len(self.options) and index == self.height - 1),
        )

    @pluggable
    def _decorate(self, option, **flags):
        active = flags.get("active", False)
        selected = flags.get("selected", False)

        # add selection / cursor decorations
        if active and selected:
            option = "*" + ansi.colorize(option, "red", "white")
        elif active:
            option = " " + ansi.colorize(option, "black", "white")
        elif selected:
            option = "*" + ansi.colorize(option, "red")
        else:
            option = " " + option

        return self._decorate_indicators(option, **flags)

    @pluggable
    def _decorate_indicators(self, option, **flags):
        moreAbove = flags.get("moreAbove", False)
        moreBelow = flags.get("moreBelow", False)

        # add more above/below indicators
        if moreAbove:
            option = option + " " + ansi.colorize("^", "white", bright=True)
        elif moreBelow:
            option = option + " " + ansi.colorize("v", "white", bright=True)
        else:
            option = option + "  "

        return option

class FilterPlugin(Plugin):
    def __init__(self):
        self.text = None

    def _make_option_objects(self, options, results):
        objects = self.parent._make_option_objects(options, results)
        self._allOptions = objects[:]
        return objects

    def _on_key(self, key):
        prevent = False
        if len(key) == 1 and 32 < ord(key) <= 127:
            if not self.text:
                self.text = []
            self.text.append(key)
            self._refilter()
        elif self.text and key == "backspace":
            del self.text[-1]
            self._refilter()
        elif self.text is not None and key == "esc":
            self.text = None
            ansi.hide_cursor()
            prevent = True
            self._refilter()

        if not prevent:
            return self.parent._on_key(key)

    def _print_menu(self):
        self.parent._print_menu()

        for i in xrange(0, self.host.height - len(self.host.options)):
            ansi.clear_eol()
            ansi.write("\n")
        if self.text is not None:
            ansi.write("/" + "".join(self.text))
            ansi.show_cursor()
        ansi.clear_eol()

    def _refilter(self):
        self.host.options = []
        text = "".join(self.text or []).lower()
        # filter the matching options
        for option in self._allOptions:
            if text in option.text.lower() or option.attrs.get("showAlways"):
                self.host.options.append(option)
        # select the first matching element (showAlways elements might not match)
        self.host.scroll = 0
        for i, option in enumerate(self.host.options):
            if text in option.text:
                self.host.cursor = i
                break

class Header(str):
    pass

class HeaderPlugin(Plugin):
    def _set_default(self, default):
        if default:
            return self.parent._set_default()
        else:
            self.host.scroll = 0
            for i, option in enumerate(self.host.options):
                if not option.attrs.get("header"):
                    self.host.cursor = i
                    break

    def _make_option_objects(self, options, results):
        options = self.parent._make_option_objects(options, results)
        for option in options:
            if isinstance(option.text, Header):
                option.attrs["header"] = True
                option.attrs["showAlways"] = True
                option.result = None
        return options

    def _on_enter(self):
        # can't select a header
        if self.host._get_active_option().attrs.get("header") and self.host.get_result() == [None]:
            return False
        else:
            return self.parent._on_enter()

    def _on_space(self):
        if self.host._get_active_option().attrs.get("header"):
            self.host._on_down()
        else:
            self.parent._on_space()

    def _decorate_flags(self, index):
        flags = self.parent._decorate_flags(index)
        flags["header"] = self.host.options[self.host.scroll+index].attrs.get("header")
        return flags

    def _decorate(self, option, **flags):
        active = flags.get("active", False)
        header = flags.get("header", False)
        if header:
            option = "{0:<{width}}".format(option, width=self.host.width)
            if active:
                option = " " + ansi.colorize(option, "black", "white", bright=True)
            else:
                option = " " + ansi.colorize(option, "white", bright=True)
            return option
        else:
            return self.parent._decorate(option, **flags)

class Precolored(Plugin):
    def _make_option_objects(self, options, results):
        options = self.parent._make_option_objects(options, results)
        for option in options:
            option.result = ansi.decolorize(option.text)
            option.text = ansi.ansistr(option.text)
        return options

    def _decorate(self, option, **flags):
        active = flags.get("active", False)
        selected = flags.get("selected", False)
        moreAbove = flags.get("moreAbove", False)
        moreBelow = flags.get("moreBelow", False)

        # add selection / cursor decorations
        option = ("=> " if selected else "   ") + option
        if active:
            option = ansi.highlight(option, "black")

        # add more above/below indicators
        if moreAbove:
            option = option + " " + ansi.colorize("^", "white", bright=True)
        elif moreBelow:
            option = option + " " + ansi.colorize("v", "white", bright=True)
        else:
            option = option + "  "

        return option

class TitlePlugin(Plugin):
    def __init__(self, title):
        self.title = title
        
    def _goto_top(self):
        self.parent._goto_top()
        ansi.up(1)

    def _print_menu(self):
        ansi.write(ansi.colorize(self.title + "\n", "white", bright=True))
        return self.parent._print_menu()

    def _clear_menu(self):
        self.parent._clear_menu()
        ansi.up()
        ansi.clear_eol()

class Minimenu(object):
    def __init__(self, options, default=None):
        self.options = options
        try:
            self.cursor = options.index(default)
        except ValueError:
            self.cursor = 0

    def show(self):
        import keyboard
        ansi.hide_cursor()
        self._print_menu(rewind=False)
        try:
            for key in keyboard.keyboard_listener():
                if key == "enter":
                    self._clear_menu()
                    ansi.write(self.options[self.cursor])
                    return self.options[self.cursor]
                elif key == "esc":
                    self._clear_menu()
                    ansi.write("<esc>")
                    return None
                elif key == "left":
                    self.cursor = max(0, self.cursor - 1)
                elif key == "right":
                    self.cursor = min(len(self.options) - 1, self.cursor + 1)
                self._print_menu(rewind=True)
        finally:
            ansi.show_cursor()
            ansi.write("\n")

    def _make_menu(self, _decorate=True):
        menu = []
        for i, option in enumerate(self.options):
            if _decorate:
                menu.append(ansi.colorize(option, "black", "white") if i == self.cursor else option)
            else:
                menu.append(option)
        menu = " ".join(menu)
        return menu

    def _print_menu(self, rewind):
        menu = self._make_menu()
        if rewind:
            menu = "\b"*len(self._make_menu(_decorate=False)) + menu
        ansi.write(menu)

    def _clear_menu(self):
        menu = self._make_menu(_decorate=False)
        ansi.write("\b"*len(menu)+" "*len(menu)+"\b"*len(menu))

def redirect_std():
    """
    Connect stdin/stdout to controlling terminal even if the scripts input and output
    were redirected. This is useful in utilities based on termenu.
    """
    stdin = sys.stdin
    stdout = sys.stdout
    if not sys.stdin.isatty():
        sys.stdin = open("/dev/tty", "r", 0)
    if not sys.stdout.isatty():
        sys.stdout = open("/dev/tty", "w", 0)
    return stdin, stdout

def shorten(s, l=100):
    if len(s) <= l or l < 3:
        return s
    return s[:l/2-2] + "..." + s[-l/2+1:]

def get_terminal_size():
    import fcntl, termios, struct
    h, w, hp, wp = struct.unpack('HHHH', fcntl.ioctl(sys.stdin,
        termios.TIOCGWINSZ, struct.pack('HHHH', 0, 0, 0, 0)))
    return w, h

if __name__ == "__main__":
    options = ["option-%06d" % i for i in xrange(1,100)]
    options.insert(0, Header("One"))
    options.insert(3, Header("Three"))
    options.insert(17, Header("Seventeen"))
    menu = Termenu(options, plugins=[HeaderPlugin(), FilterPlugin(), TitlePlugin("List Of Numbers")])
#~     menu = Termenu(["option-%06d" % i for i in xrange(1,100)], height=10, plugins=[Precolored()])
    print(menu.show())
#~     print "Would you like to continue? ",
#~     result = Minimenu(["Abort", "Retry", "Fail"], "Fail").show()
#~     print result
