"""Layar lobby: lihat daftar project, bikin, masuk, atau hapus project."""

import tkinter as tk
from tkinter import messagebox, simpledialog

from shared.protocol import MessageType


class LobbyFrame(tk.Frame):
    def __init__(self, parent, net, username, on_joined, **kwargs):
        super().__init__(parent, **kwargs)
        self.net = net
        self.username = username
        self.on_joined = on_joined
        self.users_panel = None
        self.users_visible = False
        self._build()
        self._register_handlers()
        self.net.send(MessageType.PROJECT_LIST)

    def _register_handlers(self):
        self.net.set_handlers({
            MessageType.PROJECT_LIST_RESULT: self._on_project_list,
            MessageType.SHOW_ALL_USERS_RESULT: self._on_users,
            MessageType.ACK: self._on_ack,
            MessageType.ERROR: self._on_error,
        })

    def _build(self):
        header = tk.Frame(self)
        header.pack(fill="x", padx=16, pady=12)
        tk.Label(header, text="Projects", font=(None, 16, "bold")).pack(side="left")
        tk.Label(header, text=f"Logged in as {self.username}", fg="#666").pack(side="right")

        body = tk.Frame(self)
        body.pack(fill="both", expand=True, padx=16, pady=(0, 8))

        project_frame = tk.Frame(body)
        project_frame.pack(side="left", fill="both", expand=True)

        self.listbox = tk.Listbox(project_frame, font=(None, 12))
        self.listbox.pack(side="left", fill="both", expand=True)
        self.listbox.bind("<Double-Button-1>", lambda e: self._join())

        scrollbar = tk.Scrollbar(project_frame, command=self.listbox.yview)
        scrollbar.pack(side="right", fill="y")
        self.listbox.config(yscrollcommand=scrollbar.set)

        self.users_panel = tk.Frame(body)

        tk.Label(
            self.users_panel,
            text="Users",
            font=(None, 14, "bold")
        ).pack(pady=(0, 8))

        users_list_frame = tk.Frame(self.users_panel)
        users_list_frame.pack(fill="both", expand=True)

        self.users_listbox = tk.Listbox(users_list_frame, width=25)
        self.users_listbox.pack(side="left", fill="both", expand=True)

        users_scrollbar = tk.Scrollbar(
            users_list_frame,
            command=self.users_listbox.yview
        )
        users_scrollbar.pack(side="right", fill="y")

        self.users_listbox.config(
            yscrollcommand=users_scrollbar.set
        )

        tk.Button(
            self.users_panel,
            text="Refresh Users",
            command=self._get_users
        ).pack(fill="x", pady=(8, 0))

        buttons = tk.Frame(self)
        buttons.pack(fill="x", padx=16, pady=12)

        tk.Button(buttons, text="Refresh", command=self._refresh).pack(side="left", padx=4)
        tk.Button(buttons, text="New Project", command=self._create).pack(side="left", padx=4)
        tk.Button(buttons, text="Open", command=self._join).pack(side="left", padx=4)
        tk.Button(buttons, text="Delete", command=self._delete).pack(side="left", padx=4)

        self.show_users_button = tk.Button(
            buttons,
            text="Show Users",
            command=self._toggle_users
        )
        self.show_users_button.pack(side="left", padx=4)

    def _refresh(self):
        self.net.send(MessageType.PROJECT_LIST)

    def _create(self):
        name = simpledialog.askstring("New Project", "Project name:", parent=self)
        if name:
            self.net.send(MessageType.CREATE_PROJECT, name=name.strip())

    def _selected(self):
        sel = self.listbox.curselection()
        return self.listbox.get(sel[0]) if sel else None

    def _join(self):
        name = self._selected()
        if not name:
            messagebox.showinfo("Open", "Select a project first", parent=self)
            return
        self.on_joined(name)

    def _delete(self):
        name = self._selected()
        if not name:
            return
        if messagebox.askyesno("Delete", f"Delete project '{name}'?", parent=self):
            self.net.send(MessageType.DELETE_PROJECT, room_id=name)

    def _on_project_list(self, message):
        self.listbox.delete(0, tk.END)
        for name in message.get("projects", []):
            self.listbox.insert(tk.END, name)

    def _on_users(self, message):
        self.users_listbox.delete(0, tk.END)
        for user in message.get("users", []):
            self.users_listbox.insert(tk.END, user)

    def _toggle_users(self):
        if self.users_visible:
            self.users_panel.pack_forget()
            self.users_visible = False
            self.show_users_button.config(text="Show Users")
            return

        self.users_panel.pack(side="right", fill="y", padx=(8, 0))
        self.users_visible = True
        self.show_users_button.config(text="Hide Users")
        self._get_users()

    def _get_users(self):
        self.net.send(MessageType.SHOW_ALL_USERS)

    def _on_ack(self, message):
        # abis create/delete, server otomatis kirim PROJECT_LIST_RESULT baru, jadi ga ngapa2in
        pass

    def _on_error(self, message):
        messagebox.showerror("Error", message.get("message", "Error"), parent=self)
