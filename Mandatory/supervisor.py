import errno
import os
import signal
import subprocess
import sys
import time
import json

from termcolor import colored

from ParseConfige import ConfigParser


class Supervisor:
    def __init__(self, programs: dict, config_file_name: str):
        self.programs = programs
        self.start_series = {}
        self.child_pids = {}
        self.config_file_name = config_file_name
        self.state_dir = '/tmp/taskmaster_states'
        if not os.path.isdir(self.state_dir):
            try:
                os.makedirs(self.state_dir, exist_ok=True)
            except OSError as e:
                print(f"Failed to create state dir {self.state_dir}: {e}", file=sys.stderr)

    def supervise(self, cmd):
        self.cmd = cmd[0]
        self.arg = cmd[1] if len(cmd) > 1 else None
        
        if self.arg not in self.programs and self.arg is not None and self.arg != "all":
            print(colored(f"Program '{self.arg}' not found in configuration.", "red"))
            return

        if self.cmd == "start":
            self.start(self.arg)
        elif self.cmd == "status":
            self.status(self.arg)
        elif self.cmd == "restart":
            self.restart(self.arg)
        elif self.cmd == "stop":
            self.stop(self.arg)
        elif self.cmd == "reload":
            self.reload(self.arg)
            
        else:
            print("Invalid command")
            
    def start(self, arg, restart=False):
        for key, value in self.programs.items():
            if not (arg == key or (value.get('autostart', True) and arg is None) or arg == "all"):
                continue

            # Initialize start_series on first (non-restart) start or ensure it exists during restart


            for i in range(value.get('numprocs', 1)):
                worker_name = f"{key}:{key}_{i}" if value.get('numprocs', 1) > 1 else key
                if restart:
                    self.start_series[worker_name] -= 1
                if not restart:
                    self.start_series[worker_name] = value.get('startretries', 0)
                else:
                    self.start_series.setdefault(worker_name, value.get('startretries', 0))

                # print(f"restart = {restart}, start_series = {self.start_series}")

                worker_state = self._get_all_worker_states(worker_name)
                if restart and self.start_series.get(worker_name, 0) <= 0 and worker_state and worker_name in worker_state.keys() and worker_state[worker_name]["status"] != "running":
                    # print(f"Max restart attempts reached for {worker_name}. Not restarting.")
                    self._write_worker_state(worker_name, exit_code=1, message="Max restart attempts reached")
                    continue
                if worker_state and worker_name in worker_state.keys() and worker_state[worker_name]["status"] == "running":
                    print(f"{worker_name} is already running")
                    continue
                try:
                    pid = os.fork()
                except OSError as e:
                    print(f"fork failed: {e}")
                    sys.exit(1)
                
                if pid == 0:
                    self._worker(key, worker_name)
                else:
                    self.child_pids[key] = pid
        if self.child_pids:
            self._monitor()

    def status(self, arg):
        for key in self.programs.keys():
            if arg is not None and arg != key:
                continue
            
            # Get all worker states for this program
            worker_states = self._get_all_worker_states(key)
            
            if not worker_states:
                print(f"{key} is not running")
            else:
                for worker_name, state in worker_states.items():
                    if state.get('status') == 'running' and 'pid' in state:
                        print(f"{worker_name} is running with PID {state['pid']}")
                    elif 'message' in state and state['message'] is not None and state['message'] != "":
                        print(f"{worker_name} {state['message']}")
                    elif 'exit_code' in state:
                        print(f"{worker_name} Error exited with code {state['exit_code']}")
                    else:
                        print(f"{worker_name} is not running")

    def restart(self, arg, force=False):
        for key in self.programs.keys():
            if arg is not None and arg != key:
                continue
            self.stop(key, force)
            self.start(key)

    def stop(self, arg, force=False):
        for key in self.programs.keys():
                if arg is not None and arg != key:
                    continue
                
                # Get all worker states for this program
                worker_states = self._get_all_worker_states(key)
                # print(worker_states)
                
                if not worker_states:
                    print(f"{key} is not running")
                    continue
                
                # Stop all workers for this program
                for worker_name, state in worker_states.items():
                    if state.get('status') == 'running' and 'pid' in state:
                    # if state.get('status') == 'running' and 'pid' in state:
                        pid = state['pid']
                        try:
                            if force:
                                sig = signal.SIGHUP
                            elif self.programs[key].get('stopsignal'):
                                sig = getattr(signal, f"SIG{self.programs[key]['stopsignal']}", signal.SIGTERM)
                            else:
                                sig = signal.SIGTERM
                            os.kill(pid, sig)
                            time.sleep(1)
                            print(f"Sent {sig.name} to {worker_name} (PID {pid})")
                            self._write_worker_state(worker_name, exit_code=143, message=f"Stopped by {sig.name}")
                            self._remove_worker_state(worker_name)
                        except OSError as e:
                            print(f"Failed to stop {worker_name} (PID {pid}): {e}")
                    else:
                        print(f"{worker_name} is not running")
                        self._remove_worker_state(worker_name)
                        
    
    def reload(self, arg):
        new_programs = ConfigParser.parse_config_file(self.config_file_name)

        # If an argument is provided, only reload that specific program
        if arg is not None:
            # If program exists in new config, update/restart if changed or new
            if arg in new_programs:
                program_data = new_programs[arg]
                if arg not in self.programs or program_data != self.programs.get(arg):
                    self.programs[arg] = program_data
                    self.restart(arg, True)
            # If program was removed from config, stop and delete it
            else:
                if arg in self.programs:
                    self.stop(arg, True)#! send SIGHUP
                    del self.programs[arg]
            return

        # Reload all programs: add/update and restart changed/new programs
        for program_name, program_data in new_programs.items():
            if program_name not in self.programs or program_data != self.programs.get(program_name):
                self.programs[program_name] = program_data
                self.restart(program_name, True)

        # Stop and remove programs that are no longer present in the new config.
        # Iterate over a list copy to avoid "dictionary changed size during iteration".
        for program_name in list(self.programs.keys()):
            if program_name not in new_programs:
                self.stop(program_name, True)
                del self.programs[program_name]


    def _get_all_worker_states(self, program_name):
        """Get all worker state files for a program"""
        worker_states = {}
        
        if not os.path.exists(self.state_dir):
            return worker_states
        
        # Look for all state files matching this program
        for filename in os.listdir(self.state_dir):
            if filename.endswith('.state'):
                worker_name = filename[:-6]  # Remove .state extension
                
                # Check if this state file belongs to the program
                # Handle both single process (program_name) and multi-process (program_name:program_name_0)
                if worker_name == program_name or worker_name.startswith(f"{program_name}:"):
                    state = self._read_worker_state(worker_name)
                    if state:
                        worker_states[worker_name] = state
        
        return worker_states
    
    def _worker(self, worker, worker_name):
        """Execute the program in child process with output redirection"""
        try:
            # test = {}
            # pid = os.getpid()
            
            os.setsid()
            
            try:
                pid2 = os.fork()
                if pid2 > 0:
                    # # First child: monitor the grandchild for a short "start" interval
                    # # pid2 is the grandchild PID. Ensure it stays alive for configured 'starttime' seconds.
                    start_check = self.programs[worker].get('starttime', 0.0)
                    end_time = time.time() + start_check
                    while time.time() < end_time:
                        try:
                            wpid, st = os.waitpid(pid2, os.WNOHANG)
                            if wpid == 0:
                                # grandchild still running, wait a bit and continue monitoring
                                time.sleep(0.1)
                                continue
                            else:
                                # grandchild exited before the start interval elapsed
                                self._write_worker_state(worker_name, exit_code=1, message="Exited toooooo quickly during start")
                                sys.exit(1)
                        except ChildProcessError:
                            # No such child -> treat as exited too quickly
                            self._write_worker_state(worker_name, exit_code=1, message="Exited toooooo quickly during start")

                            sys.exit(1)
                    # # Grandchild survived the start interval -> exit the first child successfully
                    sys.exit(0)
            except OSError as e:
                print(f"Second fork failed: {e}", file=sys.stderr)
                sys.exit(0)

            # Write worker PID to state file
            start_time = time.perf_counter()

            env = os.environ.copy()
            prog_env = self.programs[worker].get('env')
            if isinstance(prog_env, dict):
                for k, v in prog_env.items():
                    env[str(k)] = str(v)
            
            os.chdir(self.programs[worker].get('workingdir', './workir'))
            
            # Reset file creation mask
            os.umask(self.programs[worker].get('umask', 0o022))
            cmd = self.programs[worker]['cmd']
            
            stdout_path = self.programs[worker].get('stdout', f"./logs/{worker_name}_stdout.log")
            stderr_path = self.programs[worker].get('stderr', f"./logs/{worker_name}_stderr.log")
            
            os.makedirs(os.path.dirname(stdout_path) if os.path.dirname(stdout_path) else './logs', exist_ok=True)

            with open(stdout_path, 'a') as stdout_file, open(stderr_path, 'a') as stderr_file:
                process = subprocess.Popen(
                    cmd.split(),
                    stdout=stdout_file,
                    stderr=stderr_file,
                    text=True,
                    env=env
                )
            self._write_worker_state(worker_name=worker_name, pid=process.pid)

            print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - INFO {worker_name} started with pid {process.pid}", file=sys.stdout, flush=True)
            exit_code = process.wait()
            end_time = time.perf_counter()
            status_message = ""
            elapsed_time = end_time - start_time
            
            
            
            if self.programs[worker].get('stoptime') and elapsed_time < self.programs[worker]['stoptime']:
                exit_code = 1
                status_message = "Exited too quickly"
                

            
            
            
            
            
            # Write exit status to state file
            elif exit_code in self.programs[worker_name].get('exitcodes', [0]):
                status_message = f"Exited successfully with code {exit_code}"
            else:
                status_message = f"Exited with code {exit_code}"
            time.sleep(0.1)
            self._write_worker_state(worker_name, exit_code=exit_code, message=status_message)
            
            
            sys.exit(exit_code)

        except Exception as e:

            sys.exit(1)

    def _should_restart(self, worker_name, exit_code):
        """Determine if a worker should be restarted based on its configuration"""
        config = self.programs.get(worker_name)
        if not config:
            return False
        
        autorestart = config.get('autorestart', 'never')
        
        if autorestart == 'always':
            return True
        elif autorestart == 'unexpected':
            expected_exitcodes = config.get('exitcodes', [0])
            return False if exit_code in expected_exitcodes else True
        else:  # 'never'
            return False

    def _monitor(self):
        """Monitor child processes and handle their exit"""
        try:
            while self.child_pids:
                try:
                    pid, status = os.waitpid(-1, 0)  # Changed to blocking wait
                    
                    if os.WIFEXITED(status):
                        exit_code = os.WEXITSTATUS(status)
                    elif os.WIFSIGNALED(status):
                        exit_code = 128 + os.WTERMSIG(status)
                    else:
                        exit_code = 1
                    
                    # Find which program this PID belongs to
                    program_name = None
                    for prog, prog_pid in self.child_pids.items():
                        if prog_pid == pid:
                            program_name = prog
                            break
                    
                    if program_name:
                        del self.child_pids[program_name]
                        if self._should_restart(program_name, exit_code) and self.programs[program_name].get('startretries', 0) > 0:
                            time.sleep(0.5)  # Brief delay before restart
                            self.start(program_name, restart=True)
                        
                except ChildProcessError:
                    # No more children
                    break
                    
        except KeyboardInterrupt:
            print(f"\n{time.strftime('%Y-%m-%d %H:%M:%S')} - Shutting down supervisor...")
            self.stop(None)

    
    def _write_worker_state(self, worker_name, pid=None, exit_code=None, message=None):
        """Write worker state to a file"""
        # print('exit code frm write worker state function = ', exit_code)
        state_file = os.path.join(self.state_dir, f'{worker_name}.state')
        state = {}
        
        # Read existing state if it exists
        if os.path.exists(state_file):
            try:
                with open(state_file, 'r') as f:
                    state = json.load(f)
            except:
                pass
        
        # Update state
        if pid is not None:
            state['pid'] = pid
            state['status'] = 'running'
        if exit_code is not None:
            # print(f"Writing exit code {exit_code} for {worker_name}, and exit message : {message}")  # Debug print
            state['exit_code'] = exit_code
            state['status'] = 'exited'
            state['message'] = message
            state.pop('pid', None)
        
        # Write state
        with open(state_file, 'w') as f:
            json.dump(state, f)
    
    def _remove_worker_state(self, worker_name):
        """Remove worker state file"""
        state_file = os.path.join(self.state_dir, f'{worker_name}.state')
        try:
            # Normalize and ensure we don't remove files outside the state directory
            state_file = os.path.abspath(state_file)
            state_dir_abs = os.path.abspath(self.state_dir)
            try:
                if os.path.commonpath([state_dir_abs, state_file]) != state_dir_abs:
                    print(f"Warning: Attempt to remove file outside state dir: {state_file}", file=sys.stderr)
                    return
            except Exception:
                # If commonpath fails for any reason, bail out safely
                print(f"Warning: Could not verify state file path: {state_file}", file=sys.stderr)
                return

            # Try removing the file without a preceding exists() check to avoid TOCTOU races
            os.remove(state_file)
        except FileNotFoundError:
            # Already removed -> nothing to do
            return
        except PermissionError as e:
            print(f"Warning: Permission denied when removing state file {state_file}: {e}", file=sys.stderr)
        except OSError as e:
            print(f"Warning: Could not remove state file {state_file}: {e}", file=sys.stderr)

    def _read_worker_state(self, worker_name):
        """Read worker state from file"""
        state_file = os.path.join(self.state_dir, f'{worker_name}.state')
        if os.path.exists(state_file):
            try:
                with open(state_file, 'r') as f:
                    state = json.load(f)
                    # Verify if PID is still running
                    if 'pid' in state:
                        try:
                            os.kill(state['pid'], 0)  # Check if process exists
                        except OSError:
                            # Process doesn't exist anymore
                            state['status'] = 'NOT RUNNING'
                            state.pop('pid', None)
                    return state
            except:
                pass
        return None

