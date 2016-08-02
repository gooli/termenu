import time
from termenu.app import AppMenu
from functools import reduce
try:
    input = raw_input
except NameError:
    pass


class TopMenu(AppMenu):
    title = staticmethod(lambda: "YELLOW<<%s>>" % time.ctime())
    timeout = 15
    submenus = ["Empty", "Letters", "Numbers", "Submenu", "Foo", "Bar"]

    class Empty(AppMenu):
        title = "CYAN(BLUE)<<Empty>>"
        option_name = "BLUE<<Empty>>"
        items = []
        def action(self, letters):
            input("Selected: %s" % "".join(letters))

    class Letters(AppMenu):
        title = "CYAN(BLUE)<<Letters>>"
        option_name = "BLUE<<Letters>>"
        multiselect = True
        items = [chr(i) for i in range(65, 91)]
        def action(self, letters):
            input("Selected: %s" % "".join(letters))

    class Numbers(AppMenu):
        multiselect = True
        @property
        def items(self):
            return list(range(int(time.time()*2) % 10, 50))
        def get_selection_actions(self, selection):
            yield "MinMax"
            yield "Add"
            if min(selection) > 0:
                yield "Multiply"
            yield "Quit"
        def get_selection_title(self, selection):
            return ", ".join(map(str, sorted(selection)))
        def MinMax(self, numbers):
            "Min/Max"
            input("Min: %s, Max: %s" % (min(numbers), max(numbers)))
            self.retry()
        def Add(self, numbers):
            input("Sum: %s" % sum(numbers))
            self.back()
        def Multiply(self, numbers):
            input("Mult: %s" % reduce((lambda a, b: a*b), numbers))
        def Quit(self, numbers):
            input("%s" % numbers)
            self.quit()


    class Submenu(AppMenu):
        submenus = ["Letter", "Number"]

        class Letter(AppMenu):
            @property
            def items(self):
                return [chr(i) for i in range(65, 91)][int(time.time()*2) % 10:][:10]
            def action(self, letter):
                input("Selected: %s" % letter)
                self.back()

        class Number(AppMenu):
            items = list(range(50))
            def action(self, number):
                input("Sum: %s" % number)

    def Foo(self):
        input("Foo?")

    def Bar(object):
        input("Bar! ")

    Bar.get_option_name = lambda: "Dynamic option name: (%s)" % (int(time.time()) % 20)


if __name__ == "__main__":
    TopMenu()
