import socket
import sys
import os
import tty
import termios
import select
from termcolor import colored

class TaskmasterCtlClient:
    def __init__(self, host='localhost', port=12345):
        self.host = host
        self.port = port
        self.sock = None

    def connect(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((self.host, self.port))

    def send_command(self, command):
        if not self.sock:
            raise ConnectionError("Not connected to the server.")
        
        self.sock.sendall(command.encode('utf-8'))
        response = self.sock.recv(4096).decode('utf-8')
        return response

    def close(self):
        if self.sock:
            self.sock.close()
            self.sock = None
            
    def attach(self, program_name):
        """Attach to a running process's console"""
        try:
            self.sock.sendall(f"attach {program_name}".encode('utf-8'))
            response = self.sock.recv(4096).decode('utf-8')
            
            if response.startswith("Error:"):
                print(colored(response, "red"))
                return
            
            if not response.startswith("ATTACH_OK|"):
                print(colored(f"Error: Invalid server response: {response}", "red"))
                return
            
            try:
                pid = int(response.split("|")[1].strip())
            except (IndexError, ValueError):
                print(colored("Error: Invalid process information", "red"))
                return
            
            print(colored(f"\n=== Attached to {program_name} (pid {pid}) ===", "green"))
            print(colored("Press Ctrl+D or Ctrl+C to detach\n", "yellow"))
            
            # Save terminal settings
            try:
                old_settings = termios.tcgetattr(sys.stdin.fileno())
            except termios.error:
                print(colored("Error: Not running in a terminal", "red"))
                return
            
            try:
                tty.setraw(sys.stdin.fileno())
                self.sock.setblocking(False)
                
                detached = False
                buffer = ""  
                
                while not detached:
                    readable, _, _ = select.select([sys.stdin, self.sock], [], [], 0.1)
                    
                    if sys.stdin in readable:
                        try:
                            char = os.read(sys.stdin.fileno(), 1)
                            
                            if char in (b'\x04', b'\x03'):  # Ctrl+D or Ctrl+C
                                detached = True
                                break
                            
                            # Send character to server
                            cmd = f"process_input {program_name} {char.hex()}"
                            try:
                                self.sock.sendall(cmd.encode('utf-8'))
                            except (socket.error, BrokenPipeError):
                                detached = True
                                break
                                
                        except OSError:
                            detached = True
                            break
                    
                    # Handle process output
                    if self.sock in readable:
                        try:
                            data = self.sock.recv(4096)
                            if not data:
                                detached = True
                                break
                            
                            # Add received data to buffer
                            buffer += data.decode('utf-8')
                            
                            # Process all complete messages (delimited by \n)
                            while '\n' in buffer:
                                line, buffer = buffer.split('\n', 1)
                                line = line.strip()
                                
                                if not line:
                                    continue
                                
                                if line.startswith("output:"):
                                    hex_data = line[7:]
                                    try:
                                        output = bytes.fromhex(hex_data)
                                        sys.stdout.buffer.write(output)
                                        sys.stdout.buffer.flush()
                                    except ValueError:
                                        # Invalid hex, skip it
                                        pass
                                        
                                elif line == "terminated":
                                    print(colored("\n[Process terminated]", "red"))
                                    detached = True
                                    break
                                
                        except socket.error as e:
                            if e.errno not in (11, 35):  # Not EAGAIN/EWOULDBLOCK
                                detached = True
                                break
                        except UnicodeDecodeError:
                            continue
            
            finally:
                # Restore terminal settings
                try:
                    termios.tcsetattr(sys.stdin.fileno(), termios.TCSADRAIN, old_settings)
                except:
                    pass
                
                print(colored(f"\n=== Detached from {program_name} ===\n", "yellow"))
                
                # Close and reconnect
                try:
                    self.sock.setblocking(True)
                    self.sock.sendall(f"detach {program_name}".encode('utf-8'))
                    self.sock.close()
                except:
                    pass
                
                # Reconnect for next commands
                try:
                    self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    self.sock.connect((self.host, self.port))
                except Exception as e:
                    print(colored(f"Warning: Could not reconnect: {e}", "yellow"))
        
        except Exception as e:
            print(colored(f"Error during attach: {e}", "red"))
        
        
            