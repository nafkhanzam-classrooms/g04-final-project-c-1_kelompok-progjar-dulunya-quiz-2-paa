import tkinter as tk

class TextEditorFrame(tk.Frame):
    def __init__(self, parent, bg_color, initial_text="", **kwargs):
        super().__init__(parent, bg=bg_color, **kwargs)
        self.bg_color = bg_color
        self._build_contents(initial_text)

    def _build_contents(self, initial_text):
        header = tk.Label(self, text="Text Editor", bg=self.bg_color, font=(None, 12, "bold"))
        header.pack(fill="x", padx=8, pady=(8, 4))
        
        editor_container = tk.Frame(self)
        editor_container.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        self.line_numbers = tk.Text(
            editor_container,
            width=4,
            padx=4,
            pady=4,
            bd=0,
            bg="#ececec",
            fg="#555555",
            state="disabled",
            takefocus=0,
        )
        self.line_numbers.pack(side="left", fill="y")

        self.text_widget = tk.Text(editor_container, wrap="word", undo=True)
        self.scrollbar = tk.Scrollbar(editor_container, command=self._on_scroll)
        self.text_widget.configure(yscrollcommand=self._on_text_scroll)

        self.scrollbar.pack(side="right", fill="y")
        self.text_widget.pack(side="left", fill="both", expand=True)

        self.text_widget.bind("<<Modified>>", self._on_text_changed)

        if initial_text:
            self.text_widget.insert("1.0", initial_text)

        self._update_line_numbers()
        self.text_widget.edit_modified(False)

    def _on_scroll(self, *args):
        self.text_widget.yview(*args)
        self.line_numbers.yview(*args)

    def _on_text_scroll(self, *args):
        self.scrollbar.set(*args)
        if args:
            self.line_numbers.yview_moveto(args[0])

    def _on_text_changed(self, event=None):
        if self.text_widget.edit_modified():
            self._update_line_numbers()
            self.text_widget.edit_modified(False)

    def _update_line_numbers(self):
        line_count = int(self.text_widget.index("end-1c").split(".")[0])
        line_numbers = "\n".join(str(i) for i in range(1, line_count + 1))
        self.line_numbers.configure(state="normal")
        self.line_numbers.delete("1.0", tk.END)
        self.line_numbers.insert("1.0", line_numbers)
        self.line_numbers.configure(state="disabled")