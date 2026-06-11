"""Layar login: konek ke server terus masuk pakai username."""

import tkinter as tk

from shared.protocol import MessageType


class LoginFrame(tk.Frame):
    def __init__(self, parent, net, on_logged_in, **kwargs):
        super().__init__(parent, **kwargs)
        self.net = net
        self.on_logged_in = on_logged_in
        self._build()

    def _build(self):
        wrapper = tk.Frame(self)
        wrapper.place(relx=0.5, rely=0.5, anchor="center")

        tk.Label(wrapper, text="Collaborative Editor", font=(None, 20, "bold")).grid(
            row=0, column=0, columnspan=2, pady=(0, 20))

        tk.Label(wrapper, text="Server host:").grid(row=1, column=0, sticky="e", pady=4)
        self.host_entry = tk.Entry(wrapper)
        self.host_entry.insert(0, "127.0.0.1")
        self.host_entry.grid(row=1, column=1, pady=4)

        tk.Label(wrapper, text="Port:").grid(row=2, column=0, sticky="e", pady=4)
        self.port_entry = tk.Entry(wrapper)
        self.port_entry.insert(0, "8888")
        self.port_entry.grid(row=2, column=1, pady=4)

        tk.Label(wrapper, text="Username:").grid(row=3, column=0, sticky="e", pady=4)
        self.user_entry = tk.Entry(wrapper)
        self.user_entry.grid(row=3, column=1, pady=4)
        self.user_entry.bind("<Return>", lambda e: self._connect())

        self.connect_btn = tk.Button(wrapper, text="Connect", width=20, command=self._connect)
        self.connect_btn.grid(row=4, column=0, columnspan=2, pady=(16, 0))

        self.status = tk.Label(wrapper, text="", fg="red")
        self.status.grid(row=5, column=0, columnspan=2, pady=(8, 0))

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

        self.status.config(text="Connecting...", fg="black")
        self.connect_btn.config(state="disabled")
        self.update_idletasks()

        try:
            self.net.connect(host, port)
        except OSError as exc:
            self.status.config(text=f"Cannot connect: {exc}", fg="red")
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
            self.status.config(text=message.get("message", "Auth failed"), fg="red")
            self.connect_btn.config(state="normal")

    def _on_disconnect(self):
        self.status.config(text="Disconnected from server", fg="red")
        self.connect_btn.config(state="normal")
