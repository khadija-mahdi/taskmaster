#!/usr/bin/env python3
import os
import sys
from termcolor import colored
from init import init
import argparse
import time
import signal

running_processes = {}
def argsparser():
    parser = argparse.ArgumentParser(description="Task Master CLI")
    parser.add_argument(
        'config', nargs='?', default='Mandatory/configs/config_file.yml',
        help='(optional) Path to the configuration file as argument'
    )
    args = parser.parse_args()
    return args

commands = {
    "start": "Start the service or process",
    "stop": "Stop the service or process",
    "restart": "Restart the service or process",
    "status": "Show the current status",
    "reload": "Reload the configuration",
    "exit": "Exit the program",
    "help": "Show available commands"
}


def help():
    print(colored("Available commands:", 'cyan', attrs=['underline']))
    for cmd, desc in commands.items():
        print(colored(f"- {cmd}", 'green'), colored(f": {desc}", 'white'))


def parseCommandLineArgs(cmd):
    """
    Parse command line input and return command name and optional argument.
    """
    parts = cmd.strip().split(maxsplit=1)
    cmd_name = parts[0]
    program_name = parts[1] if len(parts) > 1 else None

    if cmd_name not in commands:
        print(colored("Invalid command. Type 'help' to see available commands.", 'red'))
        return None, None

    return cmd_name, program_name


def getPath(path):
    _expanded = os.path.expandvars(path)
    return _expanded.replace("$PWD", os.getcwd())

def program_config(program, program_name):
    try:
        print(colored(f"Starting program '{program_name}'...", 'yellow'))
        numprocs = program.get('numprocs')
        running_processes[program_name] = []
        for index in range(numprocs):
            pid = os.fork()
            if pid == 0:
                os.setsid()
                cmd = getPath(program.get('cmd'))
                print(f"Executing command: {cmd}")
                workingdir = getPath(program.get('workingdir'))
                umask = program.get('umask', 0o022)
                os.umask(umask)
                os.chdir(workingdir)

                # Set up stdout and stderr redirection
                stdout_path = program.get('stdout')
                stderr_path = program.get('stderr')
                if stdout_path:
                    sys.stdout.flush()
                    fd_out = os.open(stdout_path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, umask)
                    os.dup2(fd_out, sys.stdout.fileno())
                if stderr_path:
                    sys.stderr.flush()
                    fd_err = os.open(stderr_path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, umask)
                    os.dup2(fd_err, sys.stderr.fileno())

                # Set environment variables
                env = os.environ.copy()
                for k, v in (program.get('env') or {}).items():
                    env[k] = str(v)

                os.execvpe(cmd.split()[0], cmd.split(), env)
            else:
                running_processes[program_name].append(pid)
                print(f"Forking process {index + 1}/{numprocs} for program '{program_name}'")
    except Exception as e:
        print(
            colored(f"Error configuring program '{program_name}': {e}", 'red'))


def start_command(programs, program_name=None):
    if program_name:
        if program_name in programs:
            program_config(programs[program_name], program_name)
        else:
            print(colored(f"Program '{program_name}' not found.", 'red'))
    else:
        print(colored("Starting all programs...", 'cyan' ))
        for pname, pdata in programs.items():
            program_config(pdata, pname)


def stop_command(programs, program_name=None):
    """
    Stop a specific program or all programs, respecting stopsignal and stoptime.
    """
    def stop_process(pid, stopsignal, stoptime):
        try:
            os.kill(pid, stopsignal)
            start_wait = time.time()
            while True:
                try:
                    os.kill(pid, 0)  # check if process still exists
                    if time.time() - start_wait > stoptime:
                        print(f"Process {pid} did not exit, killing it...")
                        os.kill(pid, signal.SIGKILL)
                        break
                    time.sleep(0.1)
                except ProcessLookupError:
                    # process exited
                    break
        except ProcessLookupError:
            pass
        except PermissionError:
            print(f"Permission denied stopping PID {pid}")

    if program_name:
        if program_name not in programs:
            print(f"Program '{program_name}' not found.")
            return
        target_programs = {program_name: programs[program_name]}
    else:
        target_programs = programs

    for pname, pdata in target_programs.items():
        pids = running_processes.get(pname, [])
        if not pids:
            print(f"{pname} is already stopped.")
            continue

        stopsignal_name = pdata.get('stopsignal', 'TERM')
        stoptime = pdata.get('stoptime', 5)
        stopsignal = getattr(signal, stopsignal_name, signal.SIGTERM)

        print(f"Stopping program '{pname}' with signal {stopsignal_name}...")
        for pid in pids:
            stop_process(pid, stopsignal, stoptime)

        running_processes[pname] = []
        print(f"Program '{pname}' stopped.")

def status_command(programs):
    print(colored("Program status:", 'cyan', attrs=['underline']))
    for pname, pdata in programs.items():
        pids = running_processes.get(pname, [])
        status_list = []
        if not pids:
            status_list.append(colored("STOPPED", 'red'))
        else:
            for pid in pids:
                try:
                    os.kill(pid, 0)  # check if process exists
                    status_list.append(colored("RUNNING", 'green'))
                except ProcessLookupError:
                    status_list.append(colored("STOPPED", 'red'))
        print(f"- {pname}: {', '.join(status_list)}")


def taskmaster(programs, command):
    cmd_name, program_name = parseCommandLineArgs(command)
    if not cmd_name:
        return

    if cmd_name == "start":
        start_command(programs, program_name)
    elif cmd_name == "stop":
        stop_command(programs, program_name)
    elif cmd_name == "status":
        status_command(programs)
    elif cmd_name == "restart":
        stop_command(programs, program_name)
        time.sleep(1)
        start_command(programs, program_name)
    # elif cmd_name == "help":
    #     help()
    elif cmd_name == "exit":
        sys.exit(0)




def main():
    try:
        args = argsparser()
        programs = init(args.config)
        while True:
            user_input = input(colored('taskmaster> ', 'blue', attrs=['bold']))
            if user_input:
                taskmaster(programs, user_input)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
