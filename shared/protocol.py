from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any
import json


@dataclass
class Packet:
    packet_type: str

    def to_json(self):
        return json.dumps(asdict(self))

    @staticmethod
    def from_json(data: str):
        return json.loads(data)


# ==================================================
# 1. EDIT BROADCAST PACKET
# ==================================================

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


# ==================================================
# 2. CHAT MESSAGE
# ==================================================

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


# ==================================================
# IS TYPING
# ==================================================

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


# ==================================================
# 3. FILE SYSTEM UPDATE
# ==================================================

@dataclass
class FileSystemPacket(Packet):

    room_id: str

    operation: str
    # CREATE_FILE
    # CREATE_DIR
    # DELETE
    # RENAME
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