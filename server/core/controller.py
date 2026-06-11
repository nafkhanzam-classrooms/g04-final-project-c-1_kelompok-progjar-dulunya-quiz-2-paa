"""Server TCP-nya: nerima koneksi, nyimpen daftar room & client, dan broadcast ke room. Tiap koneksi dapet 1 thread ClientHandler sendiri."""

import logging
import os
import socket
import threading

from server.core.room import Room
from server.engines.file_manager import FileManager
from server.engines.ot_engine import OTEngine
from server.engines.chat import ChatManager

log = logging.getLogger("server")


DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 8888
_SERVER_DIR = os.path.dirname(os.path.dirname(__file__))
DEFAULT_STORAGE = os.path.join(_SERVER_DIR, "storage")
DEFAULT_CHAT_FILE = os.path.join(_SERVER_DIR, "data", "chats.json")


class ServerController:
    def __init__(self, host=DEFAULT_HOST, port=DEFAULT_PORT, storage_root=DEFAULT_STORAGE,
                 chat_file=DEFAULT_CHAT_FILE):
        self.host = host
        self.port = port

        self.file_manager = FileManager(storage_root)
        self.ot_engine = OTEngine(self.file_manager)
        self.chat_manager = ChatManager(chat_file)

        self._clients = set()   # semua ClientHandler yg konek
        self._rooms = {}    # room_id => Room
        self._users = {}    # username => ClientHandle (buat private chat)
        self._taken_usernames = set()   # biar username ga dobel selama online
        self._lock = threading.RLock()

        self._server_socket = None
        self._running = False

    def start(self):
        self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server_socket.bind((self.host, self.port))
        self._server_socket.listen(50)
        self._running = True
        log.info("Listening on %s:%s", self.host, self.port)
        log.info("Storage root: %s", self.file_manager.storage_root)

        try:
            while self._running:
                try:
                    conn, addr = self._server_socket.accept()
                except OSError:
                    break  # socket-nya udah ditutup pas shutdown
                from server.core.handler import ClientHandler  # import di sini biar ga circular
                handler = ClientHandler(conn, addr, self)
                self.register_client(handler)
                handler.start()
        finally:
            self.stop()

    def stop(self):
        if not self._running:
            return
        self._running = False
        log.info("Shutting down")
        if self._server_socket:
            try:
                self._server_socket.close()
            except OSError:
                pass
        for handler in list(self._clients):
            handler.close()

    def register_client(self, handler):
        with self._lock:
            self._clients.add(handler)

    def unregister_client(self, handler):
        # koneksi putus: lepas username-nya dan keluarin dari room
        with self._lock:
            self._clients.discard(handler)
            if handler.username:
                self._taken_usernames.discard(handler.username)
                self._users.pop(handler.username, None)
        if handler.room_id:
            self.leave_room(handler)

    def claim_username(self, username: str) -> bool:
        with self._lock:
            if username in self._taken_usernames:
                return False
            self._taken_usernames.add(username)
            return True

    def register_user(self, username: str, handler):
        # simpan username => handler biar bisa kirim private chat ke orang tertentu
        with self._lock:
            self._users[username] = handler

    def get_user_handler(self, username: str):
        with self._lock:
            return self._users.get(username)

    def send_to_user(self, username: str, payload: bytes) -> bool:
        handler = self.get_user_handler(username)
        if handler is None:
            return False
        handler.send_raw(payload)
        return True

    def get_room(self, room_id: str, create: bool = False) -> Room:
        with self._lock:
            room = self._rooms.get(room_id)
            if room is None and create:
                room = Room(room_id)
                self._rooms[room_id] = room
            return room

    def join_room(self, handler):
        room = self.get_room(handler.room_id, create=True)
        room.add_member(handler.username, handler)
        self.broadcast_presence(handler.room_id)

    def leave_room(self, handler):
        room_id = handler.room_id
        if not room_id:
            return
        room = self.get_room(room_id)
        if room:
            room.remove_member(handler.username)
            if room.is_empty():
                with self._lock:
                    self._rooms.pop(room_id, None)
            else:
                self.broadcast_presence(room_id)
        handler.room_id = None

    def broadcast_to_room(self, room_id: str, payload: bytes, exclude_user=None):
        room = self.get_room(room_id)
        if not room:
            return
        for user_id, handler in room.members():
            if user_id == exclude_user:
                continue
            handler.send_raw(payload)

    def broadcast_presence(self, room_id: str):
        from shared.protocol import MessageType, msg
        room = self.get_room(room_id)
        if not room:
            return
        payload = msg(MessageType.PRESENCE, room_id=room_id, members=room.member_ids())
        self.broadcast_to_room(room_id, payload)
