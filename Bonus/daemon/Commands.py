import os
import sys
import time
import signal
import pty
from ParseConfige import ConfigParser
from termcolor import colored
import select
from helper import exec_child_process
from sendEmail import EmailAlerter
import socket
from reload_handler import ReloadHandler
class Commands:
    VALID_CMDS = {"start", "stop", "restart",
                  "status", "reload", "exit", "help", "attach", "detach"}

    def __init__(self, programs=None, running_processes=None):
        self.programs = programs or {}
        self.running_processes = running_processes if running_processes is not None else {}
        self.process_info = {}
        self.running = True
        self.is_attach = False

        self.email_alerter = EmailAlerter(
            smtp_server="smtp.gmail.com",
            smtp_port=465,
            username="khadiijamahdii@gmail.com",
            password="femn jshx icni vovr",
            recipients=["khadijamahdi6@gmail.com"]
        )

    # ---------------------------------------------------------------------- #
    #                          ATTACH/DETACH COMMANDS                        #
    # ---------------------------------------------------------------------- #

    def monitor_process(self, client_socket, process_info):
        """Monitor process output and send to client"""
        master_fd = process_info.get('master_fd')
        program_name = process_info.get('program_name')

        while process_info.get('attached', False):
            try:
                r, _, _ = select.select([master_fd], [], [], 0.1)
                if master_fd in r:
                    try:
                        output = os.read(master_fd, 4096)
                        if output:
                            response = f"output:{output.hex()}"
                            client_socket.sendall(response.encode('utf-8'))
                        else:
                            client_socket.sendall(b"terminated")
                            break
                    except OSError:
                        client_socket.sendall(b"terminated")
                        break
            except Exception as e:
                print(f"Error monitoring process {program_name}: {e}")
                break

        process_info['attached'] = False

    def verify_attach(self, program_name):
        """Verify if a program can be attached to"""
        try:
            if not program_name:
                return "Error: Program name required"

            if program_name not in self.process_info:
                return f"Error: Program '{program_name}' is not running"

            process_info = self.process_info[program_name]
            master_fd = process_info.get('master_fd')
            pid = process_info.get('pid')

            if not master_fd:
                return f"Error: Process '{program_name}' has no attached terminal"

            if not pid or pid == 0:
                return f"Error: Process '{program_name}' is not running"

            try:
                os.kill(pid, 0)
            except ProcessLookupError:
                return f"Error: Process '{program_name}' (pid {pid}) is not running"

            if process_info.get('attached'):
                return f"ATTACH_OK|{pid}"
            
            self.is_attach = True  # Set is_attach to True when verifying attach command
            return f"ATTACH_OK|{pid}"

        except Exception as e:
            return f"Error: {str(e)}"

    def handle_attached_session(self, program_name, client_socket):
        """Handle an attached session with bidirectional I/O"""
        try:
            process_info = self.process_info[program_name]
            process_info['attached'] = True

            master_fd = process_info.get('master_fd')


            client_socket.setblocking(False)
            self.is_attach = True
            while process_info.get('attached', False):
                try:
                    readable, _, _ = select.select(
                        [master_fd, client_socket], [], [], 0.1)

                    if master_fd in readable:
                        try:
                            output = os.read(master_fd, 4096)
                            if output:
                                hex_output = output.hex()

                                response = f"output:{hex_output}\n"

                                try:
                                    client_socket.sendall(
                                        response.encode('utf-8'))
                                except (BrokenPipeError, socket.error, OSError) as e:
                                    break
                            else:
                                print(f"[DEBUG] Process EOF")
                                try:
                                    client_socket.sendall(b"terminated\n")
                                except:
                                    pass
                                break
                        except OSError as e:
                            try:
                                client_socket.sendall(b"terminated\n")
                            except:
                                pass
                            break

                    if client_socket in readable:
                        try:
                            data = client_socket.recv(4096)
                            if not data:
                                break

                            command = data.decode('utf-8').strip()

                            if command.startswith("process_input "):
                                parts = command.split(' ', 2)
                                if len(parts) == 3:
                                    _, pname, hex_data = parts
                                    try:
                                        input_bytes = bytes.fromhex(hex_data)
                                        os.write(master_fd, input_bytes)
                                    except ValueError as e:
                                        break

                            elif command.startswith("detach "):
                                break

                        except socket.error as e:
                            if e.errno not in (11, 35):
                                break
                        except UnicodeDecodeError as e:
                            continue

                except select.error as e:
                    break
                except Exception as e:
                    import traceback
                    traceback.print_exc()
                    break

        except Exception as e:
            import traceback
            traceback.print_exc()
        finally:
            process_info['attached'] = False
            try:
                client_socket.setblocking(True)
            except:
                pass

    def detach_command(self, program_name):
        """Handle detach request"""
        try:
            if program_name in self.process_info:
                self.process_info[program_name]['attached'] = False
            return "OK"
        except Exception as e:
            return f"Error: {str(e)}"

    def process_input(self, command):
        """Handle input received from client for attached process"""
        try:
            parts = command.split(' ', 2)
            if len(parts) != 3:
                return colored("Error: Invalid input command format", "red")

            _, program_name, hex_data = parts

            if program_name not in self.process_info:
                return colored("Error: Process not found", "red")

            process_info = self.process_info[program_name]
            if not process_info.get('attached'):
                return colored("Error: Not attached to process", "red")

            master_fd = process_info.get('master_fd')
            if not master_fd:
                return colored("Error: Process has no terminal", "red")

            try:
                input_bytes = bytes.fromhex(hex_data)
                os.write(master_fd, input_bytes)
                return "OK"

            except OSError as e:
                process_info['attached'] = False
                return "terminated"

        except ValueError:
            return colored("Error: Invalid hex data", "red")
        except Exception as e:
            return colored(f"Error: {str(e)}", "red")

    # ---------------------------------------------------------------------- #
    #                          MODIFIED RUN_PROCESS                          #
    # ---------------------------------------------------------------------- #

    def run_process_with_pty(self, program, indexed_name, is_attach=False):
        """Run a process in a pseudo-terminal so it can be attached to"""
        master_fd, slave_fd = pty.openpty()
        print(f"Starting process '{indexed_name}' with PID {os.getpid()}")
        pid = os.fork()
        if pid == 0: 
            try:
                os.close(master_fd)

                os.setsid()

                # Redirect stdin, stdout, stderr to slave
                os.dup2(slave_fd, 0)
                os.dup2(slave_fd, 1)
                os.dup2(slave_fd, 2)

                if slave_fd > 2:
                    os.close(slave_fd)
                exec_child_process(program, indexed_name, is_attach)

            except Exception as e:
                print(f"Error in child process: {e}", file=sys.stderr)
                os._exit(1)

        else:  # Parent process
            os.close(slave_fd)
            return pid, master_fd

    # ---------------------------------------------------------------------- #
    #                             PROGRAM CONTROL                            #
    # ---------------------------------------------------------------------- #

    def start_command(self, programs, program_name=None, is_attach=False):
        """Start one or all programs, or a specific instance."""
        from start_handler import StartHandler
        start_handler = StartHandler(self)
        return start_handler.start_command(programs, program_name, is_attach)

    # ---------------------------------------------------------------------- #
    #                               STOP COMMAND                             #
    # ---------------------------------------------------------------------- #

    def stop_command(self, programs, program_name=None, isReload=False):
        """Stop one or all programs."""
        from stop_handler import StopHandler
        stop_handler = StopHandler(self)
        return stop_handler.stop_command(programs, program_name, isReload)

    # ---------------------------------------------------------------------- #
    #                             STATUS COMMAND                             #
    # ---------------------------------------------------------------------- #

    def status_command(self, programs):
        """Display the current status of all programs."""
        from status_handler import StatusHandler
        status_handler = StatusHandler(self)
        return status_handler.status_command(programs)

    # ---------------------------------------------------------------------- #
    #                              HELP COMMAND                              #
    # ---------------------------------------------------------------------- #

    def help(self):
        out = [colored("Available commands:", 'cyan', attrs=['underline'])]
        for cmd, desc in {
            "start [program]": "Start a service or all services",
            "stop [program]": "Stop a service or all services",
            "restart [program]": "Restart a service",
            "status": "Show the current status of all programs",
            "reload [program]": "Reload configuration and restart affected programs",
            "attach <program>": "Attach to a running service (view live output, Ctrl+D to detach)",
            "help": "Show available commands",
            "exit": "Exit taskmasterctl",
        }.items():
            out.append(colored(f"  {cmd:<20}", 'green') +
                       colored(f" {desc}", 'white'))
        return "\n".join(out)

    # ---------------------------------------------------------------------- #
    #                              RESTART COMMAND                           #
    # ---------------------------------------------------------------------- #

    def restart_command(self, program_name):
        """Helper method to restart a specific program."""
        self.stop_command(self.programs, program_name)
        time.sleep(1)
        return self.start_command(self.programs, program_name)

    # ---------------------------------------------------------------------- #
    #                              RELOAD COMMAND                            #
    # ---------------------------------------------------------------------- #

    def reload_command(self, program_name=None, config_path='config_file.yml'):
        reload_handler = ReloadHandler(self)
        return reload_handler.reload_command(program_name, config_path)
    # ---------------------------------------------------------------------- #
    #                            Handle COMMANDs                             #
    # ---------------------------------------------------------------------- #

    def process_command(self, command, program_name=None, programs=None, config_path='config_file.yml', client_socket=None):
        cmd = command.strip().lower()
        if program_name and program_name.lower() == 'all':
            program_name = None

        if cmd == 'start':
            return self.start_command(programs or self.programs, program_name)
        if cmd == 'stop':
            return self.stop_command(programs or self.programs, program_name)
        if cmd == 'restart':
            return self.restart_command(program_name)
        if cmd == 'status':
            return self.status_command(programs or self.programs)
        if cmd == 'help':
            return self.help()
        if cmd == 'reload':
            return self.reload_command(program_name=program_name, config_path=config_path)
        

        return f"ERROR: unknown command '{command}'"
