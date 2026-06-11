import os
import socket
import threading
from multiprocessing import Process
import time
from core.project_server import ProjectServer

class LoadBalancerServer:
    def __init__(self, host='127.0.0.1', port=5000, root_dir='./projects'):
        self.host = host
        self.port = port
        self.root_dir = root_dir
        self.active_projects = {}
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        if not os.path.exists(self.root_dir):
            os.makedirs(self.root_dir)

    def _get_available_projects(self):
        return [d for d in os.listdir(self.root_dir) if os.path.isdir(os.path.join(self.root_dir, d))]

    def _spin_up_project_process(self, project_name):
        project_server = ProjectServer(project_name, self.host)
        p = Process(target=project_server.start, daemon=True)
        p.start()
        time.sleep(0.2) 
        return project_server.port

    def handle_initial_routing(self, client_socket, client_address):
        try:
            projects = self._get_available_projects()
            if not projects:
                client_socket.sendall("ERR: No projects found in root directory. Goodbye.\n".encode('utf-8'))
                client_socket.close()
                return

            menu = "Available Projects:\n" + "\n".join([f"- {p}" for p in projects]) + "\nEnter project name to connect: "
            client_socket.sendall(menu.encode('utf-8'))
            
            chosen_project = client_socket.recv(1024).decode('utf-8').strip()

            if chosen_project in projects:
                if chosen_project not in self.active_projects:
                    print(f"Project '{chosen_project}' isn't running. Initializing new process...")
                    allocated_port = self._spin_up_project_process(chosen_project)
                    self.active_projects[chosen_project] = allocated_port
                
                target_port = self.active_projects[chosen_project]
                redirect_msg = f"REDIRECT:{self.host}:{target_port}\n"
                client_socket.sendall(redirect_msg.encode('utf-8'))
            else:
                client_socket.sendall("ERR: Invalid project selection. Closing connection.\n".encode('utf-8'))
        
        except Exception as e:
            print(f"Error handling routing for {client_address}: {e}")
        finally:
            client_socket.close()

    def start(self):
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(10)
        print(f"Main Load Balancer Gateway listening on {self.host}:{self.port}...")

        try:
            while True:
                client_socket, client_address = self.server_socket.accept()
                routing_thread = threading.Thread(
                    target=self.handle_initial_routing, 
                    args=(client_socket, client_address)
                )
                routing_thread.start()
        except KeyboardInterrupt:
            print("\nShutting down Load Balancer system.")
        finally:
            self.server_socket.close()