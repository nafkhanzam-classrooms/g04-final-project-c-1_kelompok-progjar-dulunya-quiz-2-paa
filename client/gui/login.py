"""Layar login: konek ke server terus masuk pakai username."""

import tkinter as tk

from shared.protocol import MessageType
from gui import theme


class LoginFrame(tk.Frame):
    def __init__(self, parent, net, on_logged_in, **kwargs):
        super().__init__(parent, bg=theme.BG, **kwargs)
        self.net = net
        self.on_logged_in = on_logged_in
        self._build()

    def _build(self):
        card = tk.Frame(self, bg=theme.PANEL, padx=34, pady=28)
        card.place(relx=0.5, rely=0.5, anchor="center")

        tk.Label(card, text="Collaborative Editor", font=theme.FONT_TITLE,
                 bg=theme.PANEL, fg=theme.TEXT).grid(row=0, column=0, columnspan=2)
        tk.Label(card, text="masuk dulu buat mulai kolaborasi", font=theme.FONT_SM,
                 bg=theme.PANEL, fg=theme.MUTED).grid(row=1, column=0, columnspan=2, pady=(2, 20))

        def field(row, label, default=""):
            tk.Label(card, text=label, font=theme.FONT, bg=theme.PANEL, fg=theme.TEXT).grid(
                row=row, column=0, sticky="e", padx=(0, 10), pady=6)
            e = theme.entry(card, width=22)
            if default:
                e.insert(0, default)
            e.grid(row=row, column=1, pady=6, ipady=4)
            return e

        self.host_entry = field(2, "Server host:", "127.0.0.1")
        self.port_entry = field(3, "Port:", "8888")
        self.user_entry = field(4, "Username:")
        self.user_entry.bind("<Return>", lambda e: self._connect())

        self.connect_btn = theme.button(card, "Connect", self._connect, primary=True)
        self.connect_btn.grid(row=5, column=0, columnspan=2, pady=(20, 0), sticky="ew", ipady=2)

        self.status = tk.Label(card, text="", fg=theme.DANGER, bg=theme.PANEL, font=theme.FONT_SM)
        self.status.grid(row=6, column=0, columnspan=2, pady=(10, 0))

        self.user_entry.focus_set()

    def _connect(self):
        host = self.host_entry.get().strip()
        username = self.user_entry.get().strip()
        try:
            port = int(self.port_entry.get().strip())
        except ValueError:
            self.status.config(text="Port must be a number")
            return
        if not username:
            self.status.config(text="Username required")
            return

        self.status.config(text="Connecting...", fg=theme.MUTED)
        self.connect_btn.config(state="disabled")
        self.update_idletasks()

        try:
            self.net.connect(host, port)
        except OSError as exc:
            self.status.config(text=f"Cannot connect: {exc}", fg=theme.DANGER)
            self.connect_btn.config(state="normal")
            return

        # tunggu balasan AUTH_RESULT lewat handler
        self.net.set_handlers(
            {MessageType.AUTH_RESULT: self._on_auth_result},
            on_disconnect=self._on_disconnect,
        )
        self.net.username = username
        self.net.send(MessageType.AUTH, username=username)

    def _on_auth_result(self, message):
        if message.get("ok"):
            self.on_logged_in(self.net.username)
        else:
            self.status.config(text=message.get("message", "Auth failed"), fg=theme.DANGER)
            self.connect_btn.config(state="normal")

    def _on_disconnect(self):
        self.status.config(text="Disconnected from server", fg=theme.DANGER)
        self.connect_btn.config(state="normal")
