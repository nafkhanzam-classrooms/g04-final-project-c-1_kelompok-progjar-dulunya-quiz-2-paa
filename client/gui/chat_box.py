import tkinter as tk

class ChatFrame(tk.Frame):
    def __init__(self, parent, bg_color, chats, **kwargs):
        super().__init__(parent, bg=bg_color, **kwargs)
        self.bg_color = bg_color
        self.chats = chats or []
        self._build_contents()
        self._refresh_chat_view()

    def _build_contents(self):
        header = tk.Label(self, text="Chat", bg=self.bg_color, font=(None, 12, "bold"))
        header.pack(fill="x", padx=8, pady=(8, 4))

        chat_container = tk.Frame(self)
        chat_container.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        self.chat_display = tk.Text(chat_container, wrap="word", state="disabled", bg="#f5f5ff")
        self.chat_scrollbar = tk.Scrollbar(chat_container, command=self.chat_display.yview)
        self.chat_display.configure(yscrollcommand=self.chat_scrollbar.set)

        self.chat_scrollbar.pack(side="right", fill="y")
        self.chat_display.pack(side="left", fill="both", expand=True)

        input_frame = tk.Frame(self)
        input_frame.pack(fill="x", padx=8, pady=(0, 8))

        self.message_entry = tk.Entry(input_frame)
        self.message_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.message_entry.bind("<Return>", lambda event: self._send_message())

        send_button = tk.Button(input_frame, text="Send", command=self._send_message)
        send_button.pack(side="right")

    def _refresh_chat_view(self):
        self.chat_display.configure(state="normal")
        self.chat_display.delete("1.0", tk.END)

        for chat in self.chats:
            message = f"[{chat['timestamp']}] {chat['name']}: {chat['content']}\n"
            self.chat_display.insert(tk.END, message)

        self.chat_display.configure(state="disabled")
        self.chat_display.see(tk.END)

    def _send_message(self):
        content = self.message_entry.get().strip()
        if not content:
            return

        timestamp = __import__("datetime").datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        new_chat = {"name": "You", "timestamp": timestamp, "content": content}
        self.chats.append(new_chat)
        self.message_entry.delete(0, tk.END)
        self._refresh_chat_view()
