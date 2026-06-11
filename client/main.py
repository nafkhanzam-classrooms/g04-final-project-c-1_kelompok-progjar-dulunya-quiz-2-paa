"""Titik masuk client. Jalanin dari root project: python -m client.main
Pakai 1 root Tk yang gantian nampilin Login => Lobby => Editor, dan tiap 50 ms ngecek inbox jaringan biar update GUI tetap di main thread."""

import os
import sys
import tkinter as tk

# biar root project + folder client kebaca, dua cara jalanin sama-sama bisa
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_THIS_DIR)
for _p in (_ROOT, _THIS_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from client.network.net_client import NetClient
from gui import theme
from gui.login import LoginFrame
from gui.lobby import LobbyFrame
from gui.main_window import EditorScreen


class App:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Collaborative Editor")
        self.root.geometry("1280x760")
        self.root.configure(bg=theme.BG)
        self.root.protocol("WM_DELETE_WINDOW", self._quit)

        self.net = NetClient()
        self.username = None
        self.current_frame = None

        self._show_login()
        self.root.after(50, self._pump)

    def _swap(self, frame):
        if self.current_frame is not None:
            self.current_frame.destroy()
        self.current_frame = frame
        frame.pack(fill="both", expand=True)

    def _show_login(self):
        self._swap(LoginFrame(self.root, self.net, on_logged_in=self._on_logged_in))

    def _on_logged_in(self, username):
        self.username = username
        self.root.title(f"Collaborative Editor — {username}")
        self._show_lobby()

    def _show_lobby(self):
        self._swap(LobbyFrame(self.root, self.net, self.username, on_joined=self._on_joined))

    def _on_joined(self, room_id):
        from shared.protocol import MessageType
        # bikin layar editor dulu (biar handler-nya kepasang) baru kirim JOIN, biar balasan JOIN-nya ga kelewat
        self._swap(EditorScreen(self.root, self.net, room_id, on_leave=self._show_lobby))
        self.net.send(MessageType.JOIN_PROJECT, room_id=room_id)

    def _pump(self):
        self.net.pump()
        self.root.after(50, self._pump)

    def _quit(self):
        self.net.close()
        self.root.destroy()

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    App().run()
