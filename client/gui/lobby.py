"""Layar lobby: lihat daftar project, bikin, masuk, atau hapus project."""

import tkinter as tk
from tkinter import messagebox, simpledialog

from shared.protocol import MessageType
from gui import theme


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
        self.configure(bg=theme.BG)

        header = tk.Frame(self, bg=theme.HEADER)
        header.pack(fill="x")
        tk.Label(header, text="Projects", font=theme.FONT_H, bg=theme.HEADER,
                 fg="white").pack(side="left", padx=14, pady=10)
        tk.Label(header, text=f"login sebagai {self.username}", font=theme.FONT_SM,
                 bg=theme.HEADER, fg="#cfd5e3").pack(side="right", padx=14)

        body = tk.Frame(self, bg=theme.BG)
        body.pack(fill="both", expand=True, padx=16, pady=(14, 8))

        project_frame = tk.Frame(body, bg=theme.BG)
        project_frame.pack(side="left", fill="both", expand=True)

        self.listbox = tk.Listbox(project_frame, font=theme.FONT, relief="flat", bd=0,
                                  bg=theme.PANEL, fg=theme.TEXT, highlightthickness=1,
                                  highlightbackground="#d7deef",
                                  selectbackground=theme.ACCENT, selectforeground="white",
                                  activestyle="none")
        self.listbox.pack(side="left", fill="both", expand=True)
        self.listbox.bind("<Double-Button-1>", lambda _: self._join())

        scrollbar = tk.Scrollbar(project_frame, command=self.listbox.yview)
        scrollbar.pack(side="right", fill="y")
        self.listbox.config(yscrollcommand=scrollbar.set)

        self.users_panel = tk.Frame(body, bg=theme.PANEL, padx=8, pady=8)

        tk.Label(self.users_panel, text="Users", font=theme.FONT_BOLD,
                 bg=theme.PANEL, fg=theme.TEXT).pack(pady=(0, 6), anchor="w")

        users_list_frame = tk.Frame(self.users_panel, bg=theme.PANEL)
        users_list_frame.pack(fill="both", expand=True)

        self.users_listbox = tk.Listbox(users_list_frame, width=22, font=theme.FONT,
                                        relief="flat", bd=0, bg=theme.PANEL, fg=theme.TEXT,
                                        highlightthickness=1, highlightbackground="#d7deef",
                                        selectbackground=theme.ACCENT, selectforeground="white",
                                        activestyle="none")
        self.users_listbox.pack(side="left", fill="both", expand=True)

        users_scrollbar = tk.Scrollbar(users_list_frame, command=self.users_listbox.yview)
        users_scrollbar.pack(side="right", fill="y")
        self.users_listbox.config(yscrollcommand=users_scrollbar.set)

        theme.button(self.users_panel, "Refresh Users", self._get_users).pack(fill="x", pady=(8, 0))

        buttons = tk.Frame(self, bg=theme.BG)
        buttons.pack(fill="x", padx=16, pady=(0, 14))
        theme.button(buttons, "Refresh", self._refresh).pack(side="left", padx=(0, 6))
        theme.button(buttons, "New Project", self._create, primary=True).pack(side="left", padx=6)
        theme.button(buttons, "Open", self._join, primary=True).pack(side="left", padx=6)
        theme.button(buttons, "Delete", self._delete).pack(side="left", padx=6)

        self.show_users_button = theme.button(buttons, "Show Users", self._toggle_users)
        self.show_users_button.pack(side="left", padx=6)

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
