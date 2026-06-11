"""Nyimpen siapa aja yang lagi ada di sebuah project, biar tau mau broadcast ke siapa."""

import threading


class Room:
    def __init__(self, room_id: str):
        self.room_id = room_id
        self._members = {}  # user_id => ClientHandler
        self.lock = threading.RLock()

    def add_member(self, user_id: str, handler):
        with self.lock:
            self._members[user_id] = handler

    def remove_member(self, user_id: str):
        with self.lock:
            self._members.pop(user_id, None)

    def members(self):
        with self.lock:
            return list(self._members.items())

    def member_ids(self):
        with self.lock:
            return sorted(self._members.keys())

    def is_empty(self) -> bool:
        with self.lock:
            return not self._members
