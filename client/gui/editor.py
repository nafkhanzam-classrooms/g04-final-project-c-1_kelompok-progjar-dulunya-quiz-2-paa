"""Editor teks kolaboratif (sisi client OT).

Ketikan kita di-diff sama "shadow" (copy text terakhir yang udah sinkron) buat dapetin 1 op insert/delete, terus dikirim sebagai EDIT. EDIT dari orang lain langsung diterapin ke widget. Posisi di jaringan pakai offset karakter, trus diubah ke format Tkinter "baris.kolom" lewat "1.0 + N chars".
"""

import tkinter as tk

from shared.protocol import MessageType
from gui import theme


class TextEditorFrame(tk.Frame):
    def __init__(self, parent, bg_color, net, room_id, **kwargs):
        super().__init__(parent, bg=bg_color, **kwargs)
        self.bg_color = bg_color
        self.net = net
        self.room_id = room_id

        self.current_path = None
        self._version = 0
        self._shadow = ""              # text terakhir yang udah sinkron sama _version
        self._applying_remote = False  # penanda biar edit dari server ga dikirim balik

        self._typing_active = False    # lagi ngasih tau "is typing" apa ga
        self._typing_after = None      # timer buat kirim is_typing=False

        self._build_contents()

    def _build_contents(self):
        self.header = theme.header(self, "No file open")
        self.header.pack(fill="x")

        editor_container = tk.Frame(self, bg=self.bg_color)
        editor_container.pack(fill="both", expand=True, padx=8, pady=8)

        mono = ("Consolas", 11)
        self.line_numbers = tk.Text(editor_container, width=4, padx=6, pady=6, bd=0,
                                    bg="#f1f3f9", fg=theme.MUTED, font=mono,
                                    state="disabled", takefocus=0)
        self.line_numbers.pack(side="left", fill="y")

        self.text_widget = tk.Text(editor_container, wrap="word", undo=True, state="disabled",
                                   bd=0, padx=8, pady=6, font=mono, fg=theme.TEXT,
                                   bg=theme.PANEL, insertbackground=theme.ACCENT,
                                   selectbackground="#cfe0ff")
        self.scrollbar = tk.Scrollbar(editor_container, command=self._on_scroll)
        self.text_widget.configure(yscrollcommand=self._on_text_scroll)

        self.scrollbar.pack(side="right", fill="y")
        self.text_widget.pack(side="left", fill="both", expand=True)

        self.text_widget.bind("<<Modified>>", self._on_text_changed)
        self._update_line_numbers()

    def open_file(self, path):
        self.current_path = path
        self.net.send(MessageType.FILE_OPEN, room_id=self.room_id, path=path)

    def load_content(self, message):
        # FILE_CONTENT: ganti isi editor sama versi dari server
        if message.get("path") != self.current_path:
            return
        self._version = message.get("version", 0)
        text = message.get("content", "")

        self._applying_remote = True
        self.text_widget.configure(state="normal")
        self.text_widget.delete("1.0", tk.END)
        self.text_widget.insert("1.0", text)
        self.text_widget.edit_modified(False)
        self._applying_remote = False

        self._shadow = self._get_text()
        self.header.config(text=f"{self.current_path}  (v{self._version})")
        self._update_line_numbers()

    def _get_text(self):
        return self.text_widget.get("1.0", "end-1c")

    def _index(self, offset):
        return self.text_widget.index(f"1.0 + {max(0, offset)} chars")

    def _on_text_changed(self, event=None):
        if not self.text_widget.edit_modified():
            return
        self.text_widget.edit_modified(False)   # ini mancing <<Modified>> lagi, tp udah dijaga di atas
        self._update_line_numbers()

        if self._applying_remote or self.current_path is None:
            self._shadow = self._get_text()
            return

        current = self._get_text()
        if current == self._shadow:
            return
        self._emit_diff(self._shadow, current)
        self._shadow = current
        self._signal_typing()

    def _signal_typing(self):
        # kirim TYPING(True) sekali aja, baru TYPING(False) setelah berhenti ~1.2 detik, daripada ngirim tiap ketik satu huruf
        if self.current_path is None:
            return
        if not self._typing_active:
            self._typing_active = True
            self.net.send(MessageType.TYPING, room_id=self.room_id,
                          user_id=self.net.username, is_typing=True)
        if self._typing_after is not None:
            self.after_cancel(self._typing_after)
        self._typing_after = self.after(1200, self._stop_typing)

    def _stop_typing(self):
        self._typing_after = None
        if self._typing_active:
            self._typing_active = False
            self.net.send(MessageType.TYPING, room_id=self.room_id,
                          user_id=self.net.username, is_typing=False)

    def _emit_diff(self, old, new):
        # cari bagian yang berubah pakai prefix + suffix yang sama
        p = 0
        limit = min(len(old), len(new))
        while p < limit and old[p] == new[p]:
            p += 1
        s = 0
        while s < (len(old) - p) and s < (len(new) - p) and old[-1 - s] == new[-1 - s]:
            s += 1

        deleted = old[p: len(old) - s]
        inserted = new[p: len(new) - s]

        if deleted:
            self.net.send(MessageType.EDIT, room_id=self.room_id, path=self.current_path,
                          user_id=self.net.username, operation="delete",
                          positionS=p, positionE=p + len(deleted), content="",
                          version=self._version)
        if inserted:
            self.net.send(MessageType.EDIT, room_id=self.room_id, path=self.current_path,
                          user_id=self.net.username, operation="insert",
                          positionS=p, positionE=p, content=inserted,
                          version=self._version)

    def apply_remote(self, message):
        if message.get("path") != self.current_path:
            return
        op = message.get("operation")
        pos = int(message.get("position", 0))

        self._applying_remote = True
        self.text_widget.configure(state="normal")
        if op == "insert":
            self.text_widget.insert(self._index(pos), message.get("content", ""))
        elif op == "delete":
            length = int(message.get("length", 0))
            self.text_widget.delete(self._index(pos), self._index(pos + length))
        self.text_widget.edit_modified(False)
        self._applying_remote = False

        self._shadow = self._get_text()
        self._version = message.get("version", self._version)
        self.header.config(text=f"{self.current_path}  (v{self._version})")
        self._update_line_numbers()

    def on_ack(self, message):
        # ACK buat EDIT kita => naikin pointer versi
        if message.get("ref") == MessageType.EDIT and "version" in message:
            self._version = message["version"]
            self.header.config(text=f"{self.current_path}  (v{self._version})")

    def on_file_removed(self, path):
        # file yang lagi dibuka dihapus/di-rename orang lain
        if path == self.current_path:
            self.current_path = None
            self._applying_remote = True
            self.text_widget.delete("1.0", tk.END)
            self.text_widget.configure(state="disabled")
            self.text_widget.edit_modified(False)
            self._applying_remote = False
            self._shadow = ""
            self.header.config(text="No file open")
            self._update_line_numbers()

    def _on_scroll(self, *args):
        self.text_widget.yview(*args)
        self.line_numbers.yview(*args)

    def _on_text_scroll(self, *args):
        self.scrollbar.set(*args)
        if args:
            self.line_numbers.yview_moveto(args[0])

    def _update_line_numbers(self):
        line_count = int(self.text_widget.index("end-1c").split(".")[0])
        numbers = "\n".join(str(i) for i in range(1, line_count + 1))
        self.line_numbers.configure(state="normal")
        self.line_numbers.delete("1.0", tk.END)
        self.line_numbers.insert("1.0", numbers)
        self.line_numbers.configure(state="disabled")
