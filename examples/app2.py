import time
from termenu.app import AppMenu

def leave():
    print("Leave...")
    AppMenu.quit()

def go():
    def back():
        print("Going back.")
        AppMenu.back()

    def there():
        ret = AppMenu.show("Where's there?",
            "Spain France Albania".split() + [("Quit", AppMenu.quit)],
            multiselect=True, back_on_abort=True)
        print(ret)
        return ret

    return AppMenu.show("Go Where?", [
        ("YELLOW<<Back>>", back),
        ("GREEN<<There>>", there)
    ])

if __name__ == "__main__":
    AppMenu.show("Make your MAGENTA<<decision>>", [
        ("RED<<Leave>>", leave),
        ("BLUE<<Go>>", go)
    ])