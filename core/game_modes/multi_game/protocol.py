# core/game_modes/multi_game/protocol.py

"""Formato de mensajes TCP: 4 bytes de longitud + JSON UTF-8."""

import json
import struct


def send_framed(sock, message: dict):
    data = json.dumps(message).encode("utf-8")
    sock.sendall(struct.pack("!I", len(data)) + data)


def extract_messages(buffer: bytearray):
    messages = []
    while len(buffer) >= 4:
        (length,) = struct.unpack("!I", buffer[:4])
        if len(buffer) < 4 + length:
            break
        payload = bytes(buffer[4:4 + length])
        del buffer[:4 + length]
        try:
            messages.append(json.loads(payload.decode("utf-8")))
        except json.JSONDecodeError:
            pass
    return messages
