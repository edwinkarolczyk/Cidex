from ui_column_widths import SYMBOL_WIDTH, install_column_widths


def test_symbol_column_is_one_third_narrower_and_no_longer_stretches():
    calls = []

    class Table:
        def column(self, name, **kwargs):
            calls.append((name, kwargs))

    class App:
        def _build_ui(self):
            self.table = Table()

    install_column_widths(App)
    app = App()
    app._build_ui()

    symbol = [kwargs for name, kwargs in calls if name == "symbol"][-1]
    department = [kwargs for name, kwargs in calls if name == "department"][-1]

    assert SYMBOL_WIDTH == 173
    assert symbol["width"] == 173
    assert symbol["stretch"] is False
    assert department["stretch"] is True
