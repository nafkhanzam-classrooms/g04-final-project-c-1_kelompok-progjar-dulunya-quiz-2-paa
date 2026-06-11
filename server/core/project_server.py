import os
import socket
import threading

class ProjectServer:
    def __init__(self, project_name, host='127.0.0.1'):
        self.project_name = project_name
        self.host = host
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, 0))
        self.port = self.server_socket.getsockname()[1]
        self.is_running = True

    def start(self):
        self.server_socket.listen(5)
        print(f"[Process {os.getpid()}] Server started for Project '{self.project_name}' on port {self.port}")
        
        try:
            while self.is_running:
                client_socket, client_address = self.server_socket.accept()
                client_thread = threading.Thread(
                    target=self.handle_client, 
                    args=(client_socket, client_address),
                    daemon=True
                )
                client_thread.start()
        except KeyboardInterrupt:
            print(f"Shutting down Project '{self.project_name}' server.")
        finally:
            self.server_socket.close()

    def handle_client(self, client_socket, client_address):
        print(f"[Thread {threading.get_ident()}] Connected to client {client_address} on Project '{self.project_name}'")
        client_socket.sendall(f"Welcome to Project '{self.project_name}' workspace!\n".encode('utf-8'))
        
        while True:
            try:
                data = client_socket.recv(1024)
                if not data:
                    break
                
                message = data.decode('utf-8').strip()
                print(f"[{self.project_name}] Received from {client_address}: {message}")
                
                response = f"Project '{self.project_name}' processed: {message}\n"
                client_socket.sendall(response.encode('utf-8'))
            except ConnectionResetError:
                break

        print(f"Client {client_address} disconnected from Project '{self.project_name}'")
        client_socket.close()