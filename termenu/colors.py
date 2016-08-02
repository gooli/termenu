#!/usr/bin/env python
from __future__ import print_function

import re
from . import ansi


colorizers_cache = {}


_RE_COLOR_SPEC = re.compile(
    "([\w]+)(?:\((.*)\))?"        # 'red', 'red(white)'
    )

_RE_COLOR = re.compile(           # 'RED<<text>>', 'RED(WHITE)<<text>>', 'RED@{text}@'
    r"(?ms)"                      # flags: mutliline/dot-all
    "([A-Z_]+"                    # foreground color
            "(?:\([^\)]+\))?"     # optional background color
        "(?:(?:\<\<).*?(?:\>\>)"  # text string inside <<...>>
            "|"
        "(?:\@\{).*?(?:\}\@)))"   # text string inside @{...}@
    )

_RE_COLORING = re.compile(
    # 'RED', 'RED(WHITE)'
    r"(?ms)"
    "([A-Z_]+(?:\([^\)]+\))?)"       # foreground color and optional background color
    "((?:\<\<.*?\>\>|\@\{.*?\}\@))"  # text string inside either <<...>> or @{...}@
    )


def get_colorizer(name):
    name = name.lower()
    try:
        return colorizers_cache[name]
    except KeyError:
        pass

    bright = True
    color, background = (c and c.lower() for c in _RE_COLOR_SPEC.match(name).groups())
    dark, _, color = color.rpartition("_")
    if dark == 'dark':
        bright = False
    if color not in ansi.COLORS:
        color = "white"
    if background not in ansi.COLORS:
        background = None
    fmt = ansi.colorize("{TEXT}", color, background, bright=bright)
    colorizer = lambda text: fmt.format(TEXT=text)
    return add_colorizer(name, colorizer)


def add_colorizer(name, colorizer):
    colorizers_cache[name.lower()] = colorizer
    return colorizer


def colorize_by_patterns(text, no_color=False):
    if no_color:
        _subfunc = lambda match_obj: match_obj.group(2)[2:-2]
    else:
        _subfunc = lambda match_obj: get_colorizer(match_obj.group(1))(match_obj.group(2)[2:-2])

    text = _RE_COLORING.sub(_subfunc, text)
    if no_color:
        text = ansi.decolorize(text)
    return text


class Colorized(str):

    class Token(str):

        def raw(self):
            return self

        def copy(self, text):
            return self.__class__(text)

        def __getslice__(self, start, stop):
            return self[start:stop:]

        def __getitem__(self, *args):
            return self.copy(str.__getitem__(self, *args))

        def __iter__(self):
            for c in str.__str__(self):
                yield self.copy(c)

    class ColoredToken(Token):

        def __new__(cls, text, colorizer_name):
            self = str.__new__(cls, text)
            if ">>" in text or "<<" in text:
                self.__p, self.__s = "@{", "}@"
            else:
                self.__p, self.__s = "<<", ">>"
            self.__name = colorizer_name
            return self

        def __str__(self):
            return get_colorizer(self.__name)(str.__str__(self))

        def copy(self, text):
            return self.__class__(text, self.__name)

        def raw(self):
            return "".join((self.__name, self.__p, str.__str__(self), self.__s))

        def __repr__(self):
            return repr(self.raw())

    def __new__(cls, text):
        self = str.__new__(cls, text)
        self.tokens = []
        for text in _RE_COLOR.split(text):
            match = _RE_COLORING.match(text)
            if match:
                stl = match.group(1).strip("_")
                text = match.group(2)[2:-2]
                for l in text.splitlines():
                    self.tokens.append(self.ColoredToken(l, stl))
                    self.tokens.append(self.Token("\n"))
                if not text.endswith("\n"):
                    del self.tokens[-1]
            else:
                self.tokens.append(self.Token(text))
        self.uncolored = "".join(str.__str__(token) for token in self.tokens)
        self.colored = "".join(str(token) for token in self.tokens)
        return self

    def raw(self):
        return str.__str__(self)

    def __str__(self):
        return self.colored

    def withuncolored(func):
        def inner(self, *args):
            return func(self.uncolored, *args)
        return inner

    __len__ = withuncolored(len)
    count = withuncolored(str.count)
    endswith = withuncolored(str.endswith)
    find = withuncolored(str.find)
    index = withuncolored(str.index)
    isalnum = withuncolored(str.isalnum)
    isalpha = withuncolored(str.isalpha)
    isdigit = withuncolored(str.isdigit)
    islower = withuncolored(str.islower)
    isspace = withuncolored(str.isspace)
    istitle = withuncolored(str.istitle)
    isupper = withuncolored(str.isupper)
    rfind = withuncolored(str.rfind)
    rindex = withuncolored(str.rindex)

    def withcolored(func):
        def inner(self, *args):
            return self.__class__("".join(t.copy(func(t, *args)).raw() for t in self.tokens if t))
        return inner

    #capitalize = withcolored(str.capitalize)
    expandtabs = withcolored(str.expandtabs)
    lower = withcolored(str.lower)
    replace = withcolored(str.replace)

    # decode = withcolored(str.decode)
    # encode = withcolored(str.encode)
    swapcase = withcolored(str.swapcase)
    title = withcolored(str.title)
    upper = withcolored(str.upper)

    def __getitem__(self, idx):
        if isinstance(idx, slice) and idx.step is None:
            start = idx.start or 0
            stop = idx.stop or len(self)
            if start < 0:
                start += stop
            cursor = 0
            tokens = []
            for token in self.tokens:
                tokens.append(token[max(0, start - cursor):stop - cursor])
                cursor += len(token)
                if cursor > stop:
                    break
            return self.__class__("".join(t.raw() for t in tokens if t))

        tokens = [c for token in self.tokens for c in token].__getitem__(idx)
        return self.__class__("".join(t.raw() for t in tokens if t))

    def __getslice__(self, *args):
        return self.__getitem__(slice(*args))

    def __add__(self, other):
        return self.__class__("".join(map(str.__str__, (self, other))))

    def __mod__(self, other):
        return self.__class__(self.raw() % other)

    def format(self, *args, **kwargs):
        return self.__class__(self.raw().format(*args, **kwargs))

    def rjust(self, *args):
        padding = self.uncolored.rjust(*args)[:-len(self.uncolored)]
        return self.__class__(padding + self.raw())

    def ljust(self, *args):
        padding = self.uncolored.ljust(*args)[len(self.uncolored):]
        return self.__class__(self.raw() + padding)

    def center(self, *args):
        padded = self.uncolored.center(*args)
        return self.__class__(padded.replace(self.uncolored, self.raw()))

    def join(self, *args):
        return self.__class__(self.raw().join(*args))

    def _iter_parts(self, parts):
        last_cursor = 0
        for part in parts:
            pos = self.uncolored.find(part, last_cursor)
            yield self[pos:pos + len(part)]
            last_cursor = pos + len(part)

    def withiterparts(func):
        def inner(self, *args):
            return list(self._iter_parts(func(self.uncolored, *args)))
        return inner

    split = withiterparts(str.split)
    rsplit = withiterparts(str.rsplit)
    splitlines = withiterparts(str.splitlines)
    partition = withiterparts(str.partition)
    rpartition = withiterparts(str.rpartition)

    def withsingleiterparts(func):
        def inner(self, *args):
            return next(self._iter_parts([func(self.uncolored, *args)]))
        return inner

    strip = withsingleiterparts(str.strip)
    lstrip = withsingleiterparts(str.lstrip)
    rstrip = withsingleiterparts(str.rstrip)

    def zfill(self, *args):
        padding = self.uncolored.zfill(*args)[:-len(self.uncolored)]
        return self.__class__(padding + self.raw())

C = Colorized


if __name__ == '__main__':
    import fileinput
    for line in fileinput.input():
        print(colorize_by_patterns(line), end="")
