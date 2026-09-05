"""
Backend fuer das persoenliche Datei-Upload-System.
Start lokal:  python app.py
Start prod:   gunicorn app:app
"""
import os
import time

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.utils import secure_filename

from config import Config
from storage import make_store
from auth import (
    require_login,
    require_device,
    check_credentials,
    create_login_token,
)
from wol import send_magic_packet

app = Flask(__name__)
app.config.from_object(Config)
app.config["MAX_CONTENT_LENGTH"] = Config.MAX_CONTENT_LENGTH

# Nur die eigene GitHub-Pages-Domain darf das Backend per Browser ansprechen
CORS(app, origins=[Config.ALLOWED_ORIGIN], supports_credentials=False)

limiter = Limiter(get_remote_address, app=app, default_limits=["200 per hour"])

os.makedirs(Config.UPLOAD_DIR, exist_ok=True)
store = make_store(Config.DB_PATH)


def _allowed_file(filename: str) -> bool:
    if Config.ALLOWED_EXTENSIONS is None:
        return True
    if "." not in filename:
        return False
    ext = filename.rsplit(".", 1)[1].lower()
    return ext in Config.ALLOWED_EXTENSIONS


def _safe_join(directory: str, filename: str) -> str:
    """Schuetzt vor Path-Traversal (../../etc)."""
    safe_name = secure_filename(filename)
    full_path = os.path.abspath(os.path.join(directory, safe_name))
    if not full_path.startswith(os.path.abspath(directory) + os.sep):
        raise ValueError("Ungueltiger Dateiname.")
    return full_path


def _effective_status() -> str:
    """Setzt Status automatisch auf 'offline' zurueck, wenn lange kein Heartbeat kam."""
    state = store.get_state()
    if state["pc_status"] not in ("offline",):
        if time.time() - state.get("last_heartbeat", 0) > Config.ONLINE_TIMEOUT_SECONDS:
            if state["pc_status"] != "starting" or (
                time.time() - state.get("wake_requested_at", 0) > 180
            ):
                store.set_status("offline")
                return "offline"
    return store.get_state()["pc_status"]


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

@app.post("/api/login")
@limiter.limit("10 per minute")
def login():
    data = request.get_json(silent=True) or {}
    username = data.get("username", "")
    password = data.get("password", "")
    if not check_credentials(username, password):
        return jsonify({"error": "Benutzername oder Passwort falsch."}), 401
    token = create_login_token(username)
    return jsonify({"token": token})


# ---------------------------------------------------------------------------
# Status (vom Handy/Browser abgefragt)
# ---------------------------------------------------------------------------

@app.get("/api/status")
@require_login
def get_status():
    state = store.get_state()
    return jsonify(
        {
            "pc_status": _effective_status(),
            "queue": state["queue"],
            "completed": state["completed"],
        }
    )


# ---------------------------------------------------------------------------
# Wake-on-LAN auslösen (vom Handy/Browser)
# ---------------------------------------------------------------------------

@app.post("/api/wake")
@require_login
@limiter.limit("6 per minute")
def wake_pc():
    store.request_wake()

    # Direkter Versuch: funktioniert nur, wenn dieses Backend selbst im
    # selben LAN wie der PC laeuft (z.B. auf einem Raspberry Pi zuhause).
    # Laeuft das Backend in der Cloud, muss stattdessen der Relay-Dienst
    # (relay/relay.py) diesen Wake-Request abholen und lokal ausfuehren.
    direct_attempt_ok = False
    if Config.PC_MAC_ADDRESS:
        try:
            send_magic_packet(Config.PC_MAC_ADDRESS, Config.LAN_BROADCAST_IP)
            direct_attempt_ok = True
        except Exception:
            direct_attempt_ok = False

    return jsonify(
        {
            "message": "Wake-on-LAN angefordert.",
            "direct_broadcast_attempted": direct_attempt_ok,
            "hinweis": (
                "Falls das Backend NICHT in deinem Heimnetzwerk laeuft, "
                "reicht dieser direkte Versuch allein nicht aus - der "
                "WoL-Relay-Dienst in deinem Heimnetz muss laufen und diesen "
                "Request abholen (siehe README)."
            ),
        }
    )


@app.get("/api/wake-status")
@require_device
def wake_status():
    """Wird vom WoL-Relay im Heimnetz abgefragt (poll)."""
    state = store.get_state()
    return jsonify({"wake_requested": state["wake_requested"]})


@app.post("/api/wake-ack")
@require_device
def wake_ack():
    """Der Relay bestaetigt, dass er das Magic Packet lokal verschickt hat."""
    store.clear_wake_request()
    return jsonify({"ok": True})


# ---------------------------------------------------------------------------
# PC-Client: Heartbeat / Online-Status
# ---------------------------------------------------------------------------

@app.post("/api/heartbeat")
@require_device
def heartbeat():
    data = request.get_json(silent=True) or {}
    status = data.get("status", "online")
    if status not in ("online", "transferring", "done"):
        status = "online"
    store.heartbeat(status)
    return jsonify({"ok": True})


# ---------------------------------------------------------------------------
# Upload vom Handy/Browser -> landet zwischengespeichert auf dem Backend
# ---------------------------------------------------------------------------

@app.post("/api/upload")
@require_login
@limiter.limit("30 per minute")
def upload_file():
    if "file" not in request.files:
        return jsonify({"error": "Keine Datei im Request gefunden."}), 400

    f = request.files["file"]
    if f.filename == "":
        return jsonify({"error": "Kein Dateiname."}), 400

    if not _allowed_file(f.filename):
        return jsonify({"error": "Dateityp nicht erlaubt."}), 400

    original_name = f.filename
    stored_name = f"{int(time.time()*1000)}_{secure_filename(original_name)}"
    dest_path = _safe_join(Config.UPLOAD_DIR, stored_name)

    f.save(dest_path)
    size = os.path.getsize(dest_path)

    file_id = store.add_to_queue(original_name, stored_name, size)
    return jsonify({"id": file_id, "filename": original_name, "size": size})


# ---------------------------------------------------------------------------
# PC-Client: Warteschlange abrufen und Dateien herunterladen
# ---------------------------------------------------------------------------

@app.get("/api/queue")
@require_device
def get_queue():
    return jsonify({"queue": store.queue_snapshot()})


@app.get("/api/download/<file_id>")
@require_device
def download_file(file_id):
    item = next((i for i in store.queue_snapshot() if i["id"] == file_id), None)
    if item is None:
        return jsonify({"error": "Datei nicht gefunden."}), 404

    store.mark_downloading(file_id)
    directory = os.path.abspath(Config.UPLOAD_DIR)
    return send_from_directory(
        directory, item["stored_name"], as_attachment=True, download_name=item["filename"]
    )


@app.post("/api/confirm/<file_id>")
@require_device
def confirm_file(file_id):
    item = next((i for i in store.queue_snapshot() if i["id"] == file_id), None)
    if item is None:
        return jsonify({"error": "Datei nicht gefunden."}), 404

    stored_path = _safe_join(Config.UPLOAD_DIR, item["stored_name"])
    store.confirm_done(file_id)
    if os.path.exists(stored_path):
        os.remove(stored_path)
    return jsonify({"ok": True})


# ---------------------------------------------------------------------------
# Shutdown
# ---------------------------------------------------------------------------

@app.post("/api/shutdown-request")
@require_login
def request_shutdown():
    """Wird vom Handy geklickt: 'PC nach Übertragung herunterfahren'."""
    store.request_shutdown()
    return jsonify({"ok": True, "message": "PC wird nach Abschluss der Übertragung heruntergefahren."})


@app.get("/api/shutdown-status")
@require_device
def shutdown_status():
    state = store.get_state()
    return jsonify(
        {
            "shutdown_requested": state["shutdown_requested"],
            "queue_empty": len(state["queue"]) == 0,
        }
    )


@app.post("/api/shutdown-ack")
@require_device
def shutdown_ack():
    store.clear_shutdown_request()
    store.set_status("offline")
    return jsonify({"ok": True})


# ---------------------------------------------------------------------------
# Health-Check (fuer den Testmodus im Frontend)
# ---------------------------------------------------------------------------

@app.get("/api/health")
def health():
    return jsonify({"ok": True, "time": time.time()})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
