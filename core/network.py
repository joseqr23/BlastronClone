# core/network.py
import socket
import threading
import pickle

class Server:
    def __init__(self, ip='0.0.0.0', port=5000, max_players=4):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.bind((ip, port))
        self.sock.listen(max_players)
        self.clients = []
        self.nicknames = []
        self.partida_config = {}
    
    def broadcast(self, data):
        for client in self.clients:
            try:
                client.send(pickle.dumps(data))
            except:
                pass
    
    def handle_client(self, client):
        while True:
            try:
                data = pickle.loads(client.recv(4096))
                
                # Eventos especiales
                if isinstance(data, dict):
                    if data.get("action") == "join":
                        nickname = data["nickname"]
                        self.nicknames.append(nickname)
                        self.broadcast({"action": "update_players", "players": self.nicknames})
                    elif data.get("action") == "start_game":
                        self.broadcast({"action": "start_game", "config": data["config"]})
                
                else:
                    # Chat u otros mensajes
                    self.broadcast(data)
            except:
                if client in self.clients:
                    index = self.clients.index(client)
                    self.clients.pop(index)
                    if index < len(self.nicknames):
                        self.nicknames.pop(index)
                        self.broadcast({"action": "update_players", "players": self.nicknames})
                break
    
    def run(self):
        print("Servidor corriendo...")
        while True:
            client, addr = self.sock.accept()
            print(f"Conectado: {addr}")
            self.clients.append(client)
            thread = threading.Thread(target=self.handle_client, args=(client,))
            thread.start()


class Client:
    def __init__(self, ip='localhost', port=5000, nickname="Jugador"):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((ip, port))
        self.nickname = nickname
        self.on_update_players = None
        self.on_start_game = None
        
        # Enviar join
        self.send({"action": "join", "nickname": self.nickname})
        
        self.thread = threading.Thread(target=self.receive, daemon=True)
        self.thread.start()
    
    def receive(self):
        while True:
            try:
                data = pickle.loads(self.sock.recv(4096))
                if isinstance(data, dict):
                    if data.get("action") == "update_players" and self.on_update_players:
                        self.on_update_players(data["players"])
                    elif data.get("action") == "start_game" and self.on_start_game:
                        self.on_start_game(data["config"])
                else:
                    print(data)
            except:
                print("Conexión perdida")
                break
    
    def send(self, data):
        self.sock.send(pickle.dumps(data))
