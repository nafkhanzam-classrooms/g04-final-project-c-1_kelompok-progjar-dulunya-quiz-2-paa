"""Bagian jaringan di client. Ada thread di belakang yang baca pesan terus dimasukin ke queue; loop Tkinter manggil pump() buat ngeproses pesannya di main thread (widget Tkinter cuma boleh disentuh dari main thread)."""

import queue
import socket
import threading

from shared.protocol import msg, StreamDecoder


class NetClient:
    def __init__(self):
        self.sock = None
        self.connected = False
        self.username = None

        self._decoder = StreamDecoder()
        self._inbox = queue.Queue()
        self._handlers = {}             # packet_type => fungsi(message)
        self._on_disconnect = None
        self._listen_thread = None

    def connect(self, host: str, port: int):
        # kalau gagal bakal lempar OSError, nanti yang manggil yang nampilin errornya
        self.sock = socket.create_connection((host, port), timeout=5)
        self.sock.settimeout(None)
        self.connected = True
        self._listen_thread = threading.Thread(target=self._listen, daemon=True)
        self._listen_thread.start()

    def _listen(self):
        try:
            while self.connected:
                chunk = self.sock.recv(4096)
                if not chunk:
                    break
                for message in self._decoder.feed(chunk):
                    self._inbox.put(message)
        except OSError:
            pass
        finally:
            self.connected = False
            self._inbox.put({"packet_type": "__DISCONNECTED__"})

    def close(self):
        self.connected = False
        if self.sock:
            try:
                self.sock.close()
            except OSError:
                pass

    def send(self, packet_type: str, **fields):
        if not self.connected or not self.sock:
            return
        try:
            self.sock.sendall(msg(packet_type, **fields))
        except OSError:
            self.connected = False

    def set_handlers(self, handlers: dict, on_disconnect=None):
        # ganti tabel handler, biasanya pas pindah layar
        self._handlers = dict(handlers)
        self._on_disconnect = on_disconnect

    def pump(self):
        # ngeproses isi inbox di main thread; dipanggil dari root.after()
        while True:
            try:
                message = self._inbox.get_nowait()
            except queue.Empty:
                break
            ptype = message.get("packet_type")
            if ptype == "__DISCONNECTED__":
                if self._on_disconnect:
                    self._on_disconnect()
                continue
            handler = self._handlers.get(ptype)
            if handler:
                handler(message)
