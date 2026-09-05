"""
Erzeugt und verschickt ein Wake-on-LAN "Magic Packet".

WICHTIG (siehe README!): Ein UDP-Broadcast-Paket kommt nur innerhalb
desselben lokalen Netzwerks an. Wird diese Funktion von einem Server im
Internet aufgerufen (z.B. Render/Fly.io), verlaesst das Paket dessen
Rechenzentrums-Netzwerk und erreicht dein Heimnetzwerk NICHT.
Diese Funktion ist deshalb fuer zwei Faelle gedacht:
  1) Das Backend laeuft selbst in deinem Heimnetz (z.B. auf einem
     Raspberry Pi) -> Aufruf funktioniert direkt.
  2) Ein kleines "Relay"-Programm in deinem Heimnetz (relay/relay.py)
     ruft diese Funktion lokal auf, nachdem es vom Cloud-Backend erfahren
     hat, dass ein Wake-Request vorliegt.
"""
import socket


def send_magic_packet(mac_address: str, broadcast_ip: str = "255.255.255.255", port: int = 9):
    mac_clean = mac_address.replace("-", "").replace(":", "").strip().upper()
    if len(mac_clean) != 12:
        raise ValueError(f"Ungueltige MAC-Adresse: {mac_address}")

    mac_bytes = bytes.fromhex(mac_clean)
    magic_packet = b"\xff" * 6 + mac_bytes * 16

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    try:
        sock.sendto(magic_packet, (broadcast_ip, port))
    finally:
        sock.close()
