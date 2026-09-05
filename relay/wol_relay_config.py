import os
from dotenv import load_dotenv

load_dotenv()

BACKEND_URL = os.environ.get("BACKEND_URL", "https://dein-backend-url.example.com")
DEVICE_TOKEN = os.environ.get("DEVICE_TOKEN", "")
PC_MAC_ADDRESS = os.environ.get("PC_MAC_ADDRESS", "2C-F0-5D-5D-37-AA")
LAN_BROADCAST_IP = os.environ.get("LAN_BROADCAST_IP", "255.255.255.255")
