from termcolor import colored


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
