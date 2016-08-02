import sys
sys.path.insert(0, "..")
import termenu

"""
This example shows how you could implement a menu for a very long (or endless)
list of options.
"""

class IteratorList(object):
    def __init__(self, iter):
        self._iter = iter
        self._list = []

    def __getitem__(self, index):
        if isinstance(index, slice):
            return self.__slice__(index.start, index.stop, index.step)
        try:
            while index >= len(self._list):
                self._list.append(next(self._iter))
        except StopIteration:
            pass
        return self._list[index]

    def __slice__(self, i, j, k=None):
        self[j]
        return self._list[i:j:k]

def show_long_menu(optionsIter, pagesize=30):
    Next = object()
    Previous = object()
    options = IteratorList("%05d" % n for n in optionsIter)
    start = 0
    while True:
        page = options[start:start+pagesize]
        if len(page) == pagesize:
            page.append((">>", Next))
        if start > 0:
            page.insert(0, ("<<", Previous))
        result = termenu.Termenu(page, multiselect=False).show()
        if not result:
            break
        if result == Next:
            start = start + pagesize
        elif result == Previous:
            start = start - pagesize
        else:
            break

    return result

if __name__ == "__main__":
    show_long_menu(range(500))
