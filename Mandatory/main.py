#!/usr/bin/env python3
import os
import sys
from supervisor import Supervisor
from termcolor import colored
from init import init
import argparse
from parse_cli import parseCommandLineArgs, help
import readline


running_processes = {}
def argsparser():
    parser = argparse.ArgumentParser(description="Task Master CLI")
    parser.add_argument(
        '-c', '--config', type=str, default='config_file.yml',
        help='Path to the configuration file (default: config_file.yml)'
    )
    # Accept config file as positional argument as well
    parser.add_argument(
        'config_positional', nargs='?', default=None,
        help='(optional) Path to the configuration file as positional argument'
    )
    args = parser.parse_args()
    return args



def main():
    try:
        args = argsparser()
        programs = init(args.config)
        supervisor = Supervisor(programs, args.config)
        supervisor.supervise(('autostart', ))
        while True:
            user_input = input(colored('taskmaster> ', 'magenta', attrs=['bold']))
            user_input = input(colored('taskmaster> ', 'magenta', attrs=['bold']))
            if user_input:
                result = parseCommandLineArgs(user_input)
                readline.add_history(user_input)
                # print(result)
                supervisor.supervise(result)
                result = parseCommandLineArgs(user_input)
                readline.add_history(user_input)
                supervisor.supervise(result)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
