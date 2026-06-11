# warna & font biar tampilan antar-layar konsisten
import tkinter as tk

FONT       = ("Segoe UI", 10)
FONT_SM    = ("Segoe UI", 9)
FONT_BOLD  = ("Segoe UI", 10, "bold")
FONT_H     = ("Segoe UI", 12, "bold")
FONT_TITLE = ("Segoe UI", 18, "bold")

BG      = "#eef1f7"   # background app
PANEL   = "#ffffff"   # isi panel
HEADER  = "#3b4252"   # bar header (gelap)
ACCENT  = "#5b8def"   # warna utama (tombol penting)
ACCENT2 = "#e7ecf8"   # tombol biasa
TEXT    = "#2e3440"
MUTED   = "#8a90a0"
DANGER  = "#d9534f"


def button(parent, text, command, primary=False, **kw):
    if primary:
        bg, fg, active = ACCENT, "white", "#4a7be0"
    else:
        bg, fg, active = ACCENT2, TEXT, "#d7deef"
    return tk.Button(parent, text=text, command=command, font=FONT,
                     bg=bg, fg=fg, activebackground=active, activeforeground=fg,
                     relief="flat", bd=0, padx=12, pady=5, cursor="hand2", **kw)


def header(parent, text):
    return tk.Label(parent, text=text, bg=HEADER, fg="white",
                    font=FONT_H, anchor="w", padx=10, pady=8)


def entry(parent, **kw):
    return tk.Entry(parent, font=FONT, relief="flat", bg="#f1f3f9",
                    highlightthickness=1, highlightbackground="#d7deef",
                    highlightcolor=ACCENT, **kw)
