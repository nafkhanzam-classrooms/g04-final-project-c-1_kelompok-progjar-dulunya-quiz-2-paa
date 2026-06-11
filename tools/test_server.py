"""Tes end-to-end server: nyalain server beneran di port sementara terus nyoba auth, project, operasi file, edit OT barengan, chat, private chat, reaction, dan persistence. Jalanin: python -m tools.test_server"""

import os
import socket
import sys
import tempfile
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.protocol import MessageType, msg, StreamDecoder
from server.core.controller import ServerController

HOST = "127.0.0.1"
PORT = 8899


class TestClient:
    def __init__(self, host=HOST, port=PORT):
        self.sock = socket.create_connection((host, port))
        self.sock.settimeout(0.2)
        self._decoder = StreamDecoder()
        self._inbox = []

    def send(self, packet_type, **fields):
        self.sock.sendall(msg(packet_type, **fields))

    def _pump(self):
        try:
            chunk = self.sock.recv(4096)
            if chunk:
                self._inbox.extend(self._decoder.feed(chunk))
        except socket.timeout:
            pass
        except OSError:
            pass

    def wait_for(self, packet_type, timeout=3.0):
        """Nunggu sampai ada pesan dengan packet_type tertentu, then balikin (atau None)."""
        deadline = time.time() + timeout
        while time.time() < deadline:
            for i, m in enumerate(self._inbox):
                if m.get("packet_type") == packet_type:
                    return self._inbox.pop(i)
            self._pump()
        return None

    def drain(self):
        self._pump()

    def close(self):
        try:
            self.sock.close()
        except OSError:
            pass


PASS = "\033[92mPASS\033[0m"
FAIL = "\033[91mFAIL\033[0m"
_failures = 0


def check(label, condition):
    global _failures
    print(f"  [{PASS if condition else FAIL}] {label}")
    if not condition:
        _failures += 1


def main():
    storage = tempfile.mkdtemp(prefix="collab_test_")
    chat_file = os.path.join(storage, "chats.json")
    controller = ServerController(host=HOST, port=PORT, storage_root=storage, chat_file=chat_file)
    server_thread = threading.Thread(target=controller.start, daemon=True)
    server_thread.start()
    time.sleep(0.4)  # let it bind/listen

    try:
        print("== AUTH ==")
        alice = TestClient()
        alice.send(MessageType.AUTH, username="alice")
        r = alice.wait_for(MessageType.AUTH_RESULT)
        check("alice authenticates", r and r.get("ok") is True)

        bob = TestClient()
        bob.send(MessageType.AUTH, username="bob")
        r = bob.wait_for(MessageType.AUTH_RESULT)
        check("bob authenticates", r and r.get("ok") is True)

        # username dobel harus ditolak
        dup = TestClient()
        dup.send(MessageType.AUTH, username="alice")
        r = dup.wait_for(MessageType.AUTH_RESULT)
        check("duplicate username rejected", r and r.get("ok") is False)
        dup.close()

        print("== PROJECT ==")
        alice.send(MessageType.CREATE_PROJECT, name="proj1")
        r = alice.wait_for(MessageType.PROJECT_LIST_RESULT)
        check("create + list project", r and "proj1" in r.get("projects", []))

        alice.send(MessageType.JOIN_PROJECT, room_id="proj1")
        check("alice joins (file list)", alice.wait_for(MessageType.FILE_LIST_RESULT) is not None)
        check("alice joins (ack)", alice.wait_for(MessageType.ACK) is not None)

        bob.send(MessageType.JOIN_PROJECT, room_id="proj1")
        bob.wait_for(MessageType.ACK)

        print("== FILE SYSTEM ==")
        alice.send(MessageType.FILE_SYSTEM, room_id="proj1", operation="CREATE_FILE", path="notes.txt")
        r = alice.wait_for(MessageType.FILE_LIST_RESULT)
        names = [n.get("name") for n in (r.get("tree") if r else [])]
        check("create file broadcasts new tree", "notes.txt" in names)
        check("bob also receives tree update", bob.wait_for(MessageType.FILE_LIST_RESULT) is not None)

        alice.send(MessageType.FILE_OPEN, room_id="proj1", path="notes.txt")
        r = alice.wait_for(MessageType.FILE_CONTENT)
        check("open file -> empty content v0", r and r.get("content") == "" and r.get("version") == 0)

        print("== OT (concurrent edits) ==")
        # dua client sama-sama di versi 0, nyisip di posisi 0 barengan
        alice.send(MessageType.EDIT, room_id="proj1", path="notes.txt", user_id="alice",
                   operation="insert", positionS=0, positionE=0, content="Hello", version=0)
        bob.send(MessageType.EDIT, room_id="proj1", path="notes.txt", user_id="bob",
                 operation="insert", positionS=0, positionE=0, content="World", version=0)
        time.sleep(0.5)
        alice.drain(); bob.drain()

        doc = controller.ot_engine.get_document("proj1", "notes.txt")
        check("server doc converged to length 10", len(doc.text) == 10)
        check("server doc contains both inserts",
              "Hello" in doc.text and "World" in doc.text)
        print(f"      server text = {doc.text!r}  version={doc.version}")

        # client baru yang buka file harusnya lihat hasil teks yang udah nyatu
        carol = TestClient()
        carol.send(MessageType.AUTH, username="carol"); carol.wait_for(MessageType.AUTH_RESULT)
        carol.send(MessageType.JOIN_PROJECT, room_id="proj1"); carol.wait_for(MessageType.ACK)
        carol.send(MessageType.FILE_OPEN, room_id="proj1", path="notes.txt")
        r = carol.wait_for(MessageType.FILE_CONTENT)
        check("new client opens converged text", r and r.get("content") == doc.text)

        print("== CHAT ==")
        alice.send(MessageType.CHAT, room_id="proj1", sender_id="alice", message="hi team")
        r = bob.wait_for(MessageType.CHAT)
        check("chat broadcast reaches bob", r and r.get("message") == "hi team"
              and r.get("sender_id") == "alice")
        message_id = r.get("id")
        check("chat message has an id", bool(message_id))

        print("== PRIVATE CHAT ==")
        alice.send(MessageType.PRIVATE_CHAT, room_id="proj1", sender_id="alice",
                   target_id="bob", message="psst bob")
        r = bob.wait_for(MessageType.PRIVATE_CHAT)
        check("private message reaches target only", r and r.get("message") == "psst bob")
        alice.send(MessageType.PRIVATE_CHAT, room_id="proj1", sender_id="alice",
                   target_id="ghost", message="hi")
        check("private message to offline user errors",
              (alice.wait_for(MessageType.ERROR) or {}).get("code") == "NO_USER")

        print("== REACTION ==")
        bob.send(MessageType.REACTION, room_id="proj1", message_id=message_id, emoji="👍")
        r = alice.wait_for(MessageType.REACTION_UPDATE)
        check("reaction broadcast carries the emoji",
              r and "👍" in r.get("reactions", {}) and "bob" in r["reactions"]["👍"])
        bob.send(MessageType.REACTION, room_id="proj1", message_id=message_id, emoji="👍")
        r = alice.wait_for(MessageType.REACTION_UPDATE)
        check("re-reacting toggles it off", r and "👍" not in r.get("reactions", {}))

        print("== PERSISTENCE ==")
        saved = os.path.join(storage, "proj1", "notes.txt")
        with open(saved, encoding="utf-8") as fh:
            on_disk = fh.read()
        check("edits persisted to disk", on_disk == doc.text)

        from server.engines.chat import ChatManager
        reloaded = ChatManager(chat_file)
        history = reloaded.get_history("proj1")
        check("chat history persisted & reloaded from json",
              any(m["message"] == "hi team" for m in history))

        print("== RENAME / DELETE ==")
        alice.send(MessageType.FILE_SYSTEM, room_id="proj1", operation="RENAME",
                   path="notes.txt", new_name="readme.txt")
        r = alice.wait_for(MessageType.FILE_LIST_RESULT)
        names = [n.get("name") for n in (r.get("tree") if r else [])]
        check("rename reflected in tree", "readme.txt" in names and "notes.txt" not in names)

        alice.close(); bob.close(); carol.close()
    finally:
        controller.stop()

    print()
    if _failures == 0:
        print("ALL CHECKS PASSED")
    else:
        print(f"{_failures} CHECK(S) FAILED")
    sys.exit(1 if _failures else 0)


if __name__ == "__main__":
    main()
