import os
import shutil
import sys
import time
import signal
import threading
from termcolor import colored


class Commands:
    VALID_CMDS = {"start", "stop", "restart",
                  "status", "reload", "exit", "help"}

    def __init__(self, programs=None, running_processes=None):
        self.programs = programs or {}
        self.running_processes = running_processes if running_processes is not None else {}
        self.process_info = {}
        self.monitor_thread = None
        self.running = True
        self.start_monitoring()

    def get_path(self, path):
        if path is None:
            return None
        _expanded = os.path.expandvars(path)
        return _expanded.replace("$PWD", os.getcwd())

    def start_monitoring(self):
        if self.monitor_thread is None or not self.monitor_thread.is_alive():
            self.monitor_thread = threading.Thread(
                target=self.monitor_processes, daemon=True)
            self.monitor_thread.start()

    def monitor_processes(self):
        while self.running:
            try:
                for program_name, program_config in self.programs.items():
                    pids = list(self.running_processes.get(program_name, []))
                    if not pids:
                        continue

                    for pid in pids[:]:
                        try:
                            os.kill(pid, 0)
                        except ProcessLookupError:
                            self.handle_dead_process(
                                program_name, program_config, pid)
                        except PermissionError:
                            pass

                time.sleep(1)
            except Exception as e:
                print(f"Monitor thread error: {e}")
                time.sleep(5)

    def handle_dead_process(self, program_name, program_config, pid):
        try:
            if pid in self.running_processes.get(program_name, []):
                self.running_processes[program_name].remove(pid)

            try:
                _, exit_status = os.waitpid(pid, os.WNOHANG)
                exit_code = os.WEXITSTATUS(
                    exit_status) if os.WIFEXITED(exit_status) else -1
            except:
                exit_code = -1

            exitcodes = program_config.get('exitcodes', [0, 2])
            if exit_code in exitcodes:
                print(f"exited: {program_name} (exit status {exit_code})")
            else:
                print(
                    f"exited: {program_name} (exit status {exit_code}; not expected)")

            autorestart = program_config.get('autorestart', 'unexpected')

            should_restart = False
            if autorestart == 'always':
                should_restart = True
            elif autorestart == 'never':
                should_restart = False
            elif autorestart == 'unexpected':
                should_restart = exit_code not in exitcodes

            if should_restart:
                process_key = f"{program_name}_{pid}"
                if process_key not in self.process_info:
                    self.process_info[process_key] = {
                        'retries': 0, 'start_time': time.time()}

                startretries = program_config.get('startretries', 3)
                if self.process_info[process_key]['retries'] < startretries:
                    self.process_info[process_key]['retries'] += 1
                    # new_pid = self.restart_single_process(program_name, program_config)
                    self.start_command(self.programs, program_name)
                    print(f"attempted to restart '{program_name}'")
                else:
                    print(
                        f"gave up: {program_name} entered FATAL state, too many start retries too quickly")

        except Exception as e:
            print(
                f"Error handling dead process {pid} for '{program_name}': {e}")

        except Exception as e:
            print(
                f"Error handling dead process {pid} for '{program_name}': {e}")

    def exec_child_process(self, program, program_name):
        os.setsid()
        cmd = self.get_path(program.get('cmd'))
        if not cmd:
            raise Exception(
                f"spawnerr: no command specified for program '{program_name}'")

        parts = cmd.split()
        command_path = parts[0]

        if not os.path.isabs(command_path):
            if not shutil.which(command_path):
                raise Exception(f"spawnerr: can't find command '{command_path}'")
        else:
            if not os.path.exists(command_path):
                raise Exception(f"spawnerr: can't find command '{command_path}'")
            if not os.access(command_path, os.X_OK):
                raise Exception(
                    f"spawnerr: command '{command_path}' is not executable")
                
        workingdir = self.get_path(program.get('workingdir')) or os.getcwd()
        umask = program.get('umask', 0o022)
        os.umask(umask)

        stdout_path = program.get('stdout')
        stderr_path = program.get('stderr')
        if stdout_path:
            try:
                sys.stdout.flush()
                fd_out = os.open(stdout_path, os.O_WRONLY |
                                    os.O_CREAT | os.O_APPEND, 0o666)
                os.dup2(fd_out, sys.stdout.fileno())
            except Exception as e:
                raise Exception(
                    f"spawnerr: can't redirect stdout to '{stdout_path}': {e}")
        if stderr_path:
            try:
                sys.stderr.flush()
                fd_err = os.open(stderr_path, os.O_WRONLY |
                                    os.O_CREAT | os.O_APPEND, 0o666)
                os.dup2(fd_err, sys.stderr.fileno())
            except Exception as e:
                raise Exception(
                    f"spawnerr: can't redirect stderr to '{stderr_path}': {e}")

        env = os.environ.copy()
        for k, v in (program.get('env') or {}).items():
            env[k] = str(v)

        try:
            os.chdir(workingdir)
        except Exception as e:
            raise Exception(f"spawnerr: can't chdir to '{workingdir}': {e}")
            

        start_time = program.get('starttime', 0)
        if start_time > 0:
            time.sleep(start_time)

        try:
            os.execvpe(parts[0], parts, env)
        except OSError as e:
            raise Exception(f"spawnerr: failed to execute '{parts[0]}': {e}")
        except Exception as e:
            raise Exception(f"spawnerr: execution error for '{parts[0]}': {e}")

    def program_config(self, program, program_name, out):
        """Fork and exec configured program instances; append human-readable
        log lines to the `out` list which will be returned to the client.
        """
        try:
            numprocs = program.get('numprocs', 1)
            self.running_processes.setdefault(program_name, [])

            for index in range(numprocs):
                startretries = program.get('startretries', 3)
                retry_count = 0
                success = False

                while retry_count <= startretries and not success:
                    try:
                        pid = os.fork()
                        if pid == 0:
                            try:
                                self.exec_child_process(program, program_name)
                            except Exception as e:
                                print(e)
                                exit(1)
                                
                                
                        else:
                            # First quick check to see if process started
                            time.sleep(0.1)  # Brief initial wait
                            try:
                                os.kill(pid, 0)
                                print(f"Process {pid} alive after 0.1s")
                            except ProcessLookupError:
                                print(f"Process {pid} died immediately")
                                retry_count += 1
                                if retry_count <= startretries:
                                    out.append(colored(
                                        f"spawnerr: '{program_name}' process died immediately, retrying ({retry_count}/{startretries})", 'yellow'))
                                    print(
                                        f"spawnerr: '{program_name}' process died immediately, retrying...")
                                    time.sleep(1)
                                    continue
                                else:
                                    out.append(colored(
                                        f"gave up: {program_name} entered FATAL state, too many start retries too quickly", 'red'))
                                    print(
                                        f"gave up: {program_name} entered FATAL state, too many start retries too quickly")
                                    success = False
                                    break
                            
                            start_time = program.get('starttime', 0)
                            validation_time = max(1, start_time + 1)
                            print(
                                f'Waiting {validation_time}s for program {program_name} to start')
                            time.sleep(validation_time)

                            # Check if process is still alive
                            try:
                                os.kill(pid, 0)
                                # Give it a bit more time to make sure it's stable
                                time.sleep(0.5)
                                os.kill(pid, 0)

                                self.running_processes[program_name].append(
                                    pid)
                                out.append(
                                    f"spawned: '{program_name}' with pid {pid}")
                                print(
                                    f"spawned: '{program_name}' with pid {pid}")
                                success = True
                                process_key = f"{program_name}_{pid}"
                                self.process_info[process_key] = {
                                    'retries': 0, 'start_time': time.time()}
                            except ProcessLookupError:
                                # Clean up zombie process
                                try:
                                    _, exit_status = os.waitpid(pid, os.WNOHANG)
                                    if os.WIFEXITED(exit_status):
                                        exit_code = os.WEXITSTATUS(exit_status)
                                        if exit_code != 0:
                                            print(f"Process {pid} exited with code {exit_code}")
                                except:
                                    pass
                                
                                retry_count += 1
                                if retry_count <= startretries:
                                    out.append(colored(
                                        f"spawnerr: '{program_name}' process died during startup, retrying ({retry_count}/{startretries})", 'yellow'))
                                    print(
                                        f"spawnerr: '{program_name}' process died during startup, retrying...")
                                    time.sleep(1)
                                else:
                                    out.append(colored(
                                        f"gave up: {program_name} entered FATAL state, too many start retries too quickly", 'red'))
                                    print(
                                        f"gave up: {program_name} entered FATAL state, too many start retries too quickly")
                                    success = False  # Ensure we exit the retry loop
                    except Exception as e:
                        retry_count += 1
                        if retry_count <= startretries:
                            out.append(
                                f"spawnerr: error starting '{program_name}', retrying ({retry_count}/{startretries}): {e}")
                            print(f"spawnerr: error starting '{program_name}', retrying: {e}")
                            time.sleep(1)
                        else:
                            out.append(colored(
                                f"gave up: {program_name} entered FATAL state, failed to start after {startretries} retries: {e}", 'red'))
                            print(colored(
                                f"gave up: {program_name} entered FATAL state, failed to start after {startretries} retries: {e}", 'red'))
                            success = False  # Ensure we exit the retry loop

        except Exception as e:
            out.append(
                colored(f"Error configuring program '{program_name}': {e}", 'red'))

    def start_command(self, programs, program_name=None):
        out = []
        if program_name in self.running_processes and self.running_processes.get(program_name):
            return f"Program '{program_name}' is already running."
        if program_name and program_name.lower() != 'all':
            if program_name in programs:
                self.program_config(programs[program_name], program_name, out)
            else:
                out.append(
                    colored(f"Program '{program_name}' not found.", 'red'))
        else:
            out.append(colored("Starting all programs...", 'cyan'))
            for pname, pdata in programs.items():
                self.program_config(pdata, pname, out)
        return "\n".join(out) if out else "OK: start"

    def stop_process(self, pid, stopsignal, stoptime):
        try:
            if isinstance(stopsignal, str):
                stopsignal = getattr(signal, f'SIG{stopsignal}', getattr(
                    signal, stopsignal, signal.SIGTERM))

            os.kill(pid, stopsignal)
            start_wait = time.time()
            while True:
                try:
                    os.kill(pid, 0)
                    if time.time() - start_wait > stoptime:
                        try:
                            os.kill(pid, signal.SIGKILL)
                            print(
                                f"Process {pid} didn't stop gracefully, sent SIGKILL")
                        except Exception:
                            pass
                        break
                    time.sleep(0.1)
                except ProcessLookupError:
                    break
        except ProcessLookupError:
            pass
        except PermissionError:
            pass

    def stop_command(self, programs, program_name=None):
        out = []
        if program_name and program_name.lower() != 'all':
            if program_name not in programs:
                out.append(
                    colored(f"Program '{program_name}' not found.", 'red'))
                return "\n".join(out)
            target = {program_name: programs[program_name]}
        else:
            target = programs

        for pname, pdata in target.items():
            pids = list(self.running_processes.get(pname, []))
            if not pids:
                out.append(f"{pname} is already stopped.")
                continue
            stopsignal_name = pdata.get('stopsignal', 'TERM')
            stoptime = pdata.get('stoptime', 5)
            if isinstance(stopsignal_name, str):
                stopsignal = getattr(signal, f'SIG{stopsignal_name}', getattr(
                    signal, stopsignal_name, signal.SIGTERM))
            else:
                stopsignal = stopsignal_name

            out.append(
                f"Stopping program '{pname}' with signal {stopsignal_name}...")
            for pid in pids:
                print(f"waiting for {pname} to stop...")
                self.stop_process(pid, stopsignal, stoptime)

            self.running_processes[pname] = []
            out.append(f"Program '{pname}' stopped.")
            print(f"Program '{pname}' stopped.")

        return "\n".join(out)

    def status_command(self, programs):
        out = []
        out.append(colored("Program status:", 'cyan', attrs=['underline']))
        for pname, pdata in programs.items():
            pids = list(self.running_processes.get(pname, []))
            if not pids:
                out.append(f"- {pname}: {colored('STOPPED', 'red')}")
            else:
                running_pids = []
                dead_pids = []
                for pid in pids:
                    try:
                        os.kill(pid, 0)
                        running_pids.append(pid)
                    except ProcessLookupError:
                        dead_pids.append(pid)

                for dead_pid in dead_pids:
                    if dead_pid in self.running_processes[pname]:
                        self.running_processes[pname].remove(dead_pid)

                if running_pids:
                    if len(running_pids) == 1:
                        process_key = f"{pname}_{running_pids[0]}"
                        if process_key in self.process_info:
                            uptime = int(
                                time.time() - self.process_info[process_key]['start_time'])
                            out.append(
                                f"- {pname}: {colored('RUNNING', 'green')} (pid {running_pids[0]}, uptime {uptime}s)")
                        else:
                            out.append(
                                f"- {pname}: {colored('RUNNING', 'green')} (pid {running_pids[0]})")
                    else:
                        out.append(
                            f"- {pname}: {colored('RUNNING', 'green')} ({len(running_pids)} processes: {', '.join(map(str, running_pids))})")
                else:
                    recent_failures = [
                        k for k in self.process_info.keys() if k.startswith(f"{pname}_")]
                    if recent_failures:
                        out.append(
                            f"- {pname}: {colored('STOPPED', 'red')} (last process failed)")
                    else:
                        out.append(f"- {pname}: {colored('STOPPED', 'red')}")
                    self.running_processes[pname] = []
        return "\n".join(out)

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
        }.items():
            out.append(colored(f"- {cmd}", 'green') +
                       " " + colored(f": {desc}", 'white'))
        return "\n".join(out)

    def process_command(self, command, program_name=None, programs=None):
        cmd = command.strip().lower()
        if program_name and program_name.lower() == 'all':
            program_name = None

        if cmd == 'start':
            return self.start_command(programs or self.programs, program_name)
        if cmd == 'stop':
            return self.stop_command(programs or self.programs, program_name)
        if cmd == 'restart':
            resp_stop = self.stop_command(
                programs or self.programs, program_name)
            time.sleep(1)
            resp_start = self.start_command(
                programs or self.programs, program_name)
            return resp_stop + "\n" + resp_start
        if cmd == 'status':
            return self.status_command(programs or self.programs)
        if cmd == 'help':
            return self.help()
        if cmd == 'exit':
            return "OK: exit"
        if cmd == 'reload':
            return "OK: reload (not implemented)"

        return f"ERROR: unknown command '{command}'"

    def shutdown(self):
        """Shutdown the commands handler and stop monitoring."""
        self.running = False
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=2)
