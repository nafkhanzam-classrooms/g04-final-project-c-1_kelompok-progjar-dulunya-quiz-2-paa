"""Tree file project, datanya dari server. Isi tree diambil dari FILE_LIST_RESULT, terus create/rename/delete cuma ngirim FILE_SYSTEM, terus server yang broadcast tree barunya. Double-klik file buat buka di editor."""

import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
from tkinter import simpledialog

from shared.protocol import MessageType
from gui import theme


class ProjectTreeFrame(tk.Frame):
    def __init__(self, parent, bg_color, net, room_id, on_open_file, tree_data=None, **kwargs):
        super().__init__(parent, bg=bg_color, **kwargs)
        self.bg_color = bg_color
        self.net = net
        self.room_id = room_id
        self.on_open_file = on_open_file
        self._build_contents()
        if tree_data:
            self.update_tree(tree_data)

    def _get_type(self, item):
        values = self.tree.item(item, "values")
        return values[0] if values else "dir"

    def _node_path(self, item):
        # path relatif 'a/b/c' dari sebuah item di tree
        parts = []
        while item:
            parts.append(self.tree.item(item, "text"))
            item = self.tree.parent(item)
        return "/".join(reversed(parts))

    def _target_dir(self):
        # folder tempat file/folder baru dibuat ('' = root project)
        sel = self.tree.selection()
        if not sel:
            return ""
        item = sel[0]
        if self._get_type(item) == "file":
            item = self.tree.parent(item)
        return self._node_path(item) if item else ""

    def _create_file(self):
        name = simpledialog.askstring("New File", "File name:", parent=self)
        if not name:
            return
        path = "/".join(p for p in (self._target_dir(), name) if p)
        self.net.send(MessageType.FILE_SYSTEM, room_id=self.room_id,
                      operation="CREATE_FILE", path=path)

    def _create_folder(self):
        name = simpledialog.askstring("New Folder", "Folder name:", parent=self)
        if not name:
            return
        path = "/".join(p for p in (self._target_dir(), name) if p)
        self.net.send(MessageType.FILE_SYSTEM, room_id=self.room_id,
                      operation="CREATE_DIR", path=path)

    def _rename_item(self):
        sel = self.tree.selection()
        if not sel:
            return
        old_name = self.tree.item(sel[0], "text")
        new_name = simpledialog.askstring("Rename", "New name:", initialvalue=old_name, parent=self)
        if not new_name or new_name == old_name:
            return
        self.net.send(MessageType.FILE_SYSTEM, room_id=self.room_id,
                      operation="RENAME", path=self._node_path(sel[0]), new_name=new_name)

    def _delete_item(self):
        sel = self.tree.selection()
        if not sel:
            return
        if messagebox.askyesno("Confirm", "Delete selected item?", parent=self):
            self.net.send(MessageType.FILE_SYSTEM, room_id=self.room_id,
                          operation="DELETE", path=self._node_path(sel[0]))

    def _on_double_click(self, event):
        item = self.tree.identify_row(event.y)
        if item and self._get_type(item) == "file":
            self.on_open_file(self._node_path(item))

    def _show_context_menu(self, event):
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.selection_set(item)
        self.menu.tk_popup(event.x_root, event.y_root)

    def _build_contents(self):
        theme.header(self, "Project Tree").pack(fill="x")

        button_frame = tk.Frame(self, bg=self.bg_color)
        button_frame.pack(fill="x", padx=8, pady=8)
        theme.button(button_frame, "New File", self._create_file).pack(side="left", padx=(0, 6))
        theme.button(button_frame, "New Folder", self._create_folder).pack(side="left")

        tree_container = tk.Frame(self, bg=self.bg_color)
        tree_container.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        style = ttk.Style()
        style.configure("ProjectTreeview.Treeview", background=theme.PANEL,
                        fieldbackground=theme.PANEL, foreground=theme.TEXT,
                        font=theme.FONT, rowheight=26, borderwidth=0)
        style.map("ProjectTreeview.Treeview",
                  background=[("selected", theme.ACCENT)], foreground=[("selected", "white")])

        self.tree = ttk.Treeview(tree_container, show="tree", style="ProjectTreeview.Treeview")
        self.tree.pack(side="left", fill="both", expand=True)

        self.menu = tk.Menu(self, tearoff=0)
        self.menu.add_command(label="Open", command=self._open_selected)
        self.menu.add_command(label="New File", command=self._create_file)
        self.menu.add_command(label="New Folder", command=self._create_folder)
        self.menu.add_separator()
        self.menu.add_command(label="Rename", command=self._rename_item)
        self.menu.add_command(label="Delete", command=self._delete_item)

        self.tree.bind("<Button-3>", self._show_context_menu)
        self.tree.bind("<Double-Button-1>", self._on_double_click)

        scrollbar = tk.Scrollbar(tree_container, orient="vertical", command=self.tree.yview)
        scrollbar.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=scrollbar.set)

    def _open_selected(self):
        sel = self.tree.selection()
        if sel and self._get_type(sel[0]) == "file":
            self.on_open_file(self._node_path(sel[0]))

    def update_tree(self, nodes):
        # bangun ulang dari tree server, folder yang lagi kebuka biarin tetap kebuka
        expanded = self._expanded_paths()
        self.tree.delete(*self.tree.get_children(""))
        self._populate("", nodes or [])
        self._restore_expanded(expanded)

    def _populate(self, parent, nodes):
        for node in nodes:
            node_type = node.get("type", "file")
            node_id = self.tree.insert(parent, "end", text=node["name"],
                                       open=False, values=(node_type,))
            if node_type == "dir" and node.get("children"):
                self._populate(node_id, node["children"])

    def _expanded_paths(self):
        result = set()

        def walk(item):
            for child in self.tree.get_children(item):
                if self._get_type(child) == "dir" and self.tree.item(child, "open"):
                    result.add(self._node_path(child))
                walk(child)

        walk("")
        return result

    def _restore_expanded(self, expanded):
        def walk(item):
            for child in self.tree.get_children(item):
                if self._node_path(child) in expanded:
                    self.tree.item(child, open=True)
                walk(child)

        walk("")
