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






def init(file_path):
    try:
        print(colored("Initializing Task Master CLI...", "yellow"), file_path)
        # return if control+c is pressed
        signal.signal(signal.SIGINT, lambda sig, frame: sys.exit(0))        
        _print_banner()

        programs = ConfigParser.parse_config_file(file_path)
        print(programs["worker"])

        print(colored("Configuration loaded successfully!", "green"))
        print(
            colored(f"Found {len(programs)} program(s): {list(programs.keys())}\n", "cyan"))
        return programs
    except Exception as e:
        print(colored(f"Error during initialization: {e}", "red"), file=sys.stderr)
        sys.exit(1)