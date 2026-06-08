import tkinter as tk
from gui.file_browser import ProjectTreeFrame
from gui.editor import TextEditorFrame
from gui.chat_box import ChatFrame


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


class TkinterApp:
    def __init__(self, title="Resizable 3-Column Layout", size="1600x900"):
        self.root = tk.Tk()
        self.root.title(title)
        self.root.geometry(size)
        self.left_visible = True
        self.right_visible = True
        self.paned_window = self._create_paned_window()
        self._create_columns()
        self._create_bottom_buttons()

    def _create_paned_window(self):
        pane = tk.PanedWindow(
            self.root,
            orient=tk.HORIZONTAL,
            sashrelief=tk.RAISED,
            sashwidth=6,
        )
        pane.pack(fill=tk.BOTH, expand=1)
        return pane

    def _create_columns(self):
        left_column = ProjectTreeFrame(
            self.paned_window,
            bg_color="#ff9999",
            tree_data=example_project_dir,
            width=200,
            height=400,
        )
        center_column = TextEditorFrame(
            self.paned_window,
            bg_color="#99ff99",
            initial_text="# Start typing here...\n",
            width=200,
            height=400,
        )
        right_column = ChatFrame(
            self.paned_window,
            bg_color="#99ccff",
            chats=example_chat,
            width=200,
            height=400,
        )

        self.left_column = left_column
        self.center_column = center_column
        self.right_column = right_column

        self._refresh_panes()

    def _create_bottom_buttons(self):
        button_frame = tk.Frame(self.root)
        button_frame.pack(fill="x", side="bottom")

        self.toggle_dir_button = tk.Button(
            button_frame,
            text="Hide Project Tree",
            command=self._toggle_dir_tree,
        )
        self.toggle_dir_button.pack(side="left", padx=8, pady=8)

        self.toggle_chat_button = tk.Button(
            button_frame,
            text="Hide Chat",
            command=self._toggle_chat,
        )
        self.toggle_chat_button.pack(side="left", padx=8, pady=8)

        leave_button = tk.Button(
            button_frame,
            text="Leave Project",
            command=self._leave_project,
        )
        leave_button.pack(side="left", padx=8, pady=8)

    def _toggle_dir_tree(self):
        self.left_visible = not self.left_visible
        self.toggle_dir_button.config(
            text="Show Project Tree" if not self.left_visible else "Hide Project Tree"
        )
        self._refresh_panes()

    def _toggle_chat(self):
        self.right_visible = not self.right_visible
        self.toggle_chat_button.config(
            text="Show Chat" if not self.right_visible else "Hide Chat"
        )
        self._refresh_panes()

    def _refresh_panes(self):
        for pane in (self.left_column, self.center_column, self.right_column):
            try:
                self.paned_window.forget(pane)
            except tk.TclError:
                pass

        if self.left_visible:
            self.paned_window.add(self.left_column, stretch="always")
        self.paned_window.add(self.center_column, stretch="always")
        if self.right_visible:
            self.paned_window.add(self.right_column, stretch="always")

    def _leave_project(self):
        self.root.quit()

    def run(self):
        self.root.mainloop()