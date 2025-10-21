#!/usr/bin/env python3
from server import TaskmasterCtlServer
from Commands import Commands
from helper import log_event
import os
import sys
from termcolor import colored
import argparse
import pwd
import signal
from ParseConfige import ConfigParser

commands = None


def argsparser():
    parser = argparse.ArgumentParser(description="Task Master CLI")
    parser.add_argument(
        'config', nargs='?', default='config_file.yml',
        help='(optional) Path to the configuration file as argument'
    )
    parser.add_argument(
        '-d', '--daemon', action='store_true',
        help='Run in daemon mode (background)'
    )
    args = parser.parse_args()
    return args


def _sigint_handler(signum, frame):
    global commands
    print('\n' + colored('Interrupted. Exiting...', 'red'))
    if commands is not None:
        print(colored('Stopping all programs...', 'yellow'))
        commands.stop_command(commands.programs, "all")
    sys.exit(130)


def initialize_server():
    server = TaskmasterCtlServer(host="127.0.0.1", port=12345)
    server.start()
    return server


def load_configuration(config_path):
    programs = ConfigParser.parse_config_file(config_path)
    print(colored("Configuration loaded successfully!", "green"))
    print(colored(f"Found {len(programs)} program(s): {list(programs.keys())}\n", "cyan"))
    return programs


def initialize_commands(programs):
    global commands
    commands = Commands(programs, running_processes={})
    print("taskmasterd Started with PID:", os.getpid())
    log_event("DAEMON_START", f"Taskmaster daemon started with PID {os.getpid()}")
    commands.email_alerter.send_alert(
        subject="Taskmaster Daemon Started",
        message=f"Taskmaster daemon successfully started with PID {os.getpid()}",
        severity="INFO"
    )


def start_autostart_programs(programs, config_path):
    global commands
    for prgm in programs:
        commands.running_processes[prgm] = []
        autostart = programs[prgm].get('autostart', False)
        if autostart is True or (isinstance(autostart, str) and autostart.lower() == 'true'):
            commands.process_command('start', prgm, programs, config_path)


def handle_client_connection(server, client_socket, programs, config_path):
    global commands
    should_exit = False
    
    while True:
        command, program_name = server.handle_client(client_socket)
        if command is None:
            break
        
        response = commands.process_command(command, program_name, programs, config_path)
        
        if response is None:
            if command.lower() == 'exit':
                should_exit = True
                break
            else:
                continue
        
        try:
            client_socket.sendall(response.encode('utf-8'))
        except BrokenPipeError:
            break
        
        if command.lower() == 'exit':
            should_exit = True
            break
    
    client_socket.close()
    return should_exit


def run_server_loop(server, programs, config_path):
    should_exit = False
    
    while not should_exit:
        client_socket = server.accept_connection()
        if client_socket is None:
            continue
        should_exit = handle_client_connection(server, client_socket, programs, config_path)


def shutdown_daemon(reason):
    global commands
    if commands:
        log_event("DAEMON_SHUTDOWN", reason)
        commands.email_alerter.send_alert(
            subject="Taskmaster Daemon Shutdown",
            message=reason,
            severity="WARNING"
        )


def log_daemon_error(error):
    global commands
    if commands:
        log_event("DAEMON_ERROR", f"Taskmaster daemon error: {error}")
        commands.email_alerter.send_alert(
            subject="Taskmaster Daemon Error",
            message=f"Taskmaster daemon encountered an error: {error}",
            severity="CRITICAL"
        )


def drop_privileges(user='nobody'):
    if os.geteuid() != 0:
        print("Warning: Running as non-root, privilege de-escalation skipped")
        return
    try:
        pw_record = pwd.getpwnam(user)
        uid, gid = pw_record.pw_uid, pw_record.pw_gid
        os.setgid(gid)
        os.setuid(uid)
        os.environ['HOME'] = pw_record.pw_dir
        print(f"Dropped privileges to user '{user}' (uid={uid}, gid={gid})")
    except Exception as e:
        print(f"Failed to drop privileges: {e}")
        sys.exit(1)

def main():
    global commands
    server = None
    
    try:
        args = argsparser()
        server = initialize_server()
        drop_privileges('nobody') 
        signal.signal(signal.SIGINT, _sigint_handler)
        
        programs = load_configuration(args.config)
        initialize_commands(programs)
        start_autostart_programs(programs, args.config)
        run_server_loop(server, programs, args.config)
        
        print("Taskmaster daemon shutting down gracefully...")
        shutdown_daemon("Taskmaster daemon shutting down gracefully")
        
    except KeyboardInterrupt:
        print("\nShutting down taskmaster daemon...")
        shutdown_daemon("Taskmaster daemon interrupted and shutting down")
        
    except Exception as e:
        print(f"Error: {e}")
        log_daemon_error(e)


if __name__ == "__main__":
    main()