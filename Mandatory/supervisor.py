import os
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
                raise


    def supervise(self, cmd):
        self.cmd = cmd[0]
        self.arg = cmd[1] if len(cmd) > 1 else None

        
        if self.cmd == "start":
            self.start(self.arg)
        elif self.cmd == "status":
            self.status(self.arg)
        else:
            print("Invalid command")
    
    def start(self, arg):
        for key, value in self.programs.items():
            if not (arg == key or  (value.get('autostart', True) and arg is None)):
                continue
            try:
                pid = os.fork()
            except OSError as e:
                print(f"fork failed: {e}")
                sys.exit(1)
            
            if pid == 0:
                self._worker(key)
            else:
                self.child_pids[key] = pid
        if self.child_pids:
            self._monitor()

    def status(self, arg):
        for key in self.programs.keys():
            if arg is not None and arg != key:
                continue
            
            state = self._read_worker_state(key)
            
            if state is None:
                print(f"{key} is not running")
            elif state.get('status') == 'running' and 'pid' in state:
                print(f"{key} is running with PID {state['pid']}")
            elif 'exit_code' in state:
                print(f"{key} exited with code {state['exit_code']}")
            else:
                print(f"{key} is not running")



    def _write_worker_state(self, worker_name, pid=None, exit_code=None):
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
                            state['status'] = 'exited'
                            state.pop('pid', None)
                    return state
            except:
                pass
        return None



    
    
    def _worker(self, worker_name):
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
            worker_pid = os.getpid()
            self._write_worker_state(worker_name, pid=worker_pid)
            print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - INFO {worker_name} started with pid {worker_pid}")

            
            os.chdir(self.programs[worker_name].get('workingdir', './workir'))
            
            # Reset file creation mask
            os.umask(0)
            cmd = self.programs[worker_name]['cmd']
            
            
            stdout_path = self.programs[worker_name].get('stdout', f"./logs/{worker_name}_stdout.log")
            stderr_path = self.programs[worker_name].get('stderr', f"./logs/{worker_name}_stderr.log")
            
            os.makedirs(os.path.dirname(stdout_path) if os.path.dirname(stdout_path) else './logs', exist_ok=True)
            
            # Open files and pass to subprocess
            with open(stdout_path, 'a') as stdout_file, open(stderr_path, 'a') as stderr_file:
                process = subprocess.Popen(
                    cmd.split(),
                    stdout=stdout_file,   # Direct to file
                    stderr=stderr_file,   # Direct to file
                    text=True
                )
                
            exit_code = process.wait()
            # Write exit status to state file
            self._write_worker_state(worker_name, exit_code=exit_code)
            sys.exit(exit_code)

        except Exception as e:
            print(f"Worker {worker_name} failed: {e}", file=sys.stderr)
            self._write_worker_state(worker_name, exit_code=1)
            sys.exit(1)





    def _monitor(self):
        """_Monitor child processes and handle their exit"""

        try:
            while self.child_pids:
                # Non-blocking wait for any child process
                try:
                    pid, status = os.waitpid(-1, os.WNOHANG)
                    
                    if pid > 0:
                        # Find which program this PID belongs to
                        prog_name = None
                        for name, p in list(self.child_pids.items()):
                            if p == pid:
                                prog_name = name
                                break
                        
                        if prog_name:
                            del self.child_pids[prog_name]
                    
                    time.sleep(0.5)  # Small sleep to avoid busy waiting
                    
                except ChildProcessError:
                    # No more children
                    break
                    
        except KeyboardInterrupt:
            print(f"\n{time.strftime('%Y-%m-%d %H:%M:%S')} - Shutting down supervisor...")
            self.stop(None)


# import os
# import subprocess
# import sys
# import time


# class Supervisor:
#     def __init__(self, programs: dict):
#         self.programs = programs
#         self.child_pids = {}
#         self.worker_pids = {}
#         self.worker_exit_status = {}


#     def supervise(self, cmd):
#         self.cmd = cmd[0]
#         self.arg = cmd[1] if len(cmd) > 1 else None

        
#         if self.cmd == "start":
#             self.start(self.arg)
#         elif self.cmd == "status":
#             self.status(self.arg)
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
#                 self._worker(key)
#             else:
#                 self.child_pids[key] = pid
#         if self.child_pids:
#             self._monitor()

#     def status(self, arg):
#         print(self.worker_pids)
#         for key in self.programs.keys():
#             if arg is not None and arg != key:
#                 continue
#             if key in self.worker_exit_status:
#                 exit_code = self.worker_exit_status[key]
#                 print(f"{key} exited with code {exit_code}")
#             elif key in self.worker_pids:
#                 pid = self.worker_pids.get(key)
#                 print(f"{key} is running with PID {pid}")
#             else:
#                 print(f"{key} is not running")
    
    
#     def _worker(self, worker_name):
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

#             self.worker_pids[worker_name] = os.getpid()
#             print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - INFO {worker_name} started with pid {os.getpid()}")

            
#             os.chdir(self.programs[worker_name].get('workingdir', './workir'))
            
#             # Reset file creation mask
#             os.umask(0)
#             cmd = self.programs[worker_name]['cmd']
            
            
#             stdout_path = self.programs[worker_name].get('stdout', f"./logs/{worker_name}_stdout.log")
#             stderr_path = self.programs[worker_name].get('stderr', f"./logs/{worker_name}_stderr.log")
            
#             os.makedirs(os.path.dirname(stdout_path) if os.path.dirname(stdout_path) else './logs', exist_ok=True)
            
#             # Open files and pass to subprocess
#             with open(stdout_path, 'a') as stdout_file, open(stderr_path, 'a') as stderr_file:
#                 process = subprocess.Popen(
#                     cmd.split(),
#                     stdout=stdout_file,   # Direct to file
#                     stderr=stderr_file,   # Direct to file
#                     text=True
#                 )
                
#             self.worker_exit_status[worker_name] = process.wait()
#             sys.exit(self.worker_exit_status[worker_name])

#         except Exception as e:
#             print(f"Worker {worker_name} failed: {e}", file=sys.stderr)
#             sys.exit(1)





#     def _monitor(self):
#         """_Monitor child processes and handle their exit"""

#         try:
#             while self.child_pids:
#                 # Non-blocking wait for any child process
#                 try:
#                     pid, status = os.waitpid(-1, os.WNOHANG)
                    
#                     if pid > 0:
#                         # Find which program this PID belongs to
#                         prog_name = None
#                         for name, p in list(self.child_pids.items()):
#                             if p == pid:
#                                 prog_name = name
#                                 break
                        
#                         if prog_name:
#                             del self.child_pids[prog_name]
                    
#                     time.sleep(0.5)  # Small sleep to avoid busy waiting
                    
#                 except ChildProcessError:
#                     # No more children
#                     break
                    
#         except KeyboardInterrupt:
#             print(f"\n{time.strftime('%Y-%m-%d %H:%M:%S')} - Shutting down supervisor...")
#             self.stop(None)
    

                            
                            # # Log exit status
                            # if os.WIFEXITED(status):
                            #     exit_code = os.WEXITSTATUS(status)
                            #     # print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - {prog_name} (PID: {pid}) exited with code {exit_code}")
                            # elif os.WIFSIGNALED(status):
                            #     sig = os.WTERMSIG(status)
                            #     print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - {prog_name} (PID: {pid}) terminated by signal {sig}")
                            
                            # Auto-restart if configured
                            # if self.programs[prog_name].get('autorestart', False):
                            #     print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - Restarting {prog_name}...")
                                # self.start(prog_name)