"""
Sehr einfache, dateibasierte Persistenz.
Fuer den persoenlichen Gebrauch (wenige Dateien, ein Nutzer) reicht das aus.
Achtung: Auf manchen kostenlosen Hosting-Plattformen ist das Dateisystem
"ephemeral" -- d.h. bei einem Neustart/Redeploy des Backends geht der
Zustand verloren (siehe README, Abschnitt "Hosting-Hinweise").
"""
import json
import os
import threading
import time
import uuid

_lock = threading.Lock()


class Store:
    def __init__(self, path: str):
        self.path = path
        if not os.path.exists(self.path):
            self._write(
                {
                    "pc_status": "offline",  # offline | starting | online | transferring | done
                    "last_heartbeat": 0,
                    "wake_requested": False,
                    "wake_requested_at": 0,
                    "shutdown_requested": False,
                    "queue": [],       # Dateien, die noch auf den PC-Client warten
                    "completed": [],   # zuletzt uebertragene Dateien (Historie)
                }
            )

    def _read(self):
        with open(self.path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _write(self, data):
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp, self.path)

    def get_state(self):
        with _lock:
            return self._read()

    def set_status(self, status: str):
        with _lock:
            data = self._read()
            data["pc_status"] = status
            self._write(data)

    def heartbeat(self, status: str = "online"):
        with _lock:
            data = self._read()
            data["last_heartbeat"] = time.time()
            data["pc_status"] = status
            self._write(data)

    def request_wake(self):
        with _lock:
            data = self._read()
            data["wake_requested"] = True
            data["wake_requested_at"] = time.time()
            data["pc_status"] = "starting"
            self._write(data)

    def clear_wake_request(self):
        with _lock:
            data = self._read()
            data["wake_requested"] = False
            self._write(data)

    def request_shutdown(self):
        with _lock:
            data = self._read()
            data["shutdown_requested"] = True
            self._write(data)

    def clear_shutdown_request(self):
        with _lock:
            data = self._read()
            data["shutdown_requested"] = False
            self._write(data)

    def add_to_queue(self, filename: str, stored_name: str, size: int) -> str:
        with _lock:
            data = self._read()
            file_id = uuid.uuid4().hex
            data["queue"].append(
                {
                    "id": file_id,
                    "filename": filename,
                    "stored_name": stored_name,
                    "size": size,
                    "status": "pending",  # pending | downloading | done
                    "added_at": time.time(),
                }
            )
            self._write(data)
            return file_id

    def mark_downloading(self, file_id: str):
        with _lock:
            data = self._read()
            for item in data["queue"]:
                if item["id"] == file_id:
                    item["status"] = "downloading"
            data["pc_status"] = "transferring"
            self._write(data)

    def confirm_done(self, file_id: str):
        with _lock:
            data = self._read()
            remaining = []
            for item in data["queue"]:
                if item["id"] == file_id:
                    item["status"] = "done"
                    item["completed_at"] = time.time()
                    data["completed"].insert(0, item)
                    data["completed"] = data["completed"][:20]
                else:
                    remaining.append(item)
            data["queue"] = remaining
            self._write(data)

    def queue_snapshot(self):
        with _lock:
            data = self._read()
            return data["queue"]


def make_store(path: str) -> Store:
    return Store(path)
