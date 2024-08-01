from typing import Type

import ttkbootstrap as ttk
from ttkbootstrap import constants as c

from .devices_tab import ConnectedDevicesWidget
from .experiment_tab import ExperimentWidget
from .store import Store


class MainWindow(ttk.Frame):
    def __init__(self, master: ttk.Window):
        super().__init__(master)
        self.master = master
        self.master.title("Bioexperiment Suite")
        self.pack(fill=c.BOTH, expand=c.YES)

        self.store = Store()

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=c.BOTH, expand=c.YES)

        self.add_tab(ConnectedDevicesWidget, "Devices")
        self.add_tab(ExperimentWidget, "Experiment")

    def add_tab(self, tab_constructor: Type[ttk.Frame], title: str):
        tab = tab_constructor(self.notebook, self.store)
        tab.pack(fill=c.BOTH, expand=c.YES)
        self.notebook.add(tab, text=title)


def main():
    root = ttk.Window(minsize=(1000, 600), themename="litera")
    MainWindow(root)
    root.mainloop()


if __name__ == "__main__":
    main()
