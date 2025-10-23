import os
import time
from termcolor import colored

class StatusHandler:
    def __init__(self, commands_instance):
        self.commands = commands_instance

    def check_and_update_process_state(self, key, info):
        """Check the current state of a process and update its status if needed."""
        state = info.get('state', 'UNKNOWN')
        pid = info.get('pid')

        if state not in ['STOPPED', 'FATAL'] and pid and pid != 0:
            try:
                os.kill(pid, 0)
                state = 'RUNNING'
            except ProcessLookupError:
                state = 'STOPPED'
                self.commands.process_info[key]['state'] = 'STOPPED'
                self.commands.process_info[key]['pid'] = 0
                master_fd = self.commands.process_info[key].get('master_fd')
                if master_fd:
                    try:
                        os.close(master_fd)
                    except:
                        pass
                    self.commands.process_info[key]['master_fd'] = None

        return state, pid

    def format_status_string(self, state, pid=None, start_time=None):
        """Format the status string with appropriate colors and information."""
        if state == 'RUNNING':
            status_color = 'green'
            uptime = int(time.time() - (start_time or time.time()))
            return f"{colored(state, status_color)} (pid {pid}, uptime {uptime}s)"
        elif state in ['FATAL', 'STOPPED']:
            status_color = 'red'
            return colored(state, status_color)
        else:
            status_color = 'yellow'
            return colored(state, status_color)

    def get_program_status_lines(self, pname):
        """Get status lines for a specific program."""
        status_lines = []
        has_instances = False

        for key, info in sorted(self.commands.process_info.items()):
            if info.get('program_name') == pname:
                has_instances = True
                state, pid = self.check_and_update_process_state(key, info)
                status_str = self.format_status_string(state, pid, info.get('start_time'))
                status_lines.append(f"- {key}: {status_str}")

        if not has_instances:
            status_lines.append(f"- {pname}: {colored('STOPPED', 'red')}")

        return status_lines

    def status_command(self, programs):
        """Display the current status of all programs."""
        out = []
        out.append(colored("Program status:", 'cyan', attrs=['underline']))

        for pname in programs:
            out.extend(self.get_program_status_lines(pname))

        return "\n".join(out)