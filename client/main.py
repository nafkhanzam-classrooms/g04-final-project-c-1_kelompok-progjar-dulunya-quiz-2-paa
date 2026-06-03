import tkinter as tk
from tkinter import ttk

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


class ProjectTreeFrame(tk.Frame):
    def __init__(self, parent, bg_color, tree_data, **kwargs):
        super().__init__(parent, bg=bg_color, **kwargs)
        self.bg_color = bg_color
        self.tree_data = tree_data or []
        self._build_contents()

    def _build_contents(self):
        header = tk.Label(self, text="Project Tree", bg=self.bg_color, font=(None, 12, "bold"))
        header.pack(fill="x", padx=8, pady=(8, 4))

        tree_container = tk.Frame(self)
        tree_container.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        style = ttk.Style()
        style.configure(
            "ProjectTreeview.Treeview",
            background="#ffffff",
            fieldbackground="#ffffff",
            rowheight=28,
            padding=4,
        )
        style.layout(
            "ProjectTreeview.Treeview",
            [
                (
                    "Treeview.field",
                    {
                        "sticky": "nswe",
                        "children": [
                            (
                                "Treeview.padding",
                                {
                                    "sticky": "nswe",
                                    "children": [
                                        ("Treeview.treearea", {"sticky": "nswe"})
                                    ],
                                },
                            )
                        ],
                    },
                )
            ],
        )

        self.tree = ttk.Treeview(tree_container, show="tree", style="ProjectTreeview.Treeview")
        self.tree.pack(side="left", fill="both", expand=True)

        scrollbar = tk.Scrollbar(tree_container, orient="vertical", command=self.tree.yview)
        scrollbar.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=scrollbar.set)

        self._populate_tree("", self.tree_data)

    def _populate_tree(self, parent, nodes):
        for node in nodes:
            node_id = self.tree.insert(parent, "end", text=node["name"], open=False)
            if node["type"] == "dir" and node.get("children"):
                self._populate_tree(node_id, node["children"])


class TextEditorFrame(tk.Frame):
    def __init__(self, parent, bg_color, initial_text="", **kwargs):
        super().__init__(parent, bg=bg_color, **kwargs)
        self.bg_color = bg_color
        self._build_contents(initial_text)

    def _build_contents(self, initial_text):
        header = tk.Label(self, text="Text Editor", bg=self.bg_color, font=(None, 12, "bold"))
        header.pack(fill="x", padx=8, pady=(8, 4))
        
        editor_container = tk.Frame(self)
        editor_container.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        self.line_numbers = tk.Text(
            editor_container,
            width=4,
            padx=4,
            pady=4,
            bd=0,
            bg="#ececec",
            fg="#555555",
            state="disabled",
            takefocus=0,
        )
        self.line_numbers.pack(side="left", fill="y")

        self.text_widget = tk.Text(editor_container, wrap="word", undo=True)
        self.scrollbar = tk.Scrollbar(editor_container, command=self._on_scroll)
        self.text_widget.configure(yscrollcommand=self._on_text_scroll)

        self.scrollbar.pack(side="right", fill="y")
        self.text_widget.pack(side="left", fill="both", expand=True)

        self.text_widget.bind("<<Modified>>", self._on_text_changed)

        if initial_text:
            self.text_widget.insert("1.0", initial_text)

        self._update_line_numbers()
        self.text_widget.edit_modified(False)

    def _on_scroll(self, *args):
        self.text_widget.yview(*args)
        self.line_numbers.yview(*args)

    def _on_text_scroll(self, *args):
        self.scrollbar.set(*args)
        if args:
            self.line_numbers.yview_moveto(args[0])

    def _on_text_changed(self, event=None):
        if self.text_widget.edit_modified():
            self._update_line_numbers()
            self.text_widget.edit_modified(False)

    def _update_line_numbers(self):
        line_count = int(self.text_widget.index("end-1c").split(".")[0])
        line_numbers = "\n".join(str(i) for i in range(1, line_count + 1))
        self.line_numbers.configure(state="normal")
        self.line_numbers.delete("1.0", tk.END)
        self.line_numbers.insert("1.0", line_numbers)
        self.line_numbers.configure(state="disabled")


class ChatFrame(tk.Frame):
    def __init__(self, parent, bg_color, chats, **kwargs):
        super().__init__(parent, bg=bg_color, **kwargs)
        self.bg_color = bg_color
        self.chats = chats or []
        self._build_contents()
        self._refresh_chat_view()

    def _build_contents(self):
        header = tk.Label(self, text="Chat", bg=self.bg_color, font=(None, 12, "bold"))
        header.pack(fill="x", padx=8, pady=(8, 4))

        chat_container = tk.Frame(self)
        chat_container.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        self.chat_display = tk.Text(chat_container, wrap="word", state="disabled", bg="#f5f5ff")
        self.chat_scrollbar = tk.Scrollbar(chat_container, command=self.chat_display.yview)
        self.chat_display.configure(yscrollcommand=self.chat_scrollbar.set)

        self.chat_scrollbar.pack(side="right", fill="y")
        self.chat_display.pack(side="left", fill="both", expand=True)

        input_frame = tk.Frame(self)
        input_frame.pack(fill="x", padx=8, pady=(0, 8))

        self.message_entry = tk.Entry(input_frame)
        self.message_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.message_entry.bind("<Return>", lambda event: self._send_message())

        send_button = tk.Button(input_frame, text="Send", command=self._send_message)
        send_button.pack(side="right")

    def _refresh_chat_view(self):
        self.chat_display.configure(state="normal")
        self.chat_display.delete("1.0", tk.END)

        for chat in self.chats:
            message = f"[{chat['timestamp']}] {chat['name']}: {chat['content']}\n"
            self.chat_display.insert(tk.END, message)

        self.chat_display.configure(state="disabled")
        self.chat_display.see(tk.END)

    def _send_message(self):
        content = self.message_entry.get().strip()
        if not content:
            return

        timestamp = __import__("datetime").datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        new_chat = {"name": "You", "timestamp": timestamp, "content": content}
        self.chats.append(new_chat)
        self.message_entry.delete(0, tk.END)
        self._refresh_chat_view()


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


if __name__ == "__main__":
    app = TkinterApp()
    app.run()