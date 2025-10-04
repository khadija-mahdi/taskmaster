from termcolor import colored
import sys
import signal
import os
from ParseConfige import ConfigParser



def _print_banner():
    banner = r"""
  _______        _      __  __           _
 |__   __|      | |    |  \/  |         | |
    | | __ _ ___| | __ | \  / | __ _ ___| |_ ___ _ __
    | |/ _` / __| |/ / | |\/| |/ _` / __| __/ _ \ '__|
    | | (_| \__ \   <  | |  | | (_| \__ \ ||  __/ |
    |_|\__,_|___/_|\_\ |_|  |_|\__,_|___/\__\___|_|
"""
    
    banner_lines = banner.split('\n')
    banner_colors = ['magenta', 'cyan', 'yellow',
                     'green', 'blue', 'red', 'white']
    for i, line in enumerate(banner_lines):
        if line.strip():
            color = banner_colors[i % len(banner_colors)]
            print(colored(line, color, attrs=['bold']))
        else:
            print()
    print(colored('★ Welcome to Task Master CLI ★',
          'yellow', attrs=['bold', 'underline']))
    print()


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
    key = cmd.strip()
    if key not in commands:
        print(colored("Invalid command. Type 'help' to see available commands.", 'red'))
        return
    else:
        switcher = {
            "start": lambda: print(colored("Starting...", 'green')),
            "stop": lambda: print(colored("Stopping...", 'yellow')),
            "restart": lambda: print(colored("Restarting...", 'yellow')),
            "status": lambda: print(colored("Status: (not implemented)", 'cyan')),
            "reload": lambda: print(colored("Reloading...", 'green')),
            "exit": lambda: sys.exit(0),
            "help": help
        }
    func = switcher.get(key, lambda: print(colored("Invalid command", 'red')))
    return func()


def _sigint_handler(signum, frame):
    print('\n' + colored('Interrupted. Exiting...', 'red'))
    sys.exit(130)


def init(file_path):
    try:
        signal.signal(signal.SIGINT, _sigint_handler)
        _print_banner()

        programs = ConfigParser.parse_config_file(file_path)

        print(colored("Configuration loaded successfully!", "green"))
        print(
            colored(f"Found {len(programs)} program(s): {list(programs.keys())}\n", "cyan"))
    except Exception as e:
        print(colored(f"Error during initialization: {e}", "red"), file=sys.stderr)
        sys.exit(1)