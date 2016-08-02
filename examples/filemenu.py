import os
import sys
import termenu

"""
This example shows how to implement a file browser using multi-level menus
and custom menu item decoration.
"""

class FilePlugin(termenu.Plugin):
    # TODO go back one level using backspace
    def _decorate_flags(self, index):
        flags = self.parent._decorate_flags(index)
        flags.update(dict(
            directory = self.host.options[self.host.scroll+index].text[-1] == "/",
            exe = isexe(self.host.options[self.host.scroll+index].text)
        ))
        return flags

    def _decorate(self, option, **flags):
        directory = flags.get("directory", False)
        exe = flags.get("exe", False)
        active = flags.get("active", False)
        selected = flags.get("selected", False)
        if active:
            if directory:
                option = termenu.ansi.colorize(option, "blue", "white", bright=True)
            elif exe:
                option = termenu.ansi.colorize(option, "green", "white", bright=True)
            else:
                option = termenu.ansi.colorize(option, "black", "white")
        elif directory:
            option = termenu.ansi.colorize(option, "blue", bright=True)
        elif exe:
            option = termenu.ansi.colorize(option, "green", bright=True)
        if selected:
            option = termenu.ansi.colorize("* ", "red") + option
        else:
            option = "  " + option

        return self.host._decorate_indicators(option, **flags)

def isexe(path):
    return os.path.isfile(path) and os.access(path, os.X_OK)

def list_files():
    dirs = list(sorted([f+"/" for f in os.listdir(".") if os.path.isdir(f)]))
    files = list(sorted([f for f in os.listdir(".") if not os.path.isdir(f)]))
    entries = dirs + files
    entries = [e for e in entries if e[0] != "."]
    if os.getcwd() != "/":
        entries = ["../"] + entries
    return entries

def main():
    redirectedStdin, redirectedStdout = termenu.redirect_std()
    while True:
        selected = termenu.Termenu(list_files(), plugins=[termenu.FilterPlugin(), FilePlugin()]).show()
        if selected:
            if len(selected) == 1 and os.path.isdir(selected[0]):
                os.chdir(selected[0])
            else:
                for file in selected:
                    print(os.path.abspath(file), file=redirectedStdout)
                return
        else:
            return

if __name__ == "__main__":
    main()
