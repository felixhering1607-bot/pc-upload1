"""
WoL-Relay
=========
WARUM DIESES PROGRAMM EXISTIERT (bitte lesen!):

Ein Wake-on-LAN "Magic Packet" ist ein UDP-Broadcast, der NUR innerhalb
des lokalen Netzwerks funktioniert. Ein Cloud-Backend (z.B. auf Render
oder Fly.io gehostet) sitzt in einem fremden Rechenzentrum und kann
diesen Broadcast NICHT in dein Heimnetzwerk schicken - das ist eine
technische Grenze von WoL, keine Einschraenkung dieses Projekts.

Es gibt nur zwei ehrliche Loesungen, um einen komplett ausgeschalteten
PC von unterwegs zu wecken, OHNE eine Portfreigabe am Router einzurichten:

 1) Dein Router unterstuetzt "Wake on LAN aus dem Internet" nativ
    (z.B. manche FRITZ!Box- oder ASUS-Router). Dann brauchst du dieses
    Relay-Skript nicht - konfiguriere stattdessen die Router-Funktion
    und lass /api/wake im Backend ungenutzt bzw. passe wake_pc() an,
    damit es die Router-API aufruft.

 2) Du hast irgendein Geraet, das in deinem Heimnetz DAUERHAFT laeuft
    (Raspberry Pi, ein alter Laptop, eine NAS, ein Smart-Home-Hub mit
    Python-Unterstuetzung). Auf genau diesem Geraet laeuft dieses
    relay.py-Skript. Es fragt regelmaessig das Cloud-Backend, ob ein
    Wake-Request vorliegt, und schickt dann - von INNERHALB deines
    Heimnetzes - das Magic Packet an deinen PC.

Wenn keine der beiden Optionen fuer dich in Frage kommt, ist "PC von
komplett ausgeschaltet aus dem Internet wecken, ohne jede zusaetzliche
Hardware und ohne Router-Konfiguration" technisch NICHT moeglich.
Die realistische Alternative waere dann, den PC gar nicht komplett
auszuschalten, sondern in den Energiesparmodus (Sleep/S3) zu versetzen -
aus dem manche Netzwerkkarten per WoL auch ohne Neustart-Broadcast-
Einschraenkungen zuverlaessiger aufwachen, das Grundproblem (Paket muss
lokal ankommen) bleibt aber bestehen.
"""
import os
import time

import requests
from dotenv import load_dotenv

from wol_relay_config import BACKEND_URL, DEVICE_TOKEN, PC_MAC_ADDRESS, LAN_BROADCAST_IP

load_dotenv()

POLL_INTERVAL_SECONDS = 5


def send_magic_packet(mac_address: str, broadcast_ip: str, port: int = 9):
    import socket

    mac_clean = mac_address.replace("-", "").replace(":", "").strip().upper()
    mac_bytes = bytes.fromhex(mac_clean)
    packet = b"\xff" * 6 + mac_bytes * 16
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    try:
        sock.sendto(packet, (broadcast_ip, port))
    finally:
        sock.close()


def main():
    headers = {"Authorization": f"Bearer {DEVICE_TOKEN}"}
    print("WoL-Relay gestartet. Warte auf Wake-Requests vom Backend...")
    while True:
        try:
            resp = requests.get(f"{BACKEND_URL}/api/wake-status", headers=headers, timeout=10)
            if resp.ok and resp.json().get("wake_requested"):
                print("Wake-Request erhalten -> sende Magic Packet lokal...")
                send_magic_packet(PC_MAC_ADDRESS, LAN_BROADCAST_IP)
                requests.post(f"{BACKEND_URL}/api/wake-ack", headers=headers, timeout=10)
                print("Magic Packet gesendet und bestaetigt.")
        except requests.RequestException as exc:
            print(f"Verbindungsfehler zum Backend: {exc}")

        time.sleep(POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
