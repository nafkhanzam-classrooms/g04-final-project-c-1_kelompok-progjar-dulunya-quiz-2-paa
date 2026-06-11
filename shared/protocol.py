from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any
import json


# kumpulan packet_type, dipakai bareng server sama client biar ga salah ketik
class MessageType:
    # auth / session
    AUTH = "AUTH" # client => server : { username }
    AUTH_RESULT = "AUTH_RESULT" # server => client : { ok, user_id, message }

    # project (1 project = 1 room, intinya folder di storage)
    PROJECT_LIST = "PROJECT_LIST" # client => server : (no body)
    PROJECT_LIST_RESULT = "PROJECT_LIST_RESULT" # server => client : { projects: [..] }
    CREATE_PROJECT = "CREATE_PROJECT" # client => server : { name }
    JOIN_PROJECT = "JOIN_PROJECT" # client => server : { room_id }
    DELETE_PROJECT = "DELETE_PROJECT" # client => server : { room_id }
    LEAVE_PROJECT = "LEAVE_PROJECT" # client => server : { room_id }
    ROOM_STATE = "ROOM_STATE" # server => client : { room_id, members, tree }

    # file
    FILE_LIST = "FILE_LIST" # client => server : { room_id }
    FILE_LIST_RESULT = "FILE_LIST_RESULT" # server => client : { room_id, tree }
    FILE_OPEN = "FILE_OPEN" # client => server : { room_id, path }
    FILE_CONTENT = "FILE_CONTENT" # server => client : { room_id, path, content, version }
    FILE_SYSTEM = "FILE_SYSTEM" # create/delete/rename

    # collaboration
    EDIT = "EDIT"
    CHAT = "CHAT"
    PRIVATE_CHAT = "PRIVATE_CHAT" # direct message : { room_id, sender_id, target_id, message, timestamp }
    TYPING = "TYPING"
    REACTION = "REACTION" # client => server : { room_id, message_id, emoji }
    REACTION_UPDATE = "REACTION_UPDATE" # server => client : { room_id, message_id, reactions }
    CHAT_HISTORY = "CHAT_HISTORY" # server => client : { room_id, messages }
    PRESENCE = "PRESENCE" # server => client : { room_id, members }

    # respon umum
    ACK = "ACK" # server => client : { ref, message }
    ERROR = "ERROR" # server => client : { code, message }


@dataclass
class Packet:
    packet_type: str

    def to_json(self):
        return json.dumps(asdict(self))

    @staticmethod
    def from_json(data: str):
        return json.loads(data)


# format kirim: 1 pesan = 1 JSON per baris, diakhiri '\n'
def encode(payload) -> bytes:
    if hasattr(payload, "to_json"):
        data = payload.to_json()
    elif isinstance(payload, (dict, list)):
        data = json.dumps(payload)
    else:
        data = json.dumps(asdict(payload))
    return (data + "\n").encode("utf-8")


def msg(packet_type: str, **fields) -> bytes:
    body = {"packet_type": packet_type}
    body.update(fields)
    return encode(body)


class StreamDecoder:
    """Nampung byte mentah dari socket, terus keluarin pesan JSON utuh per baris."""

    def __init__(self):
        self._buffer = b""

    def feed(self, chunk: bytes):
        if not chunk:
            return
        self._buffer += chunk
        while b"\n" in self._buffer:
            line, self._buffer = self._buffer.split(b"\n", 1)
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line.decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError):
                continue


# helper packet bertipe (opsional aja, servernya sendiri kerja pakai dict biasa)
@dataclass
class EditPacket(Packet):
    room_id: str
    user_id: str
    operation: str      # append | insert | delete
    positionS: int   
    positionE: int
    content: str
    version: int

    def __init__(
        self,
        room_id: str,
        user_id: str,
        operation: str,
        positionS: int,
        positionE: int,
        content: str,
        version: int
    ):
        super().__init__("EDIT")
        self.room_id = room_id
        self.user_id = user_id
        self.operation = operation
        self.positionS = positionS
        self.positionE = positionE
        self.content = content
        self.version = version


@dataclass
class ChatPacket(Packet):
    room_id: str
    sender_id: str
    message: str

    def __init__(
        self,
        room_id: str,
        sender_id: str,
        message: str
    ):
        super().__init__("CHAT")
        self.room_id = room_id
        self.sender_id = sender_id
        self.message = message


@dataclass
class TypingPacket(Packet):
    room_id: str
    user_id: str
    is_typing: bool

    def __init__(
        self,
        room_id: str,
        user_id: str,
        is_typing: bool
    ):
        super().__init__("TYPING")
        self.room_id = room_id
        self.user_id = user_id
        self.is_typing = is_typing


@dataclass
class FileSystemPacket(Packet):
    room_id: str
    operation: str       # CREATE_FILE | CREATE_DIR | DELETE | RENAME
    path: str
    new_name: Optional[str] = None

    def __init__(
        self,
        room_id: str,
        operation: str,
        path: str,
        new_name: str | None = None
    ):
        super().__init__("FILE_SYSTEM")

        self.room_id = room_id
        self.operation = operation
        self.path = path
        self.new_name = new_name