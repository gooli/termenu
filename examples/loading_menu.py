import sys
sys.path.insert(0, "..")
import time
import termenu
import threading

"""
This example shows how you could implement a menu for data that is loading slowly,
for instance over a network or as a result of some processing.
"""

class AutoloadingList(object):
    def __init__(self, iter):
        self._iter = iter
        self._list = []
        self._lock = threading.RLock()
        self._thread = threading.Thread(target=self._loader_thread)
        self._thread.setDaemon(True)
        self._thread.start()

    def __getitem__(self, index):
        with self._lock:
            return self._list[index]

    def __len__(self):
        with self._lock:
            return len(self._list)

    def _loader_thread(self):
        for item in self._iter:
            with self._lock:
                self._list.append(item)

class IteratorPlugin(termenu.Plugin):
    def __init__(self):
        self._prevLen = 0

    def _make_option_objects(self, options):
        self._optionList = AutoloadingList(iter(options))
        # wait for at least 30 items to be loaded before showing the menu
        while len(self._optionList) < 30:
            time.sleep(0.1)
        return self.parent._make_option_objects(self._optionList)

    def _on_heartbeat(self):
        if self._prevLen != len(self._optionList):
            self.host.options = self.parent._make_option_objects(self._optionList)
        return self.parent._on_heartbeat()

class TitleCounterPlugin(termenu.TitlePlugin):
    def __init__(self):
        pass

    def _print_menu(self):
        self.title = "Showing %d options" % len(self.host.options)
        return super(TitleCounterPlugin, self)._print_menu()

def data(size):
    for i in range(size):
        yield i
        time.sleep(0.05)

if __name__ == "__main__":
    options = ("%05d" % n for n in data(500))
    menu = termenu.Termenu(options, heartbeat=0.5, plugins=[TitleCounterPlugin(), IteratorPlugin()])
    menu.show()
