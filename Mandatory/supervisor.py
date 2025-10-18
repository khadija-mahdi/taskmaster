import os
import subprocess
import sys
import time


class Supervisor:
    def __init__(self, programs: dict, cmd):
        self.programs = programs
        self.cmd = cmd[0]
        self.arg = cmd[1] if len(cmd) > 1 else None
        self.child_pids = {}
        self.child_pid_status = {}
        self.supervise(self.cmd, self.arg)


    def supervise(self, cmd: str, arg: str):
        # print the programs dict
        print(f"Supervising command: {cmd} with argument: {arg}")

        
        if cmd == "start":
            self.start(arg)
        elif cmd == "restart":
            self.restart()
        # elif cmd == "stop":
        #     self.stop()
        elif cmd == "status":
            ...
        elif cmd == "reload":
            ...
        elif cmd == "exit":
            ...
        elif cmd == "help":
            ...
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
                # This is the child process
                self.worker(key)
            else:
                # This is the parent process
                self.child_pids[key] = pid
                self.child_pid_status[pid] = 'running'
                print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - INFO {key} started with pid {os.getpid()}")
                # try:
                #     pid_ret, status = os.waitpid(pid, 0)  # Wait for the child to terminate
                #     print(f"Parent process: waitpid returned PID {pid_ret} with status {status}")
                    
                #     if pid_ret == pid:
                #         self.child_pid_status[pid] = 'stopped'
                #         if os.WIFEXITED(status):
                #             exit_code = os.WEXITSTATUS(status)
                #             print(f"Child exited normally with status {exit_code}")
                #         elif os.WIFSIGNALED(status):
                #             sig = os.WTERMSIG(status)
                #             print(f"Child terminated by signal {sig}")
                #         else:
                #             print(f"Child exited with status {status}")
                        
                #     print("Parent process: Child finished.")
                # except OSError as e:
                #     print(f"waitpid failed: {e}")
                #     sys.exit(1)
        # if self.child_pids:
        #     self.monitor()

    def worker(self, worker_name):
        """Execute the program in child process with output redirection"""
        try:
            pid = os.getpid()
            
            # Create new session and become process group leader
            os.setsid()
            
            # Second fork for true daemonization
            try:
                pid2 = os.fork()
                if pid2 > 0:
                    sys.exit(0)  # Exit first child
            except OSError as e:
                print(f"Second fork failed: {e}", file=sys.stderr)
                sys.exit(1)
            
            # This is the actual worker (grandchild)
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
                
            return_code = process.wait()
            sys.exit(return_code)
            
            
            
            
            # self._setup_logging(worker_name)
            
            
            
            # # Use Popen instead of run for continuous processes
            # process = subprocess.Popen(
            #     cmd.split(), 
            #     stdout=None, 
            #     stderr=None, 
            #     text=True,
            #     bufsize=1  # Line buffered
            # )
            
            # # Monitor the process
            # return_code = process.wait()
            
            # sys.exit(return_code)
            
        except Exception as e:
            print(f"Worker {worker_name} failed: {e}", file=sys.stderr)
            sys.exit(1)





    def monitor(self):
        """Monitor child processes and handle their exit"""

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
                            # Remove from tracking
                            del self.child_pids[prog_name]
                            
                            # Log exit status
                            if os.WIFEXITED(status):
                                exit_code = os.WEXITSTATUS(status)
                                # print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - {prog_name} (PID: {pid}) exited with code {exit_code}")
                            elif os.WIFSIGNALED(status):
                                sig = os.WTERMSIG(status)
                                print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - {prog_name} (PID: {pid}) terminated by signal {sig}")
                            
                            # Auto-restart if configured
                            # if self.programs[prog_name].get('autorestart', False):
                            #     print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - Restarting {prog_name}...")
                                # self.start(prog_name)
                    
                    time.sleep(0.5)  # Small sleep to avoid busy waiting
                    
                except ChildProcessError:
                    # No more children
                    break
                    
        except KeyboardInterrupt:
            print(f"\n{time.strftime('%Y-%m-%d %H:%M:%S')} - Shutting down supervisor...")
            self.stop(None)
    
    def _setup_logging(self, worker_name):
        """Redirect stdout and stderr to log files"""
        try:
            stdout_path = self.programs[worker_name].get('stdout', f"./logs/{worker_name}_stdout.log")
            stderr_path = self.programs[worker_name].get('stderr', f"./logs/{worker_name}_stderr.log")
            
            os.makedirs(os.path.dirname(stdout_path) if os.path.dirname(stdout_path) else './logs', exist_ok=True)
            
            # Close existing file descriptors first
            sys.stdout.flush()
            sys.stderr.flush()
            
            # Open files in append mode with buffering
            stdout_file = open(stdout_path, 'a', buffering=1)  # line buffering
            stderr_file = open(stderr_path, 'a', buffering=1)
            
            # Redirect
            os.dup2(stdout_file.fileno(), sys.stdout.fileno())
            os.dup2(stderr_file.fileno(), sys.stderr.fileno())
            
            # Store references to prevent garbage collection
            self._log_files = getattr(self, '_log_files', {})
            self._log_files[worker_name] = (stdout_file, stderr_file)
            
        except Exception as e:
            print(f"Logging setup failed for {worker_name}: {e}", file=sys.stderr)
            sys.exit(1)





# def start(program):
#     ...



# def restart(program):
#     ...


# def stop(program):
#     ...


# def supervise(programs: dict, action: str):
#     # for program in
#     ...




                # try:
                #     pid_ret, status = os.waitpid(pid, 0)  # Wait for the child to terminate
                #     print(f"Parent process: waitpid returned PID {pid_ret} with status {status}")
                    
                #     if pid_ret == pid:
                #         if os.WIFEXITED(status):
                #             exit_code = os.WEXITSTATUS(status)
                #             print(f"Child exited normally with status {exit_code}")
                #         elif os.WIFSIGNALED(status):
                #             sig = os.WTERMSIG(status)
                #             print(f"Child terminated by signal {sig}")
                #         else:
                #             print(f"Child exited with status {status}")
                #     print("Parent process: Child finished.")
                # except OSError as e:
                #     print(f"waitpid failed: {e}")
                #     sys.exit(1)