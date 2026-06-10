import socket

def run_client():
    gateway_host = '127.0.0.1'
    gateway_port = 5000

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((gateway_host, gateway_port))
    
    menu = s.recv(1024).decode('utf-8')
    print(menu, end="")
    
    choice = input()
    s.sendall(choice.encode('utf-8'))
    
    response = s.recv(1024).decode('utf-8')
    s.close()
    
    if "REDIRECT" in response:
        _, target_host, target_port = response.strip().split(":")
        target_port = int(target_port)
        
        print(f"\nRouting to isolated Project Server process at {target_host}:{target_port}...")
        
        project_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        project_socket.connect((target_host, target_port))
        
        welcome = project_socket.recv(1024).decode('utf-8')
        print(welcome.strip())
        
        while True:
            msg = input(f"[{choice}] > ")
            if msg.lower() in ['exit', 'quit']:
                break
            project_socket.sendall(msg.encode('utf-8'))
            reply = project_socket.recv(1024).decode('utf-8')
            print(reply.strip())
            
        project_socket.close()
    else:
        print(f"Server rejected request: {response}")

if __name__ == "__main__":
    run_client()