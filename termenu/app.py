import time
import functools
from textwrap import wrap
from . import termenu, keyboard
from contextlib import contextmanager
from . import ansi
from .colors import Colorized
import collections


class ParamsException(Exception):
    "An exception object that accepts arbitrary params as attributes"
    def __init__(self, message="", *args, **kwargs):
        if args:
            message %= args
        self.message = message
        for k, v in kwargs.items():
            setattr(self, k, v)
        self.params = kwargs


NoneType = type(None)


# ===============================================================================
# Termenu
# ===============================================================================
class TermenuAdapter(termenu.Termenu):

    class RefreshSignal(ParamsException):  pass
    class TimeoutSignal(ParamsException):  pass
    class HelpSignal(ParamsException): pass

    FILTER_SEPARATOR = ","
    EMPTY = "DARK_RED<< (Empty) >>"

    class _Option(termenu.Termenu._Option):
        def __init__(self, *args, **kwargs):
            super(TermenuAdapter._Option, self).__init__(*args, **kwargs)
            self.raw = self.text
            self.text = Colorized(self.raw)
            if isinstance(self.result, str):
                self.result = ansi.decolorize(self.result)
        @property
        def selectable(self):
            return self.attrs.get("selectable", True)

        @property
        def markable(self):
            return self.attrs.get("markable", True) and self.selectable

    def __init__(self, app):
        self.text = None
        self.is_empty = True
        self.dirty = False
        self.timeout = (time.time() + app.timeout) if app.timeout else None
        self.app = app

    def reset(self, title="No Title", header="", selection=None, *args, **kwargs):
        self._highlighted = False
        remains = self.timeout and (self.timeout - time.time())
        if remains:
            fmt = "(%s<<%ds left>>)"
            if remains <= 5:
                color, fmt = "RED", "(%s<<%.1fs left>>)"
            elif remains < 11:
                color = "YELLOW"
            else:
                color = "DARK_YELLOW"
            title += fmt % (color, remains)
        if header:
            title += "\n" + header
        title = Colorized(title)
        terminal_width, _ = termenu.get_terminal_size()
        terminal_width -= 2
        title_lines = []
        for line in title.splitlines():
            while line:
                title_lines.append(line[:terminal_width])
                line = line[terminal_width:]
                if line:
                    title_lines[-1] += "DARK_RED<<\u21a9>>"
                    line = Colorized("  DARK_RED<<\u21aa>> ") + line
        self.title_height = len(title_lines)
        self.title = Colorized("\n".join(title_lines))
        with self._selection_preserved(selection):
            super(TermenuAdapter, self).__init__(*args, **kwargs)

    def _make_option_objects(self, options):
        options = super(TermenuAdapter, self)._make_option_objects(options)
        self._allOptions = options[:]
        return options

    def _decorate_flags(self, index):
        flags = super()._decorate_flags(index)
        flags['highlighted'] = self._highlighted and flags['selected']
        return flags

    def _decorate(self, option, **flags):
        "Decorate the option to be displayed"

        highlighted = flags.get("highlighted", True)
        active = flags.get("active", False)
        selected = flags.get("selected", False)
        moreAbove = flags.get("moreAbove", False)
        moreBelow = flags.get("moreBelow", False)

        # add selection / cursor decorations
        option = Colorized(("WHITE<<*>> " if selected else "  ") + ("WHITE@{>}@" if active else " ") + option)
        if highlighted:
            option = ansi.colorize(option.uncolored, "cyan", bright=True)
        else:
            option = str(option)  # convert from Colorized to ansi string

        # add more above/below indicators
        if moreAbove:
            option = option + " " + ansi.colorize("^", "white", bright=True)
        elif moreBelow:
            option = option + " " + ansi.colorize("v", "white", bright=True)
        else:
            option = option + "  "

        return option

    @contextmanager
    def _selection_preserved(self, selection=None):
        if self.is_empty:
            yield
            return

        prev_active = self._get_active_option().result
        prev_selected = set(o.result for o in self.options if o.selected) if selection is None else set(selection)
        try:
            yield
        finally:
            if prev_selected:
                for option in self.options:
                    option.selected = option.result in prev_selected
            self._set_default(prev_active)

    def show(self, default=None):
        self._refilter()
        self._clear_cache()
        self._set_default(default)
        return super(TermenuAdapter, self).show()

    def _set_default(self, default):
        if default is None:
            return
        for index, o in enumerate(self.options):
            if o.result == default:
                break
        else:
            return
        for i in range(index):
            self._on_down()

    def _adjust_width(self, option):
        option = Colorized("BLACK<<\\>>").join(option.splitlines())
        l = len(option)
        w = max(self.width, 8)
        if l > w:
            option = termenu.shorten(option, w)
        if l < w:
            option += " " * (w - l)
        return option

    def _on_key(self, key):
        bubble_up = True
        if not key == "heartbeat":
            self.timeout = None
        if key == "space":
            key = " "
        elif key == "`":
            key = "insert"

        if key == "*" and self.multiselect:
            for option in self.options:
                if option.markable:
                    option.selected = not option.selected
        elif len(key) == 1 and 32 <= ord(key) <= 127:
            if key == " " and not self.text:
                pass
            else:
                if not self.text:
                    self.text = []
                self.text.append(key)
                self._refilter()
            bubble_up = False
        elif self.is_empty and key == "enter":
            bubble_up = False
        elif self.text and key == "backspace":
            del self.text[-1]
            self._refilter()
        elif self.text is not None and key == "esc":
            filters = "".join(self.text or []).split(self.FILTER_SEPARATOR)
            if filters:
                filters.pop(-1)
            self.text = list(self.FILTER_SEPARATOR.join(filters)) if filters else None
            termenu.ansi.hide_cursor()
            bubble_up = False
            self._refilter()
        elif key == "end":
            self._on_end()
            bubble_up = False
        elif callable(getattr(self.app, "on_%s" % key, None)):
            getattr(self.app, "on_%s" % key)(self)
            bubble_up = False

        if bubble_up:
            return super(TermenuAdapter, self)._on_key(key)

    def _on_F5(self):
        self.refresh('user')

    def _on_F1(self):
        self.help()

    def _on_enter(self):
        if any(option.selected for option in self.options):
            self._highlighted = True
            self._goto_top()
            self._print_menu()
            time.sleep(.1)
        elif not self._get_active_option().selectable:
            return False
        return True # stop loop

    def _on_insert(self):
        option = self._get_active_option()
        if option.markable:
            super()._on_space()
        else:
            super()._on_down()

    def _on_end(self):
        height = min(self.height, len(self.options))
        self.scroll = len(self.options) - height
        self.cursor = height - 1

    def refresh(self, source):
        if self.timeout:
            now = time.time()
            if now > self.timeout:
                raise self.TimeoutSignal()
        raise self.RefreshSignal(source=source)

    def help(self):
        raise self.HelpSignal()

    def _on_heartbeat(self):
        self.refresh("heartbeat")

    def _print_footer(self):
        if self.text is not None:
            filters = "".join(self.text).split(self.FILTER_SEPARATOR)
            termenu.ansi.write("/%s" % termenu.ansi.colorize(" , ", "white", bright=True).join(filters))
            termenu.ansi.show_cursor()

    def _print_menu(self):
        ansi.write("\r%s\n" % self.title)
        super(TermenuAdapter, self)._print_menu()
        for _ in range(0, self.height - len(self.options)):
            termenu.ansi.clear_eol()
            termenu.ansi.write("\n")
        self._print_footer()

        termenu.ansi.clear_eol()

    def _goto_top(self):
        super(TermenuAdapter, self)._goto_top()
        ansi.up(self.title_height)

    def get_total_height(self):
        return (self.title_height +  # header
                self.height          # options
                )

    def _clear_menu(self):
        super(TermenuAdapter, self)._clear_menu()
        clear = getattr(self, "clear", True)
        termenu.ansi.restore_position()
        height = self.get_total_height()
        if clear:
            for i in range(height):
                termenu.ansi.clear_eol()
                termenu.ansi.up()
            termenu.ansi.clear_eol()
        else:
            termenu.ansi.up(height)
        ansi.clear_eol()
        ansi.write("\r")

    def _refilter(self):
        with self._selection_preserved():
            self._clear_cache()
            self.options = []
            texts = "".join(self.text or []).lower().split(self.FILTER_SEPARATOR)
            pred = lambda option: all(text in option.text.lower() for text in texts)
            # filter the matching options
            for option in self._allOptions:
                if option.attrs.get("showAlways") or pred(option):
                    self.options.append(option)
            # select the first matching element (showAlways elements might not match)
            self.scroll = 0
            for i, option in enumerate(self.options):
                if not option.attrs.get("showAlways") and pred(option):
                    self.cursor = i
                    self.is_empty = False
                    break
            else:
                self.is_empty = True
                self.options.append(self._Option(" (No match for RED<<%s>>; WHITE@{<ESC>}@ to reset filter)" % " , ".join(map(repr,texts))))


def _get_option_name(sub):
    if hasattr(sub, "get_option_name"):
        return sub.get_option_name()
    return sub.__doc__ or sub.__name__


class AppMenu(object):

    class _MenuSignal(ParamsException): pass
    class RetrySignal(_MenuSignal): pass
    class AbortedSignal(KeyboardInterrupt, _MenuSignal): pass
    class QuitSignal(_MenuSignal): pass
    class BackSignal(_MenuSignal): pass
    class ReturnSignal(_MenuSignal): pass
    class TimeoutSignal(_MenuSignal): pass

    # yield this to add a separator
    SEPARATOR = dict(text="BLACK<<%s>>" % ("-"*80), result=True, selectable=False)

    _all_titles = []
    _all_menus = []

    @property
    def title(self):
        return self.__class__.__name__

    option_name = None
    @classmethod
    def get_option_name(cls):
        return cls.option_name or cls.__name__

    @property
    def height(self):
        return termenu.get_terminal_size()[1] // 2

    @property
    def items(self):

        # convert named submenus to submenu objects (functions/classes)
        submenus = (
            getattr(self, name) if isinstance(name, str) else name
            for name in self.submenus
        )

        return [
            sub if isinstance(sub, (dict, tuple)) else (_get_option_name(sub), sub)
            for sub in submenus
        ]

    submenus = []
    default = None
    multiselect = False
    fullscreen = True
    heartbeat = None
    width = None
    actions = None
    timeout = None

    def __init__(self, *args, **kwargs):
        parent = self._all_menus[-1] if self._all_menus else None
        self._all_menus.append(self)
        self.parent = parent
        self.return_value = None
        self.initialize(*args, **kwargs)
        try:
            self._menu_loop()
        finally:
            self._all_menus.pop(-1)

    def initialize(self, *args, **kwargs):
        pass

    def banner(self):
        pass

    def help(self):
        lines = [
            "WHITE@{Menu Usage:}@",
            "",
            " * Use the WHITE@{<Up/Down>}@ arrow keys to navigate the menu",
            " * Hit WHITE@{<ESC>}@ to return to the parent menu (or exit)",
            " * Hit WHITE@{<Ctrl-C>}@ to quit",
            " * Hit WHITE@{<F5>}@ to refresh/redraw",
            " * Hit WHITE@{<F1>}@ this help screen",
            " * Use any other key to filter the current selection (WHITE@{<ESC>}@ to clear the filter)",
            "", "",
        ]
        if self.multiselect:
            lines[3:3] = [
                " * Use WHITE@{`}@ or WHITE@{<Insert>}@ to select/deselect the currently active item",
                " * Use WHITE@{*}@ to toggle selection on all items",
                " * Hit WHITE@{<Enter>}@ to proceed with currently selected items, or with the active item if nothing is selected",
            ]
        else:
            lines[3:3] = [
                " * Hit WHITE@{<Enter>}@ to select",
            ]
        print(Colorized("\n".join(lines)))
        self.wait_for_keys(prompt="(Hit any key to continue)")

    def _menu_loop(self):

        # use the default only on the first iteration
        # after that we'll default to the the last selection
        menu = self.menu = TermenuAdapter(app=self)
        self.refresh = "first"
        selection = None
        default = self.default

        try:
            while True:
                if self.refresh:
                    if self.fullscreen:
                        ansi.clear_screen()
                        ansi.home()
                    title = self.title
                    titles = [t() if isinstance(t, collections.Callable) else t for t in self._all_titles + [title]]
                    banner = self.banner
                    if isinstance(banner, collections.Callable):
                        banner = banner()
                    options = list(self.items)
                    if not options:
                        return self.result(None)

                    menu.reset(
                        title=" DARK_GRAY@{>>}@ ".join(titles),
                        header=banner,
                        options=options,
                        height=self.height,
                        multiselect=self.multiselect,
                        heartbeat=self.heartbeat or (1 if self.timeout else None),
                        width=self.width,
                        selection=selection,
                    )
                else:
                    # next time we must refresh
                    self.refresh = "second"

                try:
                    selected = menu.show(default=default)
                    default = None  # default selection only on first show
                except KeyboardInterrupt:
                    self.quit()
                except menu.RefreshSignal as e:
                    self.refresh = e.source
                    continue
                except menu.HelpSignal:
                    self.help()
                    continue
                except menu.TimeoutSignal:
                    raise self.TimeoutSignal("Timed out waiting for selection")

                self._all_titles.append(title)
                try:
                    self.on_selected(selected)
                except self.RetrySignal as e:
                    self.refresh = e.refresh  # will refresh by default unless told differently
                    selection = e.selection
                    continue
                except (KeyboardInterrupt):
                    self.refresh = False  # show the same menu
                    continue
                except self.BackSignal as e:
                    if e.levels:
                        e.levels -= 1
                        raise
                    self.refresh = e.refresh
                    continue
                else:
                    self.refresh = "second"   # refresh the menu
                finally:
                    self._all_titles.pop(-1)

        except (self.QuitSignal, self.BackSignal):
            if self.parent:
                raise

        except self.ReturnSignal as e:
            self.return_value = e.value

    def action(self, selected):
        def evaluate(item):
            if isinstance(item, type):
                # we don't want the instance of the class to be returned
                # as the a result from the menu. (See 'HitMe' class below)
                item, _ = None, item()
            if isinstance(item, collections.Callable):
                item = item()
            if isinstance(item, self._MenuSignal):
                raise item
            if isinstance(item, AppMenu):
                return
            return item
        return list(map(evaluate, selected)) if self.multiselect else evaluate(selected)

    def on_selected(self, selected):
        if not selected and isinstance(selected, (NoneType, list)):
            self.back()

        actions = self.get_selection_actions(selected)

        if isinstance(actions, (list, tuple)):
            to_submenu = lambda action: (_get_option_name(action), functools.partial(action, selected))
            actions = [action if isinstance(action, collections.Callable) else getattr(self, action) for action in actions]
            ret = self.show(title=self.get_selection_title(selected), options=list(map(to_submenu, actions)))
        else:
            if actions is None:
                action = self.action
            elif isinstance(actions, str):
                action = getattr(self, actions)
            else:
                action = actions
            ret = action(selected)

        if ret is not None:
            self.result(ret)

    def get_selection_actions(self, selection):
        # override this to change available actions per selection
        return self.actions

    def get_selection_title(self, selection):
        return "Selected %s items" % len(selection)

    @classmethod
    def retry(cls, refresh="app", selection=None):
        "Refresh into the current menu"
        raise cls.RetrySignal(refresh=refresh, selection=selection)

    @classmethod
    def back(cls, refresh=True, levels=1):
        "Go back to the parent menu"
        raise cls.BackSignal(refresh=refresh, levels=levels)

    @classmethod
    def result(cls, value):
        "Return result back to the parent menu"
        raise cls.ReturnSignal(value=value)

    @classmethod
    def quit(cls):
        "Quit the whole menu system"
        raise cls.QuitSignal()

    @staticmethod
    def show(title, options, default=None, back_on_abort=True, **kwargs):
        if callable(options):
            options = property(options)
        kwargs.update(title=title, items=options, default=default, back_on_abort=back_on_abort)
        menu = type("AdHocMenu", (AppMenu,), kwargs)()
        return menu.return_value

    @staticmethod
    def wait_for_keys(keys=("enter", "esc"), prompt=None):
        if prompt:
            print(Colorized(prompt), end=" ", flush=True)

        keys = set(keys)
        for key in keyboard.keyboard_listener():
            if not keys or key in keys:
                print()
                return key
