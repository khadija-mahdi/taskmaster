#!/usr/bin/env python3
import os
import sys
from supervisor import Supervisor
from termcolor import colored
from init import init
import argparse
from parse_cli import parseCommandLineArgs, help
import readline


def argsparser():
    parser = argparse.ArgumentParser(description="Task Master CLI")
    parser.add_argument(
        'config', nargs='?', default='Mandatory/configs/config_file.yml',
        help='(optional) Path to the configuration file as argument'
    )
    args = parser.parse_args()
    return args



def main():
    try:
        args = argsparser()
        programs = init(args.config)
        while True:
            user_input = input(colored('taskmaster> ', 'magenta', attrs=['bold']))
            if user_input:
                result = parseCommandLineArgs(user_input)
                readline.add_history(user_input)
                # print(result)
                supervisor = Supervisor(programs, result)
                # supervisor.supervise()
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
