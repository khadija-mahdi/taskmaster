import os
import time
from termcolor import colored
from helper import (
    cleanup_failed_process, should_autorestart,
    isalive_process, register_process, log_event
)

class StartHandler:
    def __init__(self, commands_instance):
        self.commands = commands_instance

    def start_process(self, program, indexed_name, is_attach):
        """Start a single process and return its PID and master file descriptor."""
        pid, master_fd = self.commands.run_process_with_pty(program, indexed_name, is_attach)
        print(f"INFO Created: '{indexed_name}' with pid {pid}")
        return pid, master_fd

    def verify_process_startup(self, indexed_name, pid, starttime):
        """Verify if the process starts successfully within the given time."""
        print(f"INFO Waiting {starttime}s to verify '{indexed_name}' is running...")
        time.sleep(starttime)
        return isalive_process(pid)

    def handle_process_failure(self, indexed_name, pid, master_fd, exit_code, starttime, exitcodes, retry_count, out):
        """Handle process failure, including cleanup and notifications."""
        if master_fd:
            try:
                os.close(master_fd)
            except:
                pass

        expected = exit_code in exitcodes if exit_code is not None else False
        msg = (
            f"WARN exited: '{indexed_name}' (exit status {exit_code}; "
            f"{'expected' if expected else 'not expected'}) after {starttime:.1f}s"
        )
        out.append(colored(msg, "yellow"))
        print(msg)

        if not expected:
            self.commands.email_alerter.send_alert(
                subject=f"Process {indexed_name} Failed",
                message=f"Process '{indexed_name}' died unexpectedly with exit code {exit_code} after {starttime:.1f}s",
                severity="ERROR"
            )
            log_event("PROCESS_DIED", f"'{indexed_name}' died unexpectedly with exit code {exit_code}")
        else:
            log_event("PROCESS_EXITED", f"'{indexed_name}' exited with expected code {exit_code}")
            return True

        cleanup_failed_process(indexed_name, pid, self.commands.running_processes, self.commands.process_info)
        return False

    def handle_process_success(self, program, indexed_name, pid, master_fd, retry_count, starttime, out):
        """Handle successful process start, including registration and logging."""
        register_process(self.commands.running_processes, self.commands.process_info,
                        program["name"], indexed_name, pid, retry_count, "RUNNING", master_fd)

        msg = (
            f"INFO success: '{indexed_name}' with pid {pid} entered RUNNING state, "
            f"process has stayed up for > {starttime} seconds\n"
        )
        out.append(colored(msg, "green"))
        print(msg)
        log_event("PROCESS_RUNNING", f"'{indexed_name}' with pid {pid} entered RUNNING state")
        return True

    def handle_fatal_state(self, program, indexed_name, retry_count, out):
        """Handle process entering FATAL state after too many retries."""
        msg = f"\nINFO gave up: '{indexed_name}' entered FATAL state, too many retries\n"
        self.commands.email_alerter.send_alert(
            subject=f"CRITICAL: Process {indexed_name} FATAL",
            message=f"Process '{indexed_name}' entered FATAL state after too many failed restart attempts",
            severity="CRITICAL"
        )
        register_process(self.commands.running_processes, self.commands.process_info,
                        program["name"], indexed_name, 0, retry_count, "FATAL", None)
        out.append(colored(msg, "red"))
        print(msg)

    def start_single_instance(self, program, indexed_name, out, is_attach):
        """Start a single instance of a program with retry logic."""
        startretries = program.get("startretries", 3)
        starttime = program.get("starttime", 1)
        exitcodes = program.get("exitcodes", [0])
        autorestart = should_autorestart(program.get("autorestart", "unexpected"))

        retry_count = 0
        success = False

        while retry_count < startretries + 1 and not success:
            pid = None
            master_fd = None
            try:
                pid, master_fd = self.start_process(program, indexed_name, is_attach)
                alive, exit_code = self.verify_process_startup(indexed_name, pid, starttime)

                if not alive:
                    success = self.handle_process_failure(indexed_name, pid, master_fd, 
                                                        exit_code, starttime, exitcodes, 
                                                        retry_count, out)
                    retry_count += 1
                    if retry_count < startretries + 1 and autorestart and not success:
                        print(f"\nINFO retrying: '{indexed_name}' (attempt {retry_count}/{startretries})")
                        time.sleep(1)
                        continue
                    else:
                        break

                success = self.handle_process_success(program, indexed_name, pid, 
                                                     master_fd, retry_count, starttime, out)

            except Exception as e:
                if master_fd:
                    try:
                        os.close(master_fd)
                    except:
                        pass
                if pid:
                    cleanup_failed_process(indexed_name, pid, self.commands.running_processes, self.commands.process_info)
                retry_count += 1
                err = f"ERR Error starting '{indexed_name}': {e}"
                out.append(colored(err, "red"))
                print(err)
                time.sleep(1)

        if not success:
            self.handle_fatal_state(program, indexed_name, retry_count, out)

        return success

    def program_config(self, program, program_name, out, is_attach):
        """Start configured program instances with retries and tracking."""
        numprocs = program.get("numprocs", 1)
        program["name"] = program_name
        successful_starts = 0

        for i in range(numprocs):
            indexed_name = f"{program_name}_{i:02d}" if numprocs > 1 else program_name
            if self.start_single_instance(program, indexed_name, out, is_attach):
                successful_starts += 1

        if successful_starts == 0:
            out.append(colored(f"FATAL: '{program_name}' could not be started", "red"))
        elif successful_starts < numprocs:
            out.append(
                colored(f"WARNING: Only {successful_starts}/{numprocs} instances of '{program_name}' started", "yellow")
            )

    def handle_existing_instance(self, programs, program_name, out, is_attach):
        """Handle starting an existing program instance."""
        base_program_name = self.commands.process_info[program_name].get('program_name')
        current_state = self.commands.process_info[program_name].get('state')
        print(f"DEBUG: current_state of '{program_name}' is {current_state}")
        
        if current_state == 'RUNNING':
            return "already_running", f"Program '{program_name}' is already running."

        if base_program_name not in programs:
            return "not_found", f"Program config for '{base_program_name}' not found."

        program = programs[base_program_name].copy()
        program["name"] = base_program_name

        if self.start_single_instance(program, program_name, out,is_attach ):
            out.append(colored(f"Successfully restarted '{program_name}'", "green"))
        else:
            out.append(colored(f"Failed to restart '{program_name}'", "red"))
        return "handled", None

    def handle_program_instances(self, programs, program_name, out, is_attach):
        """Handle starting a program's instances."""
        has_instances = False
        started_any = False

        for instance_name, info in self.commands.process_info.items():
            if info.get('program_name') == program_name:
                has_instances = True
                state = info.get('state', 'UNKNOWN')
                if state != 'RUNNING':
                    program = programs[program_name].copy()
                    program["name"] = program_name
                    if self.start_single_instance(program, instance_name, out, is_attach):
                        out.append(colored(f"Started '{instance_name}'", "green"))
                    else:
                        out.append(colored(f"Failed to start '{instance_name}'", "red"))
                    started_any = True

        if not has_instances:
            self.program_config(programs[program_name], program_name, out, is_attach)
            return "new_config", None
        elif not started_any:
            return "all_running", f"Program '{program_name}' is already running (all instances active)."
        
        return "handled", None

    def start_all_programs(self, programs, out, is_attach):
        """Start all configured programs."""
        out.append(colored("Starting all programs...", "cyan"))
        for pname, pdata in programs.items():
            if pname in self.commands.running_processes and self.commands.running_processes.get(pname):
                out.append(f"Program '{pname}' is already running.")
                continue

            self.program_config(pdata, pname, out, is_attach)
            out.append("")

    def start_command(self, programs, program_name=None, is_attach=False):
        """Start one or all programs, or a specific instance."""
        out = []

        if program_name and program_name.lower() != "all":
            if program_name in self.commands.process_info:
                status, message = self.handle_existing_instance(programs, program_name, out, is_attach)
                if status in ["already_running", "not_found"]:
                    return message
            elif program_name in programs:
                status, message = self.handle_program_instances(programs, program_name, out, is_attach)
                if status == "all_running":
                    return message
            else:
                return f"Program '{program_name}' not found."
        else:
            self.start_all_programs(programs, out, is_attach)

        return "\n".join(out) if out else "OK: start"
