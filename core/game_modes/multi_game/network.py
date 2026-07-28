# core/game_modes/multi_game/network.py

"""Transporte TCP. Sus hilos solo encolan mensajes; nunca tocan Pygame."""

import queue
import socket
import threading

from .protocol import extract_messages, send_framed


class NetworkManager:
    def __init__(self, host, server_ip, port):
        self.host = host
        self.server_ip = server_ip
        self.port = port
        self.incoming = queue.Queue()
        self.listening = True
        self.server_socket = None
        self.client_socket = None
        self.client_sockets = []
        self.clients_lock = threading.Lock()
        self.connection_error = None

    def start(self):
        try:
            if self.host:
                self._start_host()
            else:
                self._start_client()
            return True
        except OSError as error:
            # No propagar la excepción: LobbyScreen la muestra al jugador.
            self.connection_error = f"{type(error).__name__}: {error}"
            self.close()
            return False

    def _start_host(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind(("0.0.0.0", self.port))
        self.server_socket.listen(8)
        print(f"[Multiplayer] Servidor TCP escuchando en 0.0.0.0:{self.port}")
        threading.Thread(target=self._accept_clients, daemon=True).start()

    def _start_client(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((self.server_ip, self.port))
        self.client_socket = sock
        print(f"[Multiplayer] Conectado al host {self.server_ip}:{self.port}")
        threading.Thread(target=self._receive_loop, args=(sock,), daemon=True).start()

    def _accept_clients(self):
        while self.listening:
            try:
                conn, address = self.server_socket.accept()
            except OSError:
                break
            print(f"[Host] Cliente conectado: {address}")
            with self.clients_lock:
                self.client_sockets.append(conn)
            threading.Thread(target=self._receive_loop, args=(conn,), daemon=True).start()

    def _receive_loop(self, sock):
        buffer = bytearray()
        while self.listening:
            try:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                buffer.extend(chunk)
                for message in extract_messages(buffer):
                    self.incoming.put((message, sock))
            except (ConnectionResetError, OSError):
                break
            except Exception as error:
                print(f"[Multiplayer] error de recepción: {error}")
                break
        with self.clients_lock:
            if sock in self.client_sockets:
                self.client_sockets.remove(sock)

    def send(self, message, exclude_socket=None):
        if self.host:
            with self.clients_lock:
                sockets = list(self.client_sockets)
            for sock in sockets:
                if sock is exclude_socket:
                    continue
                try:
                    send_framed(sock, message)
                except OSError:
                    pass
        elif self.client_socket:
            try:
                send_framed(self.client_socket, message)
            except OSError:
                pass

    def send_to(self, sock, message):
        """Envía un mensaje únicamente al cliente asociado a este socket."""
        try:
            send_framed(sock, message)
        except OSError:
            pass            
                    
    def close(self):
        self.listening = False
        for sock in (self.server_socket, self.client_socket):
            try:
                if sock:
                    sock.close()
            except OSError:
                pass
        with self.clients_lock:
            sockets = list(self.client_sockets)
            self.client_sockets.clear()
        for sock in sockets:
            try:
                sock.close()
            except OSError:
                pass
