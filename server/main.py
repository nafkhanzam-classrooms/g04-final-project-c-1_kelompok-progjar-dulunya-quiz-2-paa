import os
from core.load_balancer import LoadBalancerServer

if __name__ == "__main__":
    os.makedirs("./projects/AlphaTask", exist_ok=True)
    os.makedirs("./projects/BetaData", exist_ok=True)
    
    lb = LoadBalancerServer()
    lb.start()