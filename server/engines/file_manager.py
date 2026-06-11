"""Urusan baca/tulis file project ke disk. 1 project = 1 folder di dalam storage. Cuman di sini tempat yang nyentuh filesystem, dan path yang nyoba keluar dari storage bakal ditolak."""

import os
import shutil
import threading


class FileManagerError(Exception):
    pass


class FileManager:
    def __init__(self, storage_root: str):
        self.storage_root = os.path.abspath(storage_root)
        os.makedirs(self.storage_root, exist_ok=True)
        self._lock = threading.RLock()

    def _safe_abs(self, *parts: str) -> str:
        # gabung ke storage root, pastiin hasilnya masih di dalam storage
        joined = os.path.abspath(os.path.join(self.storage_root, *parts))
        if os.path.commonpath([joined, self.storage_root]) != self.storage_root:
            raise FileManagerError("Path escapes storage root")
        return joined

    def project_path(self, room_id: str) -> str:
        if not room_id or "/" in room_id or "\\" in room_id or os.path.sep in room_id:
            raise FileManagerError(f"Invalid project id: {room_id!r}")
        return self._safe_abs(room_id)

    def _resolve(self, room_id: str, rel_path: str) -> str:
        rel_path = (rel_path or "").replace("\\", "/").strip("/")
        return self._safe_abs(room_id, *rel_path.split("/")) if rel_path else self.project_path(room_id)

    def list_projects(self):
        with self._lock:
            return sorted(
                name for name in os.listdir(self.storage_root)
                if os.path.isdir(os.path.join(self.storage_root, name))
            )

    def create_project(self, name: str):
        with self._lock:
            path = self.project_path(name)
            if os.path.exists(path):
                raise FileManagerError(f"Project '{name}' already exists")
            os.makedirs(path)

    def delete_project(self, room_id: str):
        with self._lock:
            path = self.project_path(room_id)
            if not os.path.isdir(path):
                raise FileManagerError(f"Project '{room_id}' not found")
            shutil.rmtree(path)

    def project_exists(self, room_id: str) -> bool:
        try:
            return os.path.isdir(self.project_path(room_id))
        except FileManagerError:
            return False

    def build_tree(self, room_id: str):
        """Bikin struktur folder buat ditampilin GUI: [{type: dir|file, name, children}]."""
        root = self.project_path(room_id)
        if not os.path.isdir(root):
            raise FileManagerError(f"Project '{room_id}' not found")

        def walk(directory: str):
            nodes = []
            for entry in sorted(os.listdir(directory)):
                full = os.path.join(directory, entry)
                if os.path.isdir(full):
                    nodes.append({"type": "dir", "name": entry, "children": walk(full)})
                else:
                    nodes.append({"type": "file", "name": entry})
            nodes.sort(key=lambda n: (n["type"] != "dir", n["name"].lower()))  # folder dulu, baru file
            return nodes

        with self._lock:
            return walk(root)

    def read_file(self, room_id: str, rel_path: str) -> str:
        with self._lock:
            path = self._resolve(room_id, rel_path)
            if not os.path.isfile(path):
                raise FileManagerError(f"File not found: {rel_path}")
            with open(path, "r", encoding="utf-8", newline="") as fh:
                return fh.read()

    def write_file(self, room_id: str, rel_path: str, content: str):
        with self._lock:
            path = self._resolve(room_id, rel_path)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8", newline="") as fh:
                fh.write(content)

    def create_file(self, room_id: str, rel_path: str):
        with self._lock:
            path = self._resolve(room_id, rel_path)
            if os.path.exists(path):
                raise FileManagerError(f"Already exists: {rel_path}")
            os.makedirs(os.path.dirname(path), exist_ok=True)
            open(path, "x", encoding="utf-8").close()

    def create_dir(self, room_id: str, rel_path: str):
        with self._lock:
            path = self._resolve(room_id, rel_path)
            if os.path.exists(path):
                raise FileManagerError(f"Already exists: {rel_path}")
            os.makedirs(path)

    def delete(self, room_id: str, rel_path: str):
        with self._lock:
            path = self._resolve(room_id, rel_path)
            if path == self.project_path(room_id):
                raise FileManagerError("Cannot delete the project root via DELETE")
            if os.path.isdir(path):
                shutil.rmtree(path)
            elif os.path.isfile(path):
                os.remove(path)
            else:
                raise FileManagerError(f"Not found: {rel_path}")

    def rename(self, room_id: str, rel_path: str, new_name: str):
        if not new_name or "/" in new_name or "\\" in new_name:
            raise FileManagerError(f"Invalid new name: {new_name!r}")
        with self._lock:
            src = self._resolve(room_id, rel_path)
            if not os.path.exists(src):
                raise FileManagerError(f"Not found: {rel_path}")
            dst = os.path.join(os.path.dirname(src), new_name)
            if os.path.exists(dst):
                raise FileManagerError(f"Already exists: {new_name}")
            os.rename(src, dst)
