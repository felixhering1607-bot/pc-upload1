"""
PC-Client
=========
Laeuft dauerhaft (oder per Autostart) auf dem Windows-PC.
Aufgaben:
 - meldet sich regelmaessig ("heartbeat") beim Backend, damit die Webseite
   weiss, dass der PC online ist
 - fragt die Warteschlange ab und laedt neue Dateien herunter
 - speichert sie sicher in DOWNLOAD_DIR
 - bestaetigt erfolgreiche Downloads
 - faehrt den PC optional herunter, wenn das ueber die Webseite angefordert
   wurde UND alle Dateien fertig uebertragen sind
"""
import os
import platform
import re
import subprocess
import threading
import time

import requests

from config import (
    BACKEND_URL,
    DEVICE_TOKEN,
    DOWNLOAD_DIR,
    POLL_INTERVAL_SECONDS,
    HEARTBEAT_INTERVAL_SECONDS,
    ALLOW_AUTO_SHUTDOWN,
    SHUTDOWN_DELAY_SECONDS,
)

HEADERS = {"Authorization": f"Bearer {DEVICE_TOKEN}"}
_INVALID_CHARS = re.compile(r'[\\/:*?"<>|]')


def sanitize_filename(name: str) -> str:
    """Verhindert Path-Traversal und ungueltige Windows-Dateinamen."""
    name = os.path.basename(name)
    name = name.replace("..", "_")
    name = _INVALID_CHARS.sub("_", name)
    return name or "datei_ohne_namen"


def ensure_download_dir():
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)


def heartbeat_loop(status_holder):
    while True:
        try:
            requests.post(
                f"{BACKEND_URL}/api/heartbeat",
                json={"status": status_holder["status"]},
                headers=HEADERS,
                timeout=10,
            )
        except requests.RequestException as exc:
            print(f"[Heartbeat] Fehler: {exc}")
        time.sleep(HEARTBEAT_INTERVAL_SECONDS)


def download_pending_files(status_holder):
    try:
        resp = requests.get(f"{BACKEND_URL}/api/queue", headers=HEADERS, timeout=15)
        resp.raise_for_status()
    except requests.RequestException as exc:
        print(f"[Queue] Fehler beim Abrufen: {exc}")
        return

    queue = resp.json().get("queue", [])
    pending = [item for item in queue if item["status"] != "done"]

    if not pending:
        return

    status_holder["status"] = "transferring"

    for item in pending:
        file_id = item["id"]
        safe_name = sanitize_filename(item["filename"])
        dest_path = os.path.join(DOWNLOAD_DIR, safe_name)
        # Falls Datei bereits existiert, eindeutig machen statt zu ueberschreiben
        base, ext = os.path.splitext(dest_path)
        counter = 1
        while os.path.exists(dest_path):
            dest_path = f"{base}_{counter}{ext}"
            counter += 1

        print(f"Lade herunter: {item['filename']} -> {dest_path}")
        try:
            with requests.get(
                f"{BACKEND_URL}/api/download/{file_id}",
                headers=HEADERS,
                stream=True,
                timeout=60,
            ) as r:
                r.raise_for_status()
                downloaded = 0
                total = item.get("size", 0)
                with open(dest_path, "wb") as f:
                    for chunk in r.iter_content(chunk_size=1024 * 256):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            if total:
                                pct = int(downloaded * 100 / total)
                                print(f"  {item['filename']}: {pct}%", end="\r")
            print(f"  {item['filename']}: 100% - fertig.")

            requests.post(
                f"{BACKEND_URL}/api/confirm/{file_id}", headers=HEADERS, timeout=15
            )
        except requests.RequestException as exc:
            print(f"[Download] Fehler bei {item['filename']}: {exc}")

    status_holder["status"] = "online"


def maybe_shutdown(status_holder):
    if not ALLOW_AUTO_SHUTDOWN:
        return
    try:
        resp = requests.get(
            f"{BACKEND_URL}/api/shutdown-status", headers=HEADERS, timeout=10
        )
        resp.raise_for_status()
    except requests.RequestException as exc:
        print(f"[Shutdown-Check] Fehler: {exc}")
        return

    data = resp.json()
    if data.get("shutdown_requested") and data.get("queue_empty"):
        print(
            f"Shutdown angefordert und Warteschlange leer. "
            f"PC faehrt in {SHUTDOWN_DELAY_SECONDS}s herunter "
            f"(Abbrechen mit: shutdown /a)"
        )
        status_holder["status"] = "done"
        try:
            requests.post(f"{BACKEND_URL}/api/shutdown-ack", headers=HEADERS, timeout=10)
        except requests.RequestException:
            pass

        if platform.system() == "Windows":
            subprocess.run(
                ["shutdown", "/s", "/t", str(SHUTDOWN_DELAY_SECONDS)], check=False
            )
        else:
            print("Nicht unter Windows - Shutdown wird uebersprungen (Testmodus).")


def main():
    ensure_download_dir()
    status_holder = {"status": "online"}

    hb_thread = threading.Thread(
        target=heartbeat_loop, args=(status_holder,), daemon=True
    )
    hb_thread.start()

    print(f"PC-Client gestartet. Zielordner: {DOWNLOAD_DIR}")
    print(f"Backend: {BACKEND_URL}")

    while True:
        download_pending_files(status_holder)
        maybe_shutdown(status_holder)
        time.sleep(POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
