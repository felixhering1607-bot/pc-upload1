import os
from dotenv import load_dotenv

load_dotenv()

BACKEND_URL = os.environ.get("BACKEND_URL", "https://dein-backend-url.example.com")
DEVICE_TOKEN = os.environ.get("DEVICE_TOKEN", "")
DOWNLOAD_DIR = os.environ.get("PC_DOWNLOAD_DIR", r"C:\Users\felix\Uploads")

POLL_INTERVAL_SECONDS = 5
HEARTBEAT_INTERVAL_SECONDS = 15

# Wenn True, faehrt der PC nach vollstaendiger Uebertragung automatisch
# herunter, sobald das Backend das per /api/shutdown-request angefordert hat.
ALLOW_AUTO_SHUTDOWN = True

# Sicherheits-Verzoegerung (Sekunden) bevor tatsaechlich heruntergefahren wird,
# damit man im Notfall noch abbrechen kann (shutdown /a).
SHUTDOWN_DELAY_SECONDS = 60
