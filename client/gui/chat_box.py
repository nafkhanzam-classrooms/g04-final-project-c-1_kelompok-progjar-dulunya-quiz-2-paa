import tkinter as tk

from shared.protocol import MessageType
from gui import theme

EVERYONE = "Everyone"
EMOJIS = ["👍", "❤️", "😂", "🎉", "🔥", "😮", "😢"]


class ChatFrame(tk.Frame):
    def __init__(self, parent, bg_color, net, room_id, **kwargs):
        super().__init__(parent, bg=bg_color, **kwargs)
        self.bg_color = bg_color
        self.net = net
        self.room_id = room_id

        self._messages = [] # daftar pesan yang ditampilin
        self._members = []
        self._selected_id = None    # pesan yang dipilih buat dikasih reaksi

        self._typing_active = False # lagi ngasih tau kita ngetik apa ga
        self._typing_send_after = None  # timer buat kirim is_typing=False
        self._typing_seen = {}  # orang lain yang lagi ngetik => timer buat ngehapus

        self._build()

    def _build(self):
        theme.header(self, "Chat").pack(fill="x")

        self.members_label = tk.Label(self, text="Members: -", bg=self.bg_color,
                                      fg=theme.MUTED, anchor="w", font=theme.FONT_SM)
        self.members_label.pack(fill="x", padx=10, pady=(6, 0))

        box = tk.Frame(self, bg=self.bg_color)
        box.pack(fill="both", expand=True, padx=8, pady=6)
        self.chat_display = tk.Text(box, wrap="word", state="disabled", bd=0, padx=8, pady=6,
                                    font=theme.FONT, bg="#f7f9fd", fg=theme.TEXT)
        scroll = tk.Scrollbar(box, command=self.chat_display.yview)
        self.chat_display.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        self.chat_display.pack(side="left", fill="both", expand=True)
        self.chat_display.bind("<Button-1>", self._on_pick_message)

        self.typing_label = tk.Label(self, text="", bg=self.bg_color, fg="#2a9d6e",
                                     anchor="w", font=(theme.FONT_SM[0], 9, "italic"))
        self.typing_label.pack(fill="x", padx=10)

        react_bar = tk.Frame(self, bg=self.bg_color)
        react_bar.pack(fill="x", padx=8)
        tk.Label(react_bar, text="React:", bg=self.bg_color, fg=theme.MUTED,
                 font=theme.FONT_SM).pack(side="left")
        for e in EMOJIS:
            tk.Button(react_bar, text=e, width=2, relief="flat", bd=0, bg=self.bg_color,
                      activebackground="#e7ecf8", cursor="hand2",
                      command=lambda em=e: self._react(em)).pack(side="left")

        to_row = tk.Frame(self, bg=self.bg_color)
        to_row.pack(fill="x", padx=10, pady=(4, 0))
        tk.Label(to_row, text="To:", bg=self.bg_color, fg=theme.TEXT,
                 font=theme.FONT_SM).pack(side="left")
        self.recipient_var = tk.StringVar(value=EVERYONE)
        self.recipient_menu = tk.OptionMenu(to_row, self.recipient_var, EVERYONE)
        self.recipient_menu.config(width=14, font=theme.FONT_SM, relief="flat",
                                   bg=theme.ACCENT2, activebackground="#d7deef",
                                   highlightthickness=0, cursor="hand2")
        self.recipient_menu.pack(side="left", padx=(4, 0))

        in_row = tk.Frame(self, bg=self.bg_color)
        in_row.pack(fill="x", padx=8, pady=8)
        self.emoji_btn = tk.Menubutton(in_row, text="😀", relief="flat", bd=0,
                                       bg=self.bg_color, activebackground="#e7ecf8", cursor="hand2")
        self.emoji_btn.pack(side="left", padx=(0, 4))
        emoji_menu = tk.Menu(self.emoji_btn, tearoff=0)
        for e in EMOJIS:
            emoji_menu.add_command(label=e, command=lambda em=e: self._insert_emoji(em))
        self.emoji_btn.config(menu=emoji_menu)

        self.message_entry = theme.entry(in_row)
        self.message_entry.pack(side="left", fill="x", expand=True, padx=(0, 8), ipady=3)
        self.message_entry.bind("<Return>", lambda e: self._send_message())
        self.message_entry.bind("<KeyRelease>", self._on_keyrelease)
        theme.button(in_row, "Send", self._send_message, primary=True).pack(side="right")

    # kirim
    def _send_message(self):
        content = self.message_entry.get().strip()
        if not content:
            return
        recipient = self.recipient_var.get()
        if recipient and recipient != EVERYONE:
            self.net.send(MessageType.PRIVATE_CHAT, room_id=self.room_id,
                          sender_id=self.net.username, target_id=recipient, message=content)
        else:
            self.net.send(MessageType.CHAT, room_id=self.room_id,
                          sender_id=self.net.username, message=content)
        self.message_entry.delete(0, tk.END)
        self._stop_typing()

    def _insert_emoji(self, emoji):
        self.message_entry.insert(tk.INSERT, emoji)
        self.message_entry.focus_set()

    def _react(self, emoji):
        mid = self._selected_id or self._last_chat_id()
        if mid:
            self.net.send(MessageType.REACTION, room_id=self.room_id,
                          message_id=mid, emoji=emoji)

    def _last_chat_id(self):
        for m in reversed(self._messages):
            if m.get("kind") == "chat" and m.get("id"):
                return m["id"]
        return None

    # typing (yang kita kirim)
    def _on_keyrelease(self, event):
        if event.keysym in ("Return", "Tab"):
            return
        if not self._typing_active:
            self._typing_active = True
            self.net.send(MessageType.TYPING, room_id=self.room_id,
                          user_id=self.net.username, is_typing=True)
        if self._typing_send_after is not None:
            self.after_cancel(self._typing_send_after)
        self._typing_send_after = self.after(1200, self._stop_typing)

    def _stop_typing(self):
        if self._typing_send_after is not None:
            self.after_cancel(self._typing_send_after)
            self._typing_send_after = None
        if self._typing_active:
            self._typing_active = False
            self.net.send(MessageType.TYPING, room_id=self.room_id,
                          user_id=self.net.username, is_typing=False)

    # yang masuk dari server
    def add_message(self, message):
        self._messages.append({
            "kind": "chat",
            "id": message.get("id"),
            "sender_id": message.get("sender_id", "?"),
            "message": message.get("message", ""),
            "timestamp": message.get("timestamp", ""),
            "reactions": message.get("reactions") or {},
        })
        self._render()

    def add_private_message(self, message):
        self._messages.append({
            "kind": "pm",
            "sender_id": message.get("sender_id", "?"),
            "target_id": message.get("target_id", "?"),
            "message": message.get("message", ""),
            "timestamp": message.get("timestamp", ""),
        })
        self._render()

    def load_history(self, message):
        self._messages = [{
            "kind": "chat",
            "id": e.get("id"),
            "sender_id": e.get("sender_id", "?"),
            "message": e.get("message", ""),
            "timestamp": e.get("timestamp", ""),
            "reactions": e.get("reactions") or {},
        } for e in message.get("messages", [])]
        self._render()

    def update_reaction(self, message):
        mid = message.get("message_id")
        for m in self._messages:
            if m.get("id") == mid:
                m["reactions"] = message.get("reactions") or {}
                break
        self._render()

    def update_presence(self, message):
        self._members = message.get("members", [])
        self.members_label.config(
            text="Members: " + (", ".join(self._members) if self._members else "-"))
        self._rebuild_recipient_menu()

    def update_typing(self, message):
        user = message.get("user_id")
        if not user:
            return
        if user in self._typing_seen:
            self.after_cancel(self._typing_seen.pop(user))
        if message.get("is_typing"):
            self._typing_seen[user] = self.after(3000, lambda u=user: self._clear_typing(u))
        self._refresh_typing_label()

    def _clear_typing(self, user):
        self._typing_seen.pop(user, None)
        self._refresh_typing_label()

    def _refresh_typing_label(self):
        users = list(self._typing_seen.keys())
        if not users:
            text = ""
        elif len(users) == 1:
            text = f"{users[0]} sedang mengetik..."
        else:
            text = f"{', '.join(users)} sedang mengetik..."
        self.typing_label.config(text=text)

    # tampilan
    def _on_pick_message(self, event):
        idx = self.chat_display.index(f"@{event.x},{event.y}")
        for tag in self.chat_display.tag_names(idx):
            if tag.startswith("m:"):
                self._selected_id = tag[2:]
                self._render()
                return

    def _rebuild_recipient_menu(self):
        others = [m for m in self._members if m != self.net.username]
        current = self.recipient_var.get()
        menu = self.recipient_menu["menu"]
        menu.delete(0, "end")
        for option in [EVERYONE] + others:
            menu.add_command(label=option, command=lambda v=option: self.recipient_var.set(v))
        if current != EVERYONE and current not in others:
            self.recipient_var.set(EVERYONE)

    def _render(self):
        self.chat_display.configure(state="normal")
        self.chat_display.delete("1.0", tk.END)
        for m in self._messages:
            kind = m.get("kind")
            ts = m.get("timestamp", "")
            if kind == "pm":
                if m["sender_id"] == self.net.username:
                    self.chat_display.insert(tk.END, f"[{ts}] [PM to {m['target_id']}] you: {m['message']}\n")
                else:
                    self.chat_display.insert(tk.END, f"[{ts}] [PM from {m['sender_id']}] {m['message']}\n")
                continue

            mid = m.get("id")
            tag = f"m:{mid}" if mid else None
            start = self.chat_display.index("end-1c")
            self.chat_display.insert(tk.END, f"[{ts}] {m['sender_id']}: {m['message']}\n")
            reactions = m.get("reactions") or {}
            if reactions:
                summary = "   " + "  ".join(f"{e} {len(u)}" for e, u in reactions.items())
                self.chat_display.insert(tk.END, summary + "\n")
            if tag:
                self.chat_display.tag_add(tag, start, self.chat_display.index("end-1c"))
                if mid == self._selected_id:
                    self.chat_display.tag_config(tag, background="#d7e6ff")
        self.chat_display.configure(state="disabled")
        self.chat_display.see(tk.END)
