import os
import signal
from termcolor import colored
from helper import stop_process

class StopHandler:
    def __init__(self, commands_instance):
        self.commands = commands_instance

    def get_target_programs(self, programs, program_name):
        """Determine which programs to stop based on input."""
        if program_name and program_name.lower() != 'all':
            if program_name not in self.commands.process_info:
                return None, f"Program '{program_name}' not found."

            base_program_name = self.commands.process_info[program_name].get('program_name')
            return {base_program_name: programs.get(base_program_name, {})}, None
        return programs, None

    def get_pids_to_stop(self, pname, program_name):
        """Get list of PIDs that need to be stopped for a program."""
        if program_name and program_name.lower() != 'all':
            indexed_name = program_name
            info = self.commands.process_info.get(indexed_name, {})
            pid = info.get('pid')
            master_fd = info.get('master_fd')

            if not pid or pid == 0:
                return None, f"{indexed_name} is already stopped."

            return [(indexed_name, pid, master_fd)], None

        pids_to_stop = []
        for indexed_name, info in list(self.commands.process_info.items()):
            if info.get('program_name') == pname:
                pid = info.get('pid')
                master_fd = info.get('master_fd')
                if pid and pid != 0:
                    pids_to_stop.append((indexed_name, pid, master_fd))

        if not pids_to_stop:
            return None, f"{pname} is already stopped."

        return pids_to_stop, None

    def get_stop_signal(self, program_data, isReload=False):
        """Get the stop signal from program configuration."""
        if isReload:
            stopsignal_name = program_data.get('reloadsignal', 'HUP')
            return stopsignal_name, getattr(signal, f"SIG{stopsignal_name.upper()}", signal.SIGHUP)
        stopsignal_name = program_data.get('stopsignal', 'TERM')
        if isinstance(stopsignal_name, str):
            stopsignal_name = stopsignal_name.upper()
            return stopsignal_name, getattr(signal, f"SIG{stopsignal_name}", signal.SIGTERM)
        return stopsignal_name, stopsignal_name

    def stop_processes(self, pids_to_stop, stopsignal, stoptime):
        """Stop a list of processes and clean up their resources."""
        for indexed_name, pid, master_fd in pids_to_stop:
            print(f"waiting for {indexed_name} (pid {pid}) to stop...")
            stop_process(pid, stopsignal, stoptime)

            if master_fd:
                try:
                    os.close(master_fd)
                except:
                    pass

            if indexed_name in self.commands.process_info:
                self.commands.process_info[indexed_name]['state'] = 'STOPPED'
                self.commands.process_info[indexed_name]['pid'] = 0
                self.commands.process_info[indexed_name]['master_fd'] = None

    def update_running_processes(self, pname, program_name, indexed_name):
        """Update the running_processes list after stopping processes."""
        if program_name is None or program_name.lower() == 'all':
            if pname in self.commands.running_processes:
                self.commands.running_processes[pname] = []
        else:
            if pname in self.commands.running_processes:
                self.commands.running_processes[pname] = [
                    p for p in self.commands.running_processes[pname] if p != indexed_name
                ]

    def stop_command(self, programs, program_name=None, isReload=False):
        """Stop one or all programs."""
        out = []
        
        target_programs, error = self.get_target_programs(programs, program_name)
        if error:
            return error

        for pname, pdata in target_programs.items():
            pids_to_stop, error = self.get_pids_to_stop(pname, program_name)
            if error:
                out.append(error)
                print(error)
                continue

            stopsignal_name, stopsignal = self.get_stop_signal(pdata, isReload)
            stoptime = pdata.get('stoptime', 5)

            stop_msg = f"Stopping '{program_name}' with signal {stopsignal_name}..." if program_name and program_name.lower() != 'all' else f"Stopping program '{pname}' with signal {stopsignal_name}..."
            print(stop_msg)

            self.stop_processes(pids_to_stop, stopsignal, stoptime)
            
            self.update_running_processes(pname, program_name, pids_to_stop[0][0] if pids_to_stop else None)

            success_msg = f"Process '{program_name}' stopped." if program_name and program_name.lower() != 'all' else f"Program '{pname}' stopped."
            out.append(success_msg)
            print(success_msg)

        return "\n".join(out)