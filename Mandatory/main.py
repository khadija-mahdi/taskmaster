#!/usr/bin/env python3
import os
import sys
from termcolor import colored
from init import init, parseCommandLineArgs
import argparse

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
    # If positional argument is provided, override -c/--config
    if args.config_positional is not None:
        args.config = args.config_positional
    if not os.path.isfile(args.config):
        print(f"Error: Config file '{args.config}' does not exist.", file=sys.stderr)
        sys.exit(1)
    return args

def main():
    try:
        args = argsparser()
        init(args.config)
        while True:
            user_input = input(colored('taskmaster> ', 'blue'))
            if user_input:
                parseCommandLineArgs(user_input)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
