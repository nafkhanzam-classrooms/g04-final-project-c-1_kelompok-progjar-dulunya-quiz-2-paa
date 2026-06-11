"""Satu thread buat tiap client: baca JSON-nya terus arahin sesuai packet_type"""

import logging
import threading
import time

from shared.protocol import MessageType, encode, msg, StreamDecoder
from server.engines.file_manager import FileManagerError

log = logging.getLogger("server")


class ClientHandler(threading.Thread):
    def __init__(self, conn, addr, controller):
        super().__init__(daemon=True)
        self.conn = conn
        self.addr = addr
        self.controller = controller

        self.username = None # diisi setelah AUTH
        self.room_id = None # diisi setelah JOIN_PROJECT

        self._send_lock = threading.Lock()
        self._decoder = StreamDecoder()
        self._open = True

    def send_raw(self, payload: bytes):
        with self._send_lock:
            if not self._open:
                return
            try:
                self.conn.sendall(payload)
            except OSError:
                self.close()

    def send(self, packet_type: str, **fields):
        self.send_raw(msg(packet_type, **fields))

    def error(self, message: str, code: str = "ERROR"):
        self.send(MessageType.ERROR, code=code, message=message)

    def run(self):
        log.info("Connected %s", self.addr)
        try:
            while self._open:
                chunk = self.conn.recv(4096)
                if not chunk:
                    break
                for message in self._decoder.feed(chunk):
                    self._dispatch(message)
        except OSError:
            pass
        finally:
            self._cleanup()

    def _cleanup(self):
        log.info("Disconnected %s (user=%s)", self.addr, self.username)
        self.controller.unregister_client(self)
        self.close()

    def close(self):
        if not self._open:
            return
        self._open = False
        try:
            self.conn.close()
        except OSError:
            pass

    def _dispatch(self, message: dict):
        ptype = message.get("packet_type")

        if ptype == MessageType.AUTH:
            return self._handle_auth(message)
        if self.username is None:
            return self.error("Not authenticated", code="AUTH_REQUIRED")

        handlers = {
            MessageType.PROJECT_LIST: self._handle_project_list,
            MessageType.CREATE_PROJECT: self._handle_create_project,
            MessageType.JOIN_PROJECT: self._handle_join_project,
            MessageType.DELETE_PROJECT: self._handle_delete_project,
            MessageType.LEAVE_PROJECT: self._handle_leave_project,
            MessageType.FILE_LIST: self._handle_file_list,
            MessageType.FILE_OPEN: self._handle_file_open,
            MessageType.FILE_SYSTEM: self._handle_file_system,
            MessageType.EDIT: self._handle_edit,
            MessageType.CHAT: self._handle_chat,
            MessageType.PRIVATE_CHAT: self._handle_private_chat,
            MessageType.REACTION: self._handle_reaction,
            MessageType.TYPING: self._handle_typing,
        }
        func = handlers.get(ptype)
        if func is None:
            return self.error(f"Unknown packet_type: {ptype!r}", code="UNKNOWN_TYPE")
        log.debug("RX %s from %s", ptype, self.username)
        try:
            func(message)
        except FileManagerError as exc:
            log.warning("File error for %s: %s", self.username, exc)
            self.error(str(exc), code="FILE_ERROR")
        except Exception as exc:
            log.exception("Internal error handling %s from %s", ptype, self.username)
            self.error(f"Server error: {exc}", code="INTERNAL")

    def _handle_auth(self, message):
        username = (message.get("username") or "").strip()
        if not username:
            return self.send(MessageType.AUTH_RESULT, ok=False, message="Username required")
        if not self.controller.claim_username(username):
            return self.send(MessageType.AUTH_RESULT, ok=False, message="Username already in use")
        self.username = username
        self.controller.register_user(username, self)
        self.send(MessageType.AUTH_RESULT, ok=True, user_id=username,
                  message=f"Welcome, {username}")
        log.info("%s authenticated as '%s'", self.addr, username)

    def _handle_project_list(self, message):
        self.send(MessageType.PROJECT_LIST_RESULT,
                  projects=self.controller.file_manager.list_projects())

    def _handle_create_project(self, message):
        name = (message.get("name") or "").strip()
        if not name:
            return self.error("Project name required")
        self.controller.file_manager.create_project(name)
        log.info("%s created project '%s'", self.username, name)
        self.send(MessageType.ACK, ref=MessageType.CREATE_PROJECT, message=f"Project '{name}' created")
        self._handle_project_list(message)

    def _handle_join_project(self, message):
        room_id = (message.get("room_id") or "").strip()
        if not self.controller.file_manager.project_exists(room_id):
            return self.error(f"Project '{room_id}' not found", code="NO_PROJECT")

        if self.room_id:
            self.controller.leave_room(self)

        self.room_id = room_id
        self.controller.join_room(self)
        log.info("%s joined project '%s'", self.username, room_id)

        # kirim tree + history chat sekarang biar client bisa langsung nampilin
        self.send(MessageType.FILE_LIST_RESULT, room_id=room_id,
                  tree=self.controller.file_manager.build_tree(room_id))
        self.send(MessageType.CHAT_HISTORY, room_id=room_id,
                  messages=self.controller.chat_manager.get_history(room_id))
        self.send(MessageType.ACK, ref=MessageType.JOIN_PROJECT, message=f"Joined '{room_id}'")

    def _handle_delete_project(self, message):
        room_id = (message.get("room_id") or "").strip()
        self.controller.file_manager.delete_project(room_id)
        self.controller.ot_engine.drop_document(room_id)
        self.controller.chat_manager.clear(room_id)
        log.info("%s deleted project '%s'", self.username, room_id)
        self.send(MessageType.ACK, ref=MessageType.DELETE_PROJECT, message=f"Project '{room_id}' deleted")
        self._handle_project_list(message)

    def _handle_leave_project(self, message):
        self.controller.leave_room(self)
        self.send(MessageType.ACK, ref=MessageType.LEAVE_PROJECT, message="Left project")

    def _require_room(self, message):
        room_id = (message.get("room_id") or self.room_id or "").strip()
        if not room_id or room_id != self.room_id:
            self.error("Join a project first", code="NOT_IN_ROOM")
            return None
        return room_id

    def _handle_file_list(self, message):
        room_id = self._require_room(message)
        if room_id is None:
            return
        self.send(MessageType.FILE_LIST_RESULT, room_id=room_id,
                  tree=self.controller.file_manager.build_tree(room_id))

    def _handle_file_open(self, message):
        room_id = self._require_room(message)
        if room_id is None:
            return
        path = message.get("path") or ""
        doc = self.controller.ot_engine.get_document(room_id, path)
        self.send(MessageType.FILE_CONTENT, room_id=room_id, path=path,
                  content=doc.text, version=doc.version)

    def _handle_file_system(self, message):
        room_id = self._require_room(message)
        if room_id is None:
            return
        op = message.get("operation")
        path = message.get("path") or ""
        new_name = message.get("new_name")
        fm = self.controller.file_manager

        if op == "CREATE_FILE":
            fm.create_file(room_id, path)
        elif op == "CREATE_DIR":
            fm.create_dir(room_id, path)
        elif op == "DELETE":
            fm.delete(room_id, path)
            self.controller.ot_engine.drop_document(room_id, path)
        elif op == "RENAME":
            fm.rename(room_id, path, new_name)
            self.controller.ot_engine.drop_document(room_id, path)
        else:
            return self.error(f"Unknown file operation: {op!r}")

        log.info("%s %s '%s'%s in '%s'", self.username, op, path,
                 f" -> '{new_name}'" if new_name else "", room_id)

        # semua orang di room (termasuk yg ngubah) refresh tree-nya
        tree = fm.build_tree(room_id)
        self.controller.broadcast_to_room(
            room_id, msg(MessageType.FILE_LIST_RESULT, room_id=room_id, tree=tree))

    def _handle_edit(self, message):
        room_id = self._require_room(message)
        if room_id is None:
            return
        path = message.get("path") or message.get("file") or ""
        if not path:
            return self.error("EDIT requires a 'path'")

        transformed, version, _text = self.controller.ot_engine.apply_edit(room_id, path, message)
        log.debug("%s edit %s '%s' @%s -> v%s", self.username, transformed["operation"],
                  path, transformed["position"], version)

        out = {
            "packet_type": MessageType.EDIT,
            "room_id": room_id,
            "path": path,
            "user_id": self.username,
            "operation": transformed["operation"],
            "position": transformed["position"],
            "content": transformed.get("content", ""),
            "length": transformed.get("length", 0),
            "version": version,
        }
        self.controller.broadcast_to_room(room_id, encode(out), exclude_user=self.username)
        self.send(MessageType.ACK, ref=MessageType.EDIT, path=path, version=version)

    def _handle_chat(self, message):
        room_id = self._require_room(message)
        if room_id is None:
            return
        text = message.get("message") or ""
        entry = self.controller.chat_manager.add_message(room_id, self.username, text)
        log.info("[chat %s] %s: %s", room_id, self.username, text)
        self.controller.broadcast_to_room(
            room_id,
            msg(MessageType.CHAT, room_id=room_id, id=entry["id"], sender_id=self.username,
                message=text, timestamp=entry["timestamp"]),
        )

    def _handle_reaction(self, message):
        room_id = self._require_room(message)
        if room_id is None:
            return
        message_id = message.get("message_id")
        emoji = message.get("emoji")
        if not message_id or not emoji:
            return self.error("REACTION requires 'message_id' and 'emoji'")
        entry = self.controller.chat_manager.toggle_reaction(
            room_id, message_id, emoji, self.username)
        if entry is None:
            return
        log.info("%s reacted %s to %s in '%s'", self.username, emoji, message_id, room_id)
        self.controller.broadcast_to_room(
            room_id,
            msg(MessageType.REACTION_UPDATE, room_id=room_id,
                message_id=message_id, reactions=entry["reactions"]),
        )

    def _handle_private_chat(self, message):
        target = (message.get("target_id") or "").strip()
        text = message.get("message") or ""
        if not target:
            return self.error("PRIVATE_CHAT requires a 'target_id'")
        if target == self.username:
            return self.error("Cannot private-message yourself")

        payload = msg(MessageType.PRIVATE_CHAT, sender_id=self.username,
                      target_id=target, message=text,
                      timestamp=time.strftime("%Y-%m-%d %H:%M:%S"))

        if not self.controller.send_to_user(target, payload):
            log.info("[pm] %s -> %s FAILED (offline)", self.username, target)
            return self.error(f"User '{target}' is not online", code="NO_USER")

        self.send_raw(payload)   # balikin juga ke pengirim biar keliatan di chatnya
        log.info("[pm] %s -> %s: %s", self.username, target, text)

    def _handle_typing(self, message):
        room_id = self._require_room(message)
        if room_id is None:
            return
        log.debug("%s typing=%s in '%s'", self.username,
                  bool(message.get("is_typing")), room_id)
        self.controller.broadcast_to_room(
            room_id,
            msg(MessageType.TYPING, room_id=room_id, user_id=self.username,
                is_typing=bool(message.get("is_typing"))),
            exclude_user=self.username,
        )
