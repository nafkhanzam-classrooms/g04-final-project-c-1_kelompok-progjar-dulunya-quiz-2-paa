"""Client CLI kecil buat demo/nyoba server tanpa GUI.

Jalanin server dulu (python -m server.main), then di terminal lain baru python -m tools.cli_client --user agung

Perintah setelah konek:
    /projects                  lihat daftar project
    /create <name>             bikin project
    /join <name>               masuk project
    /leave                     keluar dari project
    /delete <name>             hapus project
    /tree                      lihat file di project
    /newfile <path>            bikin file
    /newdir <path>             bikin folder
    /open <path>               buka file (nampilin isi + version)
    /edit <path> <pos> <text>  sisip <text> di posisi <pos>
    /del <path> <pos> <len>    hapus <len> karakter mulai <pos>
    /rename <path> <newname>   ganti nama file/folder
    /pm <user> <message>       kirim pesan private
    <selain itu>               dianggap pesan chat biasa
    /quit                      keluar
"""

import argparse
import os
import socket
import sys
import threading

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.protocol import MessageType, msg, StreamDecoder


class CliClient:
    def __init__(self, host, port, user):
        self.sock = socket.create_connection((host, port))
        self.user = user
        self.room = None
        self._decoder = StreamDecoder()
        self._running = True

    def _listen(self):
        while self._running:
            try:
                chunk = self.sock.recv(4096)
            except OSError:
                break
            if not chunk:
                print("\n[disconnected]")
                self._running = False
                break
            for m in self._decoder.feed(chunk):
                self._show(m)

    def _show(self, m):
        t = m.get("packet_type")
        if t == MessageType.CHAT:
            print(f"\n  <chat> {m.get('sender_id')}: {m.get('message')}")
        elif t == MessageType.PRIVATE_CHAT:
            print(f"\n  <pm> {m.get('sender_id')} -> {m.get('target_id')}: {m.get('message')}")
        elif t == MessageType.EDIT:
            print(f"\n  <edit by {m.get('user_id')}> {m.get('operation')} @ "
                  f"{m.get('position')} {m.get('content')!r} (v{m.get('version')})")
        elif t == MessageType.FILE_CONTENT:
            print(f"\n  <file {m.get('path')} v{m.get('version')}>\n{m.get('content')}")
        elif t == MessageType.FILE_LIST_RESULT:
            print(f"\n  <tree> {_flatten(m.get('tree', []))}")
        elif t == MessageType.PROJECT_LIST_RESULT:
            print(f"\n  <projects> {m.get('projects')}")
        elif t == MessageType.PRESENCE:
            print(f"\n  <presence> {m.get('members')}")
        elif t == MessageType.AUTH_RESULT:
            print(f"\n  <auth> ok={m.get('ok')} - {m.get('message')}")
        elif t == MessageType.ACK:
            print(f"\n  <ack> {m.get('ref')} {m.get('message','')} {('v'+str(m['version'])) if 'version' in m else ''}")
        elif t == MessageType.ERROR:
            print(f"\n  <error:{m.get('code')}> {m.get('message')}")
        elif t == MessageType.CHAT_HISTORY:
            for e in m.get("messages", []):
                print(f"  <history> {e['sender_id']}: {e['message']}")
        else:
            print(f"\n  <{t}> {m}")
        print("> ", end="", flush=True)

    def send(self, packet_type, **fields):
        self.sock.sendall(msg(packet_type, **fields))

    def run(self):
        threading.Thread(target=self._listen, daemon=True).start()
        self.send(MessageType.AUTH, username=self.user)

        while self._running:
            try:
                line = input("> ").strip()
            except (EOFError, KeyboardInterrupt):
                break
            if not line:
                continue
            self._handle(line)
        self._running = False
        self.sock.close()

    def _handle(self, line):
        if not line.startswith("/"):
            if not self.room:
                print("  (join a project first to chat)")
                return
            return self.send(MessageType.CHAT, room_id=self.room, sender_id=self.user, message=line)

        parts = line.split(" ", 1)
        cmd = parts[0]
        arg = parts[1] if len(parts) > 1 else ""

        if cmd == "/quit":
            self._running = False
        elif cmd == "/projects":
            self.send(MessageType.PROJECT_LIST)
        elif cmd == "/create":
            self.send(MessageType.CREATE_PROJECT, name=arg)
        elif cmd == "/join":
            self.room = arg
            self.send(MessageType.JOIN_PROJECT, room_id=arg)
        elif cmd == "/leave":
            self.send(MessageType.LEAVE_PROJECT, room_id=self.room); self.room = None
        elif cmd == "/delete":
            self.send(MessageType.DELETE_PROJECT, room_id=arg)
        elif cmd == "/tree":
            self.send(MessageType.FILE_LIST, room_id=self.room)
        elif cmd == "/newfile":
            self.send(MessageType.FILE_SYSTEM, room_id=self.room, operation="CREATE_FILE", path=arg)
        elif cmd == "/newdir":
            self.send(MessageType.FILE_SYSTEM, room_id=self.room, operation="CREATE_DIR", path=arg)
        elif cmd == "/open":
            self.send(MessageType.FILE_OPEN, room_id=self.room, path=arg)
        elif cmd == "/edit":
            path, pos, text = arg.split(" ", 2)
            self.send(MessageType.EDIT, room_id=self.room, path=path, user_id=self.user,
                      operation="insert", positionS=int(pos), positionE=int(pos),
                      content=text, version=0)
        elif cmd == "/del":
            path, pos, length = arg.split(" ", 2)
            self.send(MessageType.EDIT, room_id=self.room, path=path, user_id=self.user,
                      operation="delete", positionS=int(pos), positionE=int(pos) + int(length),
                      content="", version=0)
        elif cmd == "/rename":
            path, new = arg.split(" ", 1)
            self.send(MessageType.FILE_SYSTEM, room_id=self.room, operation="RENAME",
                      path=path, new_name=new)
        elif cmd == "/pm":
            target, text = arg.split(" ", 1)
            self.send(MessageType.PRIVATE_CHAT, room_id=self.room,
                      sender_id=self.user, target_id=target, message=text)
        else:
            print("  unknown command")


def _flatten(tree, prefix=""):
    out = []
    for n in tree:
        out.append(prefix + n["name"] + ("/" if n["type"] == "dir" else ""))
        if n["type"] == "dir":
            out.extend(_flatten(n.get("children", []), prefix + n["name"] + "/"))
    return out


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8888)
    p.add_argument("--user", required=True)
    a = p.parse_args()
    CliClient(a.host, a.port, a.user).run()


if __name__ == "__main__":
    main()
