from dataclasses import dataclass


@dataclass
class TextOperation:

    operation: str
    # insert
    # delete
    # append
    position: int
    content: str
    author: str
    version: int


@dataclass
class CursorPosition:
    user_id: str
    line: int
    column: int


@dataclass
class DocumentState:
    room_id: str
    text: str
    version: int