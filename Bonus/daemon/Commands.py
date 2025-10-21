import os
import sys
import time
import signal
from ParseConfige import ConfigParser
from termcolor import colored
import select
from helper import exec_child_process, cleanup_failed_process, cleanup_program, stop_process, should_autorestart, isalive_process, run_process, register_process, log_event
from sendEmail import EmailAlerter


class Commands:
    VALID_CMDS = {"start", "stop", "restart",
                  "status", "reload", "exit", "help", "attach", "detach"}

    def __init__(self, programs=None, running_processes=None):
        self.programs = programs or {}
        self.running_processes = running_processes if running_processes is not None else {}
        self.process_info = {}
        self.running = True

        self.email_alerter = EmailAlerter(
            smtp_server="smtp.gmail.com",
            smtp_port=465,
            username="khadiijamahdii@gmail.com",
            password="femn jshx icni vovr",
            recipients=["khadijamahdi6@gmail.com"]
        )

    # ---------------------------------------------------------------------- #
    #                             PROGRAM CONTROL                            #
    # ---------------------------------------------------------------------- #

    def start_single_instance(self, program, indexed_name, out):
        startretries = program.get("startretries", 3)
        starttime = program.get("starttime", 1)
        exitcodes = program.get("exitcodes", [0])
        autorestart = should_autorestart(
            program.get("autorestart", "unexpected"))

        retry_count = 0
        success = False

        while retry_count < startretries + 1 and not success:
            pid = None
            try:
                pid = run_process(program, indexed_name)

                print(f"INFO Created: '{indexed_name}' with pid {pid}")

                print(
                    f"INFO Waiting {starttime}s to verify '{indexed_name}' is running...")
                time.sleep(starttime)

                alive, exit_code = isalive_process(pid)

                if not alive:
                    expected = exit_code in exitcodes if exit_code is not None else False
                    msg = (
                        f"WARN exited: '{indexed_name}' (exit status {exit_code}; "
                        f"{'expected' if expected else 'not expected'}) after {starttime:.1f}s"
                    )
                    out.append(colored(msg, "yellow"))

                    print(msg)

                    if not expected:
                        self.email_alerter.send_alert(
                            subject=f"Process {indexed_name} Failed",
                            message=f"Process '{indexed_name}' died unexpectedly with exit code {exit_code} after {starttime:.1f}s",
                            severity="ERROR"
                        )
                        log_event(
                            "PROCESS_DIED", f"'{indexed_name}' died unexpectedly with exit code {exit_code}")
                    else:
                        log_event(
                            "PROCESS_EXITED", f"'{indexed_name}' exited with expected code {exit_code}")

                    cleanup_failed_process(
                        indexed_name, pid, self.running_processes, self.process_info)

                    retry_count += 1

                    if retry_count < startretries and autorestart:

                        print(
                            f"\nINFO retrying: '{indexed_name}' (attempt {retry_count}/{startretries})")
                        time.sleep(1)
                        continue
                    else:
                        break

                register_process(self.running_processes, self.process_info,
                                 program["name"], indexed_name, pid, retry_count)

                msg = (
                    f"INFO success: '{indexed_name}' with pid {pid} entered RUNNING state, "
                    f"process has stayed up for > {starttime} seconds\n"
                )
                out.append(colored(msg, "green"))

                print(msg)
                log_event(
                    "PROCESS_RUNNING", f"'{indexed_name}' with pid {pid} entered RUNNING state")
                success = True

            except Exception as e:
                if pid:
                    cleanup_failed_process(
                        indexed_name, pid, self.running_processes, self.process_info)
                retry_count += 1
                err = f"ERR Error starting '{indexed_name}': {e}"
                out.append(colored(err, "red"))

                print(err)
                time.sleep(1)

        if not success:
            msg = f"\nINFO gave up: '{indexed_name}' entered FATAL state, too many retries\n"

            self.email_alerter.send_alert(
                subject=f"CRITICAL: Process {indexed_name} FATAL",
                message=f"Process '{indexed_name}' entered FATAL state after too many failed restart attempts",
                severity="CRITICAL"
            )

            register_process(self.running_processes, self.process_info,
                             program["name"], indexed_name, 0, retry_count, "FATAL")

            out.append(colored(msg, "red"))

            print(msg)

        return success

    def program_config(self, program, program_name, out):
        """Start configured program instances with retries and tracking."""
        numprocs = program.get("numprocs", 1)
        program["name"] = program_name
        successful_starts = 0

        for i in range(numprocs):
            indexed_name = f"{program_name}_{i:02d}" if numprocs > 1 else program_name
            if self.start_single_instance(program, indexed_name, out):
                successful_starts += 1

        if successful_starts == 0:
            out.append(
                colored(f"FATAL: '{program_name}' could not be started", "red"))
        elif successful_starts < numprocs:
            out.append(
                colored(
                    f"WARNING: Only {successful_starts}/{numprocs} instances of '{program_name}' started", "yellow")
            )

    # ---------------------------------------------------------------------- #
    #                              START COMMAND                             #
    # ---------------------------------------------------------------------- #


    def start_command(self, programs, program_name=None):
        """Start one or all programs, or a specific instance."""
        out = []

        if program_name and program_name.lower() != "all":
            # Check if this is a specific instance (e.g., api_01)
            if program_name in self.process_info:
                # This is a specific instance
                base_program_name = self.process_info[program_name].get('program_name')
                current_state = self.process_info[program_name].get('state')
                
                if current_state == 'RUNNING':
                    return f"Program '{program_name}' is already running."
                
                if base_program_name not in programs:
                    return f"Program config for '{base_program_name}' not found."
                
                # Start just this specific instance
                program = programs[base_program_name].copy()
                program["name"] = base_program_name
                
                if self.start_single_instance(program, program_name, out):
                    out.append(colored(f"Successfully restarted '{program_name}'", "green"))
                else:
                    out.append(colored(f"Failed to restart '{program_name}'", "red"))
                    
            # Check if this is a base program name
            elif program_name in programs:
                if program_name in self.running_processes and self.running_processes.get(program_name):
                    return f"Program '{program_name}' is already running."
                
                self.program_config(programs[program_name], program_name, out)
            else:
                out.append(colored(f"Program '{program_name}' not found.", "red"))
        else:
            out.append(colored("Starting all programs...", "cyan"))
            for pname, pdata in programs.items():
                if pname in self.running_processes and self.running_processes.get(pname):
                    out.append(f"Program '{pname}' is already running.")
                    continue

                self.program_config(pdata, pname, out)
                out.append("")

        return "\n".join(out) if out else "OK: start"


    # ---------------------------------------------------------------------- #
    #                               STOP COMMAND                             #
    # ---------------------------------------------------------------------- #

    def stop_command(self, programs, program_name=None):
        out = []
        if program_name and program_name.lower() != 'all':
            if program_name not in self.process_info:
                return f"Program '{program_name}' not found."
            
            base_program_name = self.process_info[program_name].get('program_name')
            target = {base_program_name: programs.get(base_program_name, {})}
        else:
            target = programs

        for pname, pdata in target.items():
            if program_name and program_name.lower() != 'all':
                indexed_name = program_name
                info = self.process_info.get(indexed_name, {})
                pid = info.get('pid')
                
                if not pid or pid == 0:
                    out.append(f"{indexed_name} is already stopped.")
                    print(f"{indexed_name} is already stopped.")
                    continue
                
                pids_to_stop = [(indexed_name, pid)]
            else:
                pids_to_stop = []
                for indexed_name, info in list(self.process_info.items()):
                    if info.get('program_name') == pname:
                        pid = info.get('pid')
                        if pid and pid != 0:
                            pids_to_stop.append((indexed_name, pid))
                
                if not pids_to_stop:
                    out.append(f"{pname} is already stopped.")
                    print(f"{pname} is already stopped.")
                    continue

            stopsignal_name = pdata.get('stopsignal', 'TERM')
            stoptime = pdata.get('stoptime', 5)

            if isinstance(stopsignal_name, str):
                stopsignal_name = stopsignal_name.upper()
                stopsignal = getattr(
                    signal, f"SIG{stopsignal_name}", signal.SIGTERM)
            else:
                stopsignal = stopsignal_name

            if program_name and program_name.lower() != 'all':
                out.append(
                    f"Stopping '{program_name}' with signal {stopsignal_name}...")
                print(
                    f"Stopping '{program_name}' with signal {stopsignal_name}...")
            else:
                out.append(
                    f"Stopping program '{pname}' with signal {stopsignal_name}...")
                print(
                    f"Stopping program '{pname}' with signal {stopsignal_name}...")

            for indexed_name, pid in pids_to_stop:
                print(f"waiting for {indexed_name} (pid {pid}) to stop...")
                stop_process(pid, stopsignal, stoptime)
                
                if indexed_name in self.process_info:
                    self.process_info[indexed_name]['state'] = 'STOPPED'
                    self.process_info[indexed_name]['pid'] = 0

            if program_name is None or program_name.lower() == 'all':
                if pname in self.running_processes:
                    self.running_processes[pname] = []
            else:
                if pname in self.running_processes:
                    self.running_processes[pname] = [
                        p for p in self.running_processes[pname] if p != indexed_name
                    ]
                
            if program_name and program_name.lower() != 'all':
                out.append(f"Process '{program_name}' stopped.")
                print(f"Process '{program_name}' stopped.")
            else:
                out.append(f"Program '{pname}' stopped.")
                print(f"Program '{pname}' stopped.")

        return "\n".join(out)


    # ---------------------------------------------------------------------- #
    #                             STATUS COMMAND                             #
    # ---------------------------------------------------------------------- #

    def status_command(self, programs):
        out = []
        out.append(colored("Program status:", 'cyan', attrs=['underline']))

        for pname, pdata in programs.items():
            numprocs = pdata.get('numprocs', 1)
            has_running = False

            for key, info in sorted(self.process_info.items()):
                if info.get('program_name') == pname:
                    state = info.get('state', 'UNKNOWN')
                    pid = info.get('pid')
                    
                    if state not in ['STOPPED', 'FATAL'] and pid and pid != 0:
                        try:
                            os.kill(pid, 0)
                            state = 'RUNNING'
                            has_running = True
                        except ProcessLookupError:
                            state = 'STOPPED'
                            self.process_info[key]['state'] = 'STOPPED'
                            self.process_info[key]['pid'] = 0

                    if state == 'RUNNING':
                        status_color = 'green'
                        uptime = int(time.time() - info.get('start_time', time.time()))
                        status_str = f"{colored(state, status_color)} (pid {pid}, uptime {uptime}s)"
                    elif state == 'FATAL':
                        status_color = 'red'
                        status_str = colored(state, status_color)
                    elif state == 'STOPPED':
                        status_color = 'red'
                        status_str = colored(state, status_color)
                    else:
                        status_color = 'yellow'
                        status_str = colored(state, status_color)

                    out.append(f"- {key}: {status_str}")
            
            if not self.process_info or not any(info.get('program_name') == pname for info in self.process_info.values()):
                out.append(f"- {pname}: {colored('STOPPED', 'red')}")

        return "\n".join(out)
    
    # ---------------------------------------------------------------------- #
    #                              HELP COMMAND                              #
    # ---------------------------------------------------------------------- #

    def help(self):
        out = [colored("Available commands:", 'cyan', attrs=['underline'])]
        for cmd, desc in {
            "start": "Start the service or process",
            "stop": "Stop the service or process",
            "restart": "Restart the service or process",
            "status": "Show the current status",
            "reload": "Reload the configuration",
            "exit": "Exit the program",
            "help": "Show available commands",
            "attach": "Attach console to running service (view live output)",
            "detach": "Detach from service console (return to command prompt)",
        }.items():
            out.append(colored(f"- {cmd}", 'green') +
                       " " + colored(f": {desc}", 'white'))
        return "\n".join(out)

    # ---------------------------------------------------------------------- #
    #                              RESTART COMMAND                           #
    # ---------------------------------------------------------------------- #

    def restart_command(self, program_name):
        """Helper method to restart a specific program."""
        self.stop_command(self.programs, program_name)
        time.sleep(1)
        return self.start_command(self.programs, program_name)

    # ---------------------------------------------------------------------- #
    #                              RELOAD COMMAND                            #
    # ---------------------------------------------------------------------- #

    def reload_command(self, program_name=None, config_path='config_file.yml'):
        """Reload the configuration and restart affected programs."""
        try:
            new_programs = ConfigParser.parse_config_file(config_path)
            out = []

            if program_name is not None:
                if program_name in new_programs:
                    program_data = new_programs[program_name]
                    if program_name not in self.programs or program_data != self.programs.get(program_name):
                        self.programs[program_name] = program_data
                        out.append(
                            f"Reloading configuration for {program_name}")
                        out.append(self.restart_command(program_name))
                else:
                    if program_name in self.programs:
                        out.append(f"Removing program {program_name}")
                        out.append(self.stop_command(
                            self.programs, program_name))
                        del self.programs[program_name]
                return "\n".join(out) if out else "No changes needed for {program_name}"

            for prog_name, prog_data in new_programs.items():
                if prog_name not in self.programs or prog_data != self.programs.get(prog_name):
                    self.programs[prog_name] = prog_data
                    out.append(f"Reloading configuration for {prog_name}")
                    out.append(self.restart_command(prog_name))

            for prog_name in list(self.programs.keys()):
                if prog_name not in new_programs:
                    out.append(f"Removing program {prog_name}")
                    out.append(self.stop_command(self.programs, prog_name))
                    del self.programs[prog_name]

            return "\n".join(out) if out else "No configuration changes needed"

        except Exception as e:
            return f"Error reloading configuration: {str(e)}"

    # ---------------------------------------------------------------------- #
    #                            Handle COMMANDs                             #
    # ---------------------------------------------------------------------- #

    def process_command(self, command, program_name=None, programs=None, config_path='config_file.yml'):
        cmd = command.strip().lower()
        if program_name and program_name.lower() == 'all':
            program_name = None

        if cmd == 'start':
            return self.start_command(programs or self.programs, program_name)
        if cmd == 'stop':
            return self.stop_command(programs or self.programs, program_name)
        if cmd == 'restart':
            return self.restart_command(program_name)
        if cmd == 'status':
            return self.status_command(programs or self.programs)
        if cmd == 'help':
            return self.help()
        if cmd == 'reload':
            return self.reload_command(program_name=program_name, config_path=config_path)

        return f"ERROR: unknown command '{command}'"
