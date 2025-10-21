import os
import signal
import subprocess
import sys
import time
import json


class Supervisor:
    def __init__(self, programs: dict):
        self.programs = programs
        self.child_pids = {}
        self.state_dir = '/tmp/taskmaster_states'
        if not os.path.isdir(self.state_dir):
            try:
                os.makedirs(self.state_dir, exist_ok=True)
            except OSError as e:
                print(f"Failed to create state dir {self.state_dir}: {e}", file=sys.stderr)

    def supervise(self, cmd):
        self.cmd = cmd[0]
        self.arg = cmd[1] if len(cmd) > 1 else None

        if self.cmd == "start":
            self.start(self.arg)
        elif self.cmd == "status":
            self.status(self.arg)
        elif self.cmd == "restart":
            self.restart(self.arg)
        elif self.cmd == "stop":
            self.stop(self.arg)
        else:
            print("Invalid command")
            
    def start(self, arg):
        for key, value in self.programs.items():
            if not (arg == key or (value.get('autostart', True) and arg is None)):
                continue
            try:
                pid = os.fork()
            except OSError as e:
                print(f"fork failed: {e}")
                sys.exit(1)
            
            if pid == 0:
                if value.get('numprocs', 1) > 1:
                    for i in range(arg.get('numprocs', 1)):
                        worker_name = f"{key}:{key}_{i}"
                        self._worker(key, worker_name)
                else:
                    self._worker(key, key)
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
                    elif 'exit_code' in state:
                        print(f"{worker_name} exited with code {state['exit_code']}")
                    else:
                        print(f"{worker_name} is not running")

    def restart(self, arg):
        for key in self.programs.keys():
            if arg is not None and arg != key:
                continue
            self.stop(key)
            self.start(key)

    def stop(self, arg):
        for key in self.programs.keys():
                if arg is not None and arg != key:
                    continue
                
                # Get all worker states for this program
                worker_states = self._get_all_worker_states(key)
                
                if not worker_states:
                    print(f"{key} is not running")
                    continue
                
                # Stop all workers for this program
                for worker_name, state in worker_states.items():
                    if state.get('status') == 'running' and 'pid' in state:
                        pid = state['pid']
                        try:
                            if self.programs[key].get('stopsignal'):
                                sig = getattr(signal, f"SIG{self.programs[key]['stopsignal']}", signal.SIGTERM)
                            else:
                                sig = signal.SIGTERM
                            os.kill(pid, sig)
                            print(f"Sent {sig.name} to {worker_name} (PID {pid})")
                        except OSError as e:
                            print(f"Failed to stop {worker_name} (PID {pid}): {e}")

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
            pid = os.getpid()
            
            os.setsid()
            
            try:
                pid2 = os.fork()
                if pid2 > 0:
                    sys.exit(0)  # Exit first child
            except OSError as e:
                print(f"Second fork failed: {e}", file=sys.stderr)
                sys.exit(0)

            # Write worker PID to state file
            start_time = time.perf_counter()
            
            worker_pid = os.getpid()
            self._write_worker_state(worker_name, pid=worker_pid)
            print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - INFO {worker_name} started with pid {worker_pid}")

            env = os.environ.copy()
            for key, value in self.programs[worker]["env"].items():
                env[key] = value
            
            os.chdir(self.programs[worker].get('workingdir', './workir'))
            
            # Reset file creation mask
            os.umask(self.programs[worker].get('umask', 0o022))
            cmd = self.programs[worker]['cmd']
            
            stdout_path = self.programs[worker].get('stdout', f"./logs/{worker_name}_stdout.log")
            stderr_path = self.programs[worker].get('stderr', f"./logs/{worker_name}_stderr.log")
            
            os.makedirs(os.path.dirname(stdout_path) if os.path.dirname(stdout_path) else './logs', exist_ok=True)
            
            # Open files and pass to subprocess
            with open(stdout_path, 'a') as stdout_file, open(stderr_path, 'a') as stderr_file:
                process = subprocess.Popen(
                    cmd.split(),
                    stdout=stdout_file,
                    stderr=stderr_file,
                    text=True,
                    env=env
                )
                
            exit_code = process.wait()
            end_time = time.perf_counter()
            elapsed_time = end_time - start_time
            if self.programs[worker].get('stoptime') and elapsed_time < self.programs[worker]['stoptime']:
                exit_code = 1
            # Write exit status to state file
            self._write_worker_state(worker_name, exit_code=exit_code)
            sys.exit(exit_code)

        except Exception as e:
            self._write_worker_state(worker_name, exit_code=1)
            sys.exit(1)

    def _monitor(self):
        """Monitor child processes and handle their exit"""
        try:
            while self.child_pids:
                try:
                    pid, status = os.waitpid(-1, os.WNOHANG)                    
                    time.sleep(0.5)  # Small sleep to avoid busy waiting
                    
                except ChildProcessError:
                    # No more children
                    break
                    
        except KeyboardInterrupt:
            print(f"\n{time.strftime('%Y-%m-%d %H:%M:%S')} - Shutting down supervisor...")
            self.stop(None)
    
    def _write_worker_state(self, worker_name, pid=None, exit_code=None, message=None):
        """Write worker state to a file"""
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
            state['exit_code'] = exit_code
            state['status'] = 'exited'
            state['message'] = message
            state.pop('pid', None)
        
        # Write state
        with open(state_file, 'w') as f:
            json.dump(state, f)

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










# import os
# import signal
# import subprocess
# import sys
# import time
# import json


# class Supervisor:
#     def __init__(self, programs: dict):
#         self.programs = programs
#         self.child_pids = {}
#         self.state_dir = '/tmp/taskmaster_states'
#         if not os.path.isdir(self.state_dir):
#             try:
#                 os.makedirs(self.state_dir, exist_ok=True)
#             except OSError as e:
#                 print(f"Failed to create state dir {self.state_dir}: {e}", file=sys.stderr)



#     def supervise(self, cmd):
#         self.cmd = cmd[0]
#         self.arg = cmd[1] if len(cmd) > 1 else None

        
#         if self.cmd == "start":
#             self.start(self.arg)
#         elif self.cmd == "status":
#             self.status(self.arg)
#         elif self.cmd == "restart":
#             self.restart(self.arg)
#         elif self.cmd == "stop":
#             self.stop(self.arg)
#         else:
#             print("Invalid command")
            
    
#     def start(self, arg):
#         for key, value in self.programs.items():
#             if not (arg == key or  (value.get('autostart', True) and arg is None)):
#                 continue
#             try:
#                 pid = os.fork()
#             except OSError as e:
#                 print(f"fork failed: {e}")
#                 sys.exit(1)
            
#             if pid == 0:
#                 # for i in range(1):
#                 #!
#                 if value.get('numprocs', 1) > 1:
#                     for i in range(value.get('numprocs', 1)):
#                         worker_name = f"{key}:{key}_{i}"
#                         self._worker(key, worker_name)
#                 else:
#                     self._worker(key, key)
#             else:
#                 self.child_pids[key] = pid
#         if self.child_pids:
#             self._monitor()

#     def status(self, arg):
#         for key in self.programs.keys():
#             if arg is not None and arg != key:
#                 continue
            
#             state = self._read_worker_state(key)
            
#             if state is None:
#                 print(f"{key} is not running")
#             elif state.get('status') == 'running' and 'pid' in state:
#                 print(f"{key} is running with PID {state['pid']}")
#             elif 'exit_code' in state:
#                 print(f"{key} exited with code {state['exit_code']}")
#             else:
#                 print(f"{key} is not running")

#     def restart(self, arg):
#         arg = self._get_program_name(arg)
#         for key in self.programs.keys():
#             if arg is not None and arg != key:
#                 continue
#             self.stop(key)
#             self.start(key)


#     def stop(self, arg):
#         print(self.child_pids)
#         #! if the program has multiple instances with underscores stop them all
#         for key in self.programs.keys():
#             if arg is not None and arg != key:
#                 continue
            
#             state = self._read_worker_state(key)
#             if state and state.get('status') == 'running' and 'pid' in state:
#                 pid = state['pid']
#                 try:
#                     if self.programs[key].get('stopsignal'):
#                         sig = getattr(signal, f"SIG{self.programs[key]['stopsignal']}", signal.SIGTERM)
#                     else:
#                         sig = signal.SIGTERM
#                     os.kill(pid, sig)
#                     print(f"Sent {sig.name} to {key} (PID {pid})")
#                 except OSError as e:
#                     print(f"Failed to stop {key} (PID {pid}): {e}")
#             else:
#                 print(f"{key} is not running")



    
    
#     def _worker(self, worker, worker_name):
#         """Execute the program in child process with output redirection"""
#         try:
#             pid = os.getpid()
            
#             os.setsid()
            
#             try:
#                 pid2 = os.fork()
#                 if pid2 > 0:
#                     sys.exit(0)  # Exit first child
#             except OSError as e:
#                 print(f"Second fork failed: {e}", file=sys.stderr)
#                 sys.exit(0)


#             # Write worker PID to state file
#             start_time = time.perf_counter()
            
#             worker_pid = os.getpid()
#             self._write_worker_state(worker_name, pid=worker_pid)
#             print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - INFO {worker_name} started with pid {worker_pid}")

#             env = os.environ.copy()
#             for key, value in self.programs[worker]["env"].items():
#                 env[key] = value
            
#             os.chdir(self.programs[worker].get('workingdir', './workir'))
            
#             # Reset file creation mask
#             os.umask(self.programs[worker].get('umask', 0o022))
#             cmd = self.programs[worker]['cmd']
            
            
#             stdout_path = self.programs[worker].get('stdout', f"./logs/{worker_name}_stdout.log")
#             stderr_path = self.programs[worker].get('stderr', f"./logs/{worker_name}_stderr.log")
            
#             os.makedirs(os.path.dirname(stdout_path) if os.path.dirname(stdout_path) else './logs', exist_ok=True)
            
#             # Open files and pass to subprocess
#             with open(stdout_path, 'a') as stdout_file, open(stderr_path, 'a') as stderr_file:
#                 process = subprocess.Popen(
#                     cmd.split(),
#                     stdout=stdout_file,   # Direct to file
#                     stderr=stderr_file,   # Direct to file
#                     text=True,
#                     env=env
#                 )
                
#             exit_code = process.wait()
#             end_time = time.perf_counter()
#             elapsed_time = end_time - start_time
#             if self.programs[worker]['stoptime'] and elapsed_time < self.programs[worker]['stoptime']:
#                 exit_code = 1
#             # Write exit status to state file
#             self._write_worker_state(worker_name, exit_code=exit_code)
#             sys.exit(exit_code)

#         except Exception as e:
#             # print(f"Worker {worker} failed: {e}", file=stderr_path)
#             self._write_worker_state(worker_name, exit_code=1)
#             sys.exit(1)





#     def _monitor(self):
#         """_Monitor child processes and handle their exit"""

#         try:
#             while self.child_pids:
#                 try:
#                     pid, status = os.waitpid(-1, os.WNOHANG)                    
#                     time.sleep(0.5)  # Small sleep to avoid busy waiting
                    
#                 except ChildProcessError:
#                     # No more children
#                     break
                    
#         except KeyboardInterrupt:
#             print(f"\n{time.strftime('%Y-%m-%d %H:%M:%S')} - Shutting down supervisor...")
#             self.stop(None)

    
#     def _write_worker_state(self, worker_name, pid=None, exit_code=None, message=None):
#         """Write worker state to a file"""
#         state_file = os.path.join(self.state_dir, f'{worker_name}.state')
#         state = {}
        
#         # Read existing state if it exists
#         if os.path.exists(state_file):
#             try:
#                 with open(state_file, 'r') as f:
#                     state = json.load(f)
#             except:
#                 pass
        
#         # Update state
#         if pid is not None:
#             state['pid'] = pid
#             state['status'] = 'running'
#         if exit_code is not None:
#             state['exit_code'] = exit_code
#             state['status'] = 'exited'
#             state['message'] = message
#             state.pop('pid', None)
        
#         # Write state
#         with open(state_file, 'w') as f:
#             json.dump(state, f)

#     def _read_worker_state(self, worker_name):
#         """Read worker state from file"""
#         state_file = os.path.join(self.state_dir, f'{worker_name}.state')
#         if os.path.exists(state_file):
#             try:
#                 with open(state_file, 'r') as f:
#                     state = json.load(f)
#                     # Verify if PID is still running
#                     if 'pid' in state:
#                         try:
#                             os.kill(state['pid'], 0)  # Check if process exists
#                         except OSError:
#                             # Process doesn't exist anymore
#                             state['status'] = 'exited'
#                             state.pop('pid', None)
#                     return state
#             except:
#                 pass
#         return None
