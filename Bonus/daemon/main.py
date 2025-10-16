#!/usr/bin/env python3
from server import TaskmasterCtlServer
from Commands import Commands
import os
import sys
from termcolor import colored
from init import init
import argparse
import time
import signal


def argsparser():
    parser = argparse.ArgumentParser(description="Task Master CLI")
    parser.add_argument(
        'config', nargs='?', default='config_file.yml',
        help='(optional) Path to the configuration file as argument'
    )
    args = parser.parse_args()
    return args


def main():
    try:
        args = argsparser()
        programs = init(args.config)
        commands = Commands(programs, running_processes={})
        print("taskmasterd Started with PID:", os.getpid())
        for prgm in programs:
            commands.running_processes[prgm] = []
            autostart = programs[prgm].get('autostart', False)
            if autostart is True or (isinstance(autostart, str) and autostart.lower() == 'true'):
                resp = commands.process_command('start', prgm, programs)
                pid_list = commands.running_processes.get(prgm, [])
                if resp:
                    print(resp)
                print(colored(f"PIDs: {pid_list}", 'cyan'))
        server = TaskmasterCtlServer(host="127.0.0.1", port=12345)
        server.start()

        while True:
            client_socket = server.accept_connection()
            while True:
                command, program_name = server.handle_client(client_socket)
                if command is None:
                    break
                response = commands.process_command(
                    command, program_name, programs)
                try:
                    client_socket.sendall(response.encode('utf-8'))
                except BrokenPipeError:
                    break
                if command.lower() == 'exit':
                    break
            client_socket.close()
    except KeyboardInterrupt:
        print("\nShutting down taskmaster daemon...")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if 'commands' in locals():
            commands.shutdown()
        if 'server' in locals():
            server.stop()


if __name__ == "__main__":
    main()
