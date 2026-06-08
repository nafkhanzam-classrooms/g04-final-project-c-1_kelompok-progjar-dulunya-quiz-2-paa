import tkinter as tk
from tkinter import ttk
from gui.main_window import TkinterApp

example_chat = [
    {"name": "system", "timestamp": "2023-04-01 12:00:00", "content": "You are a helpful assistant."},
    {"name": "system", "timestamp": "2023-04-01 12:00:00", "content": "You are a helpful assistant."},
]

example_project_dir = [
    {"type": "dir", "name": "Project1", "children": [
        {"type": "file", "name": "main.py"},
        {"type": "file", "name": "utils.py"},
        {"type": "dir", "name": "data", "children": [
            {"type": "file", "name": "data.csv"},
            {"type": "file", "name": "info.json"},
        ]},
    ]},
    {"type": "file", "name": "README.md"},
    {"type": "file", "name": "requirements.txt"},
]


class ColumnFrame(tk.Frame):
    def __init__(self, parent, bg_color, text, items=None, **kwargs):
        super().__init__(parent, bg=bg_color, **kwargs)
        self.bg_color = bg_color
        self.text = text
        self.items = items or []
        self._build_contents()

    def _build_contents(self):
        for item in self.items:
            item_label = tk.Label(self, text=item, bg=self.bg_color)
            item_label.pack(anchor="w", padx=10, pady=5)

        footer_label = tk.Label(self, text=self.text, bg=self.bg_color)
        footer_label.pack(expand=True)



if __name__ == "__main__":
    app = TkinterApp()
    app.run()