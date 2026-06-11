"""Tes integrasi: widget GUI client beneran lawan server beneran, plus 1 peer pakai socket biasa, buat ngecek sinkron dua arah (edit, chat, private chat, typing, reaction). Jalanin: python -m tools test_gui_integration"""

import os
import socket
import sys
import tempfile
import threading
import time
import tkinter as tk

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)
sys.path.insert(0, os.path.join(_ROOT, "client"))  # biar package `gui` kebaca

from shared.protocol import MessageType, msg, StreamDecoder
from server.core.controller import ServerController
from client.network.net_client import NetClient
from gui.main_window import EditorScreen

HOST, PORT = "127.0.0.1", 8898

PASS = "\033[92mPASS\033[0m"
FAIL = "\033[91mFAIL\033[0m"
_failures = 0


def check(label, cond):
    global _failures
    print(f"  [{PASS if cond else FAIL}] {label}")
    if not cond:
        _failures += 1


class RawPeer:
    """Client socket sederhana yang jadi pengganti user kedua."""

    def __init__(self):
        self.sock = socket.create_connection((HOST, PORT))
        self.sock.settimeout(0.1)
        self._dec = StreamDecoder()
        self.inbox = []

    def send(self, ptype, **f):
        self.sock.sendall(msg(ptype, **f))

    def pump(self):
        try:
            data = self.sock.recv(4096)
            if data:
                self.inbox.extend(self._dec.feed(data))
        except socket.timeout:
            pass

    def wait_for(self, ptype, timeout=3.0):
        end = time.time() + timeout
        while time.time() < end:
            for i, m in enumerate(self.inbox):
                if m.get("packet_type") == ptype:
                    return self.inbox.pop(i)
            self.pump()
        return None

    def close(self):
        self.sock.close()


def main():
    storage = tempfile.mkdtemp(prefix="collab_gui_")
    controller = ServerController(host=HOST, port=PORT, storage_root=storage,
                                  chat_file=os.path.join(storage, "chats.json"))
    threading.Thread(target=controller.start, daemon=True).start()
    time.sleep(0.4)

    root = tk.Tk()
    root.withdraw()
    gui = NetClient()
    gui.username = "gui_user"

    def pump_gui(times=25, delay=0.02):
        for _ in range(times):
            gui.pump()
            root.update()
            time.sleep(delay)

    try:
        print("== GUI client connects & authenticates ==")
        gui.connect(HOST, PORT)
        authed = {"ok": None}
        gui.set_handlers({MessageType.AUTH_RESULT: lambda m: authed.update(ok=m.get("ok"))})
        gui.send(MessageType.AUTH, username="gui_user")
        pump_gui()
        check("GUI authenticated", authed["ok"] is True)

        print("== Create & join project (build real EditorScreen) ==")
        gui.send(MessageType.CREATE_PROJECT, name="demo")
        pump_gui()
        screen = EditorScreen(root, gui, "demo", on_leave=lambda: None)
        gui.send(MessageType.JOIN_PROJECT, room_id="demo")
        pump_gui()

        print("== Create a file via the tree, open it in the editor ==")
        gui.send(MessageType.FILE_SYSTEM, room_id="demo", operation="CREATE_FILE", path="notes.txt")
        pump_gui()
        tree_names = screen.tree_panel.tree.get_children("")
        check("file appears in GUI tree",
              any(screen.tree_panel.tree.item(i, "text") == "notes.txt" for i in tree_names))

        screen.editor_panel.open_file("notes.txt")
        pump_gui()
        check("editor opened empty file", screen.editor_panel._get_text() == "")

        print("== Peer joins & opens same file ==")
        peer = RawPeer()
        peer.send(MessageType.AUTH, username="peer"); peer.wait_for(MessageType.AUTH_RESULT)
        peer.send(MessageType.JOIN_PROJECT, room_id="demo"); peer.wait_for(MessageType.ACK)
        peer.send(MessageType.FILE_OPEN, room_id="demo", path="notes.txt")
        check("peer opens empty file", peer.wait_for(MessageType.FILE_CONTENT) is not None)

        print("== GUI types 'Hello' -> propagates to server & peer ==")
        ed = screen.editor_panel
        ed.text_widget.insert("1.0", "Hello")
        ed._on_text_changed()   # niruin event <<Modified>> kepicu
        pump_gui()
        doc = controller.ot_engine.get_document("demo", "notes.txt")
        check("server stored 'Hello'", doc.text == "Hello")
        edit = peer.wait_for(MessageType.EDIT)
        check("peer received the EDIT", edit and edit.get("content") == "Hello")

        print("== Peer inserts 'World' -> GUI editor applies it (OT) ==")
        peer.send(MessageType.EDIT, room_id="demo", path="notes.txt", user_id="peer",
                  operation="insert", positionS=0, positionE=0, content="World", version=0)
        pump_gui()
        gui_text = ed._get_text()
        check("GUI editor converged with peer edit", "World" in gui_text and "Hello" in gui_text)
        check("GUI text matches server", gui_text == controller.ot_engine.get_document("demo", "notes.txt").text)
        print(f"      GUI editor text = {gui_text!r}")

        print("== Chat both directions ==")
        screen.chat_panel.message_entry.insert(0, "hi from gui")
        screen.chat_panel._send_message()
        pump_gui()
        c = peer.wait_for(MessageType.CHAT)
        check("peer received GUI chat", c and c.get("message") == "hi from gui")

        peer.send(MessageType.CHAT, room_id="demo", sender_id="peer", message="hi from peer")
        pump_gui()
        shown = screen.chat_panel.chat_display.get("1.0", "end-1c")
        check("GUI chat shows peer message", "hi from peer" in shown)

        print("== Typing indicator both directions ==")
        # GUI tadi udah ngetik, jadi otomatis ngirim TYPING(True) ke peer
        check("peer received GUI typing", peer.wait_for(MessageType.TYPING) is not None)

        peer.send(MessageType.TYPING, room_id="demo", user_id="peer", is_typing=True)
        pump_gui()
        check("GUI shows 'peer sedang mengetik'",
              "peer" in screen.chat_panel.typing_label.cget("text"))

        peer.send(MessageType.TYPING, room_id="demo", user_id="peer", is_typing=False)
        pump_gui()
        check("GUI clears typing indicator", screen.chat_panel.typing_label.cget("text") == "")

        print("== Private chat both directions ==")
        # GUI kirim DM ke peer (penerima dipilih lewat dropdown)
        screen.chat_panel.recipient_var.set("peer")
        screen.chat_panel.message_entry.insert(0, "secret to peer")
        screen.chat_panel._send_message()
        pump_gui()
        pm = peer.wait_for(MessageType.PRIVATE_CHAT)
        check("peer received private message",
              pm and pm.get("message") == "secret to peer" and pm.get("sender_id") == "gui_user")
        shown = screen.chat_panel.chat_display.get("1.0", "end-1c")
        check("GUI shows its own outgoing DM", "secret to peer" in shown and "PM to peer" in shown)

        # peer balas DM ke user GUI
        peer.send(MessageType.PRIVATE_CHAT, room_id="demo", sender_id="peer",
                  target_id="gui_user", message="psst hi")
        pump_gui()
        shown = screen.chat_panel.chat_display.get("1.0", "end-1c")
        check("GUI shows incoming DM from peer", "psst hi" in shown and "PM from peer" in shown)

        # DM ke user yang ga ada harusnya balikin ERROR
        peer.send(MessageType.PRIVATE_CHAT, room_id="demo", sender_id="peer",
                  target_id="ghost", message="anyone?")
        err = peer.wait_for(MessageType.ERROR)
        check("DM to offline user returns error", err and err.get("code") == "NO_USER")

        print("== Reactions ==")
        # peer kirim chat biasa biar GUI punya pesan ber-id buat dikasih reaksi
        peer.send(MessageType.CHAT, room_id="demo", sender_id="peer", message="react to me")
        pump_gui()
        target_id = screen.chat_panel._last_chat_id()
        check("GUI tracked a chat message id", bool(target_id))
        # GUI ngasih reaksi ke pesan itu
        screen.chat_panel._react("👍")
        pump_gui()
        ru = peer.wait_for(MessageType.REACTION_UPDATE)
        check("peer receives reaction update",
              ru and "👍" in ru.get("reactions", {}) and "gui_user" in ru["reactions"]["👍"])
        shown = screen.chat_panel.chat_display.get("1.0", "end-1c")
        check("GUI renders the reaction", "👍" in shown)

        peer.close()
    finally:
        gui.close()
        root.destroy()
        controller.stop()

    print()
    print("ALL CHECKS PASSED" if _failures == 0 else f"{_failures} CHECK(S) FAILED")
    sys.exit(1 if _failures else 0)


if __name__ == "__main__":
    main()
