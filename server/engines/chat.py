"""History chat per room, disimpen ke file JSON biar ga ilang kalau server restart"""

import json
import os
import threading
import time
import uuid


class ChatManager:
    def __init__(self, data_file, history_limit=200):
        self.data_file = data_file
        self.history_limit = history_limit
        self._history = {}          # room_id => list pesan
        self._lock = threading.RLock()

        os.makedirs(os.path.dirname(self.data_file), exist_ok=True)
        self._load()

    def _load(self):
        if not os.path.exists(self.data_file):
            return
        try:
            with open(self.data_file, encoding="utf-8") as f:
                self._history = json.load(f)
        except (OSError, json.JSONDecodeError):
            self._history = {}

    def _save(self):
        try:
            with open(self.data_file, "w", encoding="utf-8") as f:
                json.dump(self._history, f, ensure_ascii=False)
        except OSError:
            pass

    def add_message(self, room_id, sender_id, message):
        entry = {
            "id": uuid.uuid4().hex[:8],
            "sender_id": sender_id,
            "message": message,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "reactions": {},
        }
        with self._lock:
            bucket = self._history.setdefault(room_id, [])
            bucket.append(entry)
            if len(bucket) > self.history_limit:
                del bucket[: -self.history_limit]
            self._save()
        return entry

    def toggle_reaction(self, room_id, message_id, emoji, user):
        """Tambah/hapus reaksi user di sebuah pesan, then balikin pesannya"""
        with self._lock:
            for entry in self._history.get(room_id, []):
                if entry.get("id") == message_id:
                    reactions = entry.setdefault("reactions", {})
                    users = reactions.setdefault(emoji, [])
                    if user in users:
                        users.remove(user)
                        if not users:
                            del reactions[emoji]
                    else:
                        users.append(user)
                    self._save()
                    return entry
            return None

    def get_history(self, room_id):
        with self._lock:
            return [dict(e) for e in self._history.get(room_id, [])]

    def clear(self, room_id):
        with self._lock:
            self._history.pop(room_id, None)
            self._save()
