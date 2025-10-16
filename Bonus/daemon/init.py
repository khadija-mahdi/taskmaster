from termcolor import colored
import sys
import signal
import os
from ParseConfige import ConfigParser


def _sigint_handler(signum, frame):
    print('\n' + colored('Interrupted. Exiting...', 'red'))
    sys.exit(130)


def init(file_path):
    signal.signal(signal.SIGINT, _sigint_handler)

    programs = ConfigParser.parse_config_file(file_path)

    print(colored("Configuration loaded successfully!", "green"))
    print(
        colored(f"Found {len(programs)} program(s): {list(programs.keys())}\n", "cyan"))
    return programs
