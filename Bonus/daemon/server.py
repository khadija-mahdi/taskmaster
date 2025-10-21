import socket
from termcolor import colored


class TaskmasterCtlServer:
    commands = {
        "start": "Start the service or process",
        "stop": "Stop the service or process",
        "restart": "Restart the service or process",
        "status": "Show the current status",
        "reload": "Reload the configuration",
        "exit": "Exit the program",
        "help": "Show available commands"

    }

    def __init__(self, host='localhost', port=12345):
        self.host = host
        self.port = port
        self.server_socket = None

    def start(self):
        """Start the Taskmaster server to listen for incoming connections."""
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.settimeout(1.0)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)

    def accept_connection(self):
        """Accept a new connection from a client with timeout handling."""
        try:
            client_socket, addr = self.server_socket.accept()
            return client_socket
        except socket.timeout:
            return None

    def handle_client(self, client_socket):
        """Read a single request from a connected client and return the parsed
        command name and optional program name. This function does NOT close
        the socket; the caller is responsible for sending a response and
        closing the socket.
        """
        data = client_socket.recv(4096)
        if not data:
            return None, None

        command = data.decode('utf-8')
        cmd_name, program_name = self.process_command(command)
        return cmd_name, program_name

    def process_command(self, cmd):
        """
        Parse command line input and return command name and optional argument.
        """
        if cmd is None:
            return None, None

        if not cmd.strip():
            return None, None

        parts = cmd.strip().split(maxsplit=1)
        cmd_name = parts[0].lower()
        program_name = parts[1] if len(parts) > 1 else None

        return cmd_name, program_name

    def stop(self):
        """Stop the Taskmaster server."""
        if self.server_socket:
            self.server_socket.close()
            self.server_socket = None
