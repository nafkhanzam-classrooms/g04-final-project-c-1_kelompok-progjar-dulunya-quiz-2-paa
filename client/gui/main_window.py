"""Tampilan 3 kolom setelah masuk project: tree file, editor, chat. Tugasnya buat ngarahin pesan dari server ke panel yang sesuai."""

import tkinter as tk
from tkinter import messagebox

from shared.protocol import MessageType
from gui.file_browser import ProjectTreeFrame
from gui.editor import TextEditorFrame
from gui.chat_box import ChatFrame


class EditorScreen(tk.Frame):
    def __init__(self, parent, net, room_id, on_leave, **kwargs):
        super().__init__(parent, **kwargs)
        self.net = net
        self.room_id = room_id
        self.on_leave = on_leave
        self.left_visible = True
        self.right_visible = True

        self._build()
        self._register_handlers()

    def _build(self):
        self.paned_window = tk.PanedWindow(self, orient=tk.HORIZONTAL,
                                           sashrelief=tk.RAISED, sashwidth=6)
        self.paned_window.pack(fill=tk.BOTH, expand=1)

        self.tree_panel = ProjectTreeFrame(
            self.paned_window, bg_color="#ffecec", net=self.net,
            room_id=self.room_id, on_open_file=self._open_file,
            width=240, height=400)
        self.editor_panel = TextEditorFrame(
            self.paned_window, bg_color="#f4fff4", net=self.net,
            room_id=self.room_id, width=600, height=400)
        self.chat_panel = ChatFrame(
            self.paned_window, bg_color="#eef4ff", net=self.net,
            room_id=self.room_id, width=280, height=400)

        self._refresh_panes()
        self._build_bottom_bar()

    def _build_bottom_bar(self):
        bar = tk.Frame(self)
        bar.pack(fill="x", side="bottom")
        tk.Label(bar, text=f"Project: {self.room_id}", fg="#333").pack(side="left", padx=8)

        self.toggle_dir_button = tk.Button(bar, text="Hide Tree", command=self._toggle_dir)
        self.toggle_dir_button.pack(side="left", padx=8, pady=8)
        self.toggle_chat_button = tk.Button(bar, text="Hide Chat", command=self._toggle_chat)
        self.toggle_chat_button.pack(side="left", padx=8, pady=8)
        tk.Button(bar, text="Leave Project", command=self._leave).pack(side="right", padx=8, pady=8)

    def _refresh_panes(self):
        for pane in (self.tree_panel, self.editor_panel, self.chat_panel):
            try:
                self.paned_window.forget(pane)
            except tk.TclError:
                pass
        if self.left_visible:
            self.paned_window.add(self.tree_panel, stretch="always")
        self.paned_window.add(self.editor_panel, stretch="always")
        if self.right_visible:
            self.paned_window.add(self.chat_panel, stretch="always")

    def _toggle_dir(self):
        self.left_visible = not self.left_visible
        self.toggle_dir_button.config(text="Show Tree" if not self.left_visible else "Hide Tree")
        self._refresh_panes()

    def _toggle_chat(self):
        self.right_visible = not self.right_visible
        self.toggle_chat_button.config(text="Show Chat" if not self.right_visible else "Hide Chat")
        self._refresh_panes()

    def _open_file(self, path):
        self.editor_panel.open_file(path)

    def _leave(self):
        self.net.send(MessageType.LEAVE_PROJECT, room_id=self.room_id)
        self.on_leave()

    def _register_handlers(self):
        self.net.set_handlers({
            MessageType.FILE_LIST_RESULT: self._on_file_list,
            MessageType.FILE_CONTENT: self.editor_panel.load_content,
            MessageType.EDIT: self.editor_panel.apply_remote,
            MessageType.ACK: self.editor_panel.on_ack,
            MessageType.CHAT: self.chat_panel.add_message,
            MessageType.PRIVATE_CHAT: self.chat_panel.add_private_message,
            MessageType.REACTION_UPDATE: self.chat_panel.update_reaction,
            MessageType.CHAT_HISTORY: self.chat_panel.load_history,
            MessageType.PRESENCE: self.chat_panel.update_presence,
            MessageType.TYPING: self.chat_panel.update_typing,
            MessageType.ERROR: self._on_error,
        })

    def _on_file_list(self, message):
        self.tree_panel.update_tree(message.get("tree", []))
        # tutup editor kalau file yang lagi dibuka udah ga ada
        open_path = self.editor_panel.current_path
        if open_path and open_path not in self._all_paths(message.get("tree", [])):
            self.editor_panel.on_file_removed(open_path)

    def _all_paths(self, nodes, prefix=""):
        paths = set()
        for n in nodes:
            full = f"{prefix}{n['name']}"
            paths.add(full)
            if n.get("type") == "dir":
                paths |= self._all_paths(n.get("children", []), full + "/")
        return paths

    def _on_error(self, message):
        messagebox.showerror("Error", message.get("message", "Error"), parent=self)
        if (message.get("code") == "NO_PROJECT"):
            self.on_leave()
