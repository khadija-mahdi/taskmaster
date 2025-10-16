import socket

class TaskmasterCtlClient:
    def __init__(self, host='localhost', port=12345):
        self.host = host
        self.port = port
        self.sock = None

    def connect(self):
        """Establish a connection to the Taskmaster server."""
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((self.host, self.port))

    def send_command(self, command):
        """Send a command to the Taskmaster server and return the response."""
        if not self.sock:
            raise ConnectionError("Not connected to the server.")
        
        self.sock.sendall(command.encode('utf-8'))
        response = self.sock.recv(4096).decode('utf-8')
        return response

    def close(self):
        """Close the connection to the Taskmaster server."""
        if self.sock:
            self.sock.close()
            self.sock = None
