"""Operational Transformation, server jadi sumber kebenaran.

Server nyimpen 1 copy resmi tiap file (text + version + history op). Tiap edit yang masuk bawa info dia berdasarkan versi berapa, then kalau ada op yang lebih baru, edit-nya di-transform dulu biar nempel di posisi yang bener, baru di-broadcast. Hasilnya semua client jadi sama isinya.

Bentuk op kanonik:
    {"operation": "insert", "position": p, "content": s}
    {"operation": "delete", "position": p, "length": n}
"""

import threading


# transform(a, b): ubah op `a` biar pas diterapin di atas op `b` yang udah masuk duluan (keduanya awalnya dari text yang sama).

def _xf_insert_insert(a, b):
    bp, blen = b["position"], len(b["content"])
    if a["position"] < bp:
        return a
    return {**a, "position": a["position"] + blen}  # posisi sama/di belakang => geser kanan


def _xf_insert_delete(a, b):
    bp, blen = b["position"], b["length"]
    be = bp + blen
    ap = a["position"]
    if ap <= bp:
        return a
    if ap >= be:
        return {**a, "position": ap - blen}
    # titik insert jatuh di dalam area yang dihapus -> taro di awal area itu
    return {**a, "position": bp}


def _xf_delete_insert(a, b):
    bp, blen = b["position"], len(b["content"])
    ap, alen = a["position"], a["length"]
    ae = ap + alen
    if bp <= ap:
        return {**a, "position": ap + blen}
    if bp >= ae:
        return a
    # insert masuk di tengah range yang mau dihapus -> ikut kehapus
    return {**a, "length": alen + blen}


def _xf_delete_delete(a, b):
    bp, blen = b["position"], b["length"]
    be = bp + blen
    ap, alen = a["position"], a["length"]
    ae = ap + alen
    if be <= ap:            # b seluruhnya di kiri a
        return {**a, "position": ap - blen}
    if bp >= ae:            # b seluruhnya di kanan a
        return a
    # ada overlap: buang bagian yang udah dihapus duluan sama b
    overlap = min(ae, be) - max(ap, bp)
    new_pos = min(ap, bp)
    new_len = max(0, alen - overlap)
    return {**a, "position": new_pos, "length": new_len}


def transform(a, b):
    if a["operation"] == "insert" and b["operation"] == "insert":
        return _xf_insert_insert(a, b)
    if a["operation"] == "insert" and b["operation"] == "delete":
        return _xf_insert_delete(a, b)
    if a["operation"] == "delete" and b["operation"] == "insert":
        return _xf_delete_insert(a, b)
    return _xf_delete_delete(a, b)


class Document:
    def __init__(self, text: str = ""):
        self.text = text
        self.version = 0
        self.history = []          # daftar op, history[i] => hasil versi i+1
        self.lock = threading.RLock()


class OTEngine:
    """Nyimpen dokumen yang lagi kebuka, key-nya (room_id, path)."""

    def __init__(self, file_manager=None):
        self.file_manager = file_manager
        self._docs = {}
        self._lock = threading.RLock()

    def _key(self, room_id, path):
        return (room_id, (path or "").replace("\\", "/").strip("/"))

    def get_document(self, room_id, path) -> Document:
        # pertama kali dibuka, load isinya dari disk
        key = self._key(room_id, path)
        with self._lock:
            doc = self._docs.get(key)
            if doc is None:
                text = ""
                if self.file_manager is not None:
                    try:
                        text = self.file_manager.read_file(room_id, path)
                    except Exception:
                        text = ""
                doc = Document(text)
                self._docs[key] = doc
            return doc

    def drop_document(self, room_id, path=None):
        # buang dokumen dari cache setelah file/project dihapus
        with self._lock:
            if path is None:
                for k in [k for k in self._docs if k[0] == room_id]:
                    del self._docs[k]
            else:
                self._docs.pop(self._key(room_id, path), None)

    def _normalize(self, edit: dict, current_text: str) -> dict:
        # ubah packet EDIT (positionS/positionE) jadi op kanonik
        op = edit.get("operation")
        content = edit.get("content", "") or ""
        if op == "append":
            return {"operation": "insert", "position": len(current_text), "content": content}
        if op == "insert":
            return {"operation": "insert", "position": int(edit.get("positionS", 0)), "content": content}
        if op == "delete":
            start = int(edit.get("positionS", 0))
            end = int(edit.get("positionE", start))
            length = end - start
            if length <= 0:
                length = len(content)
            return {"operation": "delete", "position": start, "length": length}
        raise ValueError(f"Unknown edit operation: {op!r}")

    @staticmethod
    def _apply_to_text(text: str, op: dict) -> str:
        if op["operation"] == "insert":
            pos = max(0, min(op["position"], len(text)))
            return text[:pos] + op["content"] + text[pos:]
        # hapus
        pos = max(0, min(op["position"], len(text)))
        end = max(pos, min(pos + op["length"], len(text)))
        return text[:pos] + text[end:]

    def apply_edit(self, room_id: str, path: str, edit: dict):
        """Transform, terapin, simpan 1 edit; balikin (op, version, text)."""
        doc = self.get_document(room_id, path)
        with doc.lock:
            base_version = int(edit.get("version", doc.version))
            base_version = max(0, min(base_version, doc.version))

            op = self._normalize(edit, doc.text)

            # rebase ke semua op yang udah masuk sejak versi acuan client
            for past_op in doc.history[base_version:doc.version]:
                op = transform(op, past_op)

            doc.text = self._apply_to_text(doc.text, op)
            doc.history.append(op)
            doc.version = len(doc.history)

            if self.file_manager is not None:
                try:
                    self.file_manager.write_file(room_id, path, doc.text)
                except Exception:
                    pass

            return op, doc.version, doc.text
