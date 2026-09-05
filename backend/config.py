"""
Zentrale Konfiguration des Backends.
Alle sicherheitsrelevanten Werte kommen aus Umgebungsvariablen (.env),
NIEMALS hart im Code oder im Frontend hinterlegen.
"""
import os
from dotenv import load_dotenv

load_dotenv()


def _require(name: str) -> str:
    value = os.environ.get(name)
    if not value or value.startswith("changeme"):
        raise RuntimeError(
            f"Umgebungsvariable {name} ist nicht gesetzt (siehe .env.example)."
        )
    return value


class Config:
    SECRET_KEY = _require("SECRET_KEY")
    AUTH_USERNAME = _require("AUTH_USERNAME")
    AUTH_PASSWORD_HASH = _require("AUTH_PASSWORD_HASH")
    DEVICE_TOKEN = _require("DEVICE_TOKEN")

    ALLOWED_ORIGIN = os.environ.get("ALLOWED_ORIGIN", "*")

    PC_MAC_ADDRESS = os.environ.get("PC_MAC_ADDRESS", "")
    LAN_BROADCAST_IP = os.environ.get("LAN_BROADCAST_IP", "255.255.255.255")

    UPLOAD_DIR = os.environ.get("UPLOAD_DIR", "uploads")
    MAX_UPLOAD_MB = int(os.environ.get("MAX_UPLOAD_MB", "500"))
    MAX_CONTENT_LENGTH = MAX_UPLOAD_MB * 1024 * 1024

    _ext = os.environ.get("ALLOWED_EXTENSIONS", "").strip()
    ALLOWED_EXTENSIONS = (
        {e.strip().lower() for e in _ext.split(",") if e.strip()} if _ext else None
    )

    # Wie lange (Sekunden) ein Login-Token gueltig ist
    TOKEN_MAX_AGE = 60 * 60 * 12  # 12 Stunden

    # Nach wie vielen Sekunden ohne Heartbeat gilt der PC-Client als offline
    ONLINE_TIMEOUT_SECONDS = 40

    DB_PATH = os.environ.get("DB_PATH", "state.json")
