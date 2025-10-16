#!/usr/bin/env python3
import socket
import time

def test_commands():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect(('127.0.0.1', 12345))
    
    commands = ['status', 'start test_fail', 'status']
    
    for cmd in commands:
        print(f"\n>>> Sending command: {cmd}")
        sock.sendall(cmd.encode('utf-8'))
        response = sock.recv(4096).decode('utf-8')
        print(f"<<< Response:\n{response}")
        time.sleep(2)  # Wait between commands
    
    sock.close()

if __name__ == "__main__":
    test_commands()