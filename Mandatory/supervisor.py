import os
import subprocess
import sys
import time


class Supervisor:
    def __init__(self, programs: dict):
        self.programs = programs
        self.child_pids = {}
        # self.child_pid_status = {}
        self.worker_name_pid = {}
        self.worker_exit_status = {}


    def supervise(self, cmd):
        # print the programs dict
        # print(f"Supervising command: {cmd} with argument: {arg}")
        self.cmd = cmd[0]
        self.arg = cmd[1] if len(cmd) > 1 else None

        
        if self.cmd == "start":
            self.start(self.arg)
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
                # pid = os.getpid()
                print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - INFO {key} started with pid {os.getpid()}")
                self.worker(key)
            else:
                # This is the parent process
                self.child_pids[key] = pid
                # self.child_pid_status[pid] = 'running'
                # print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - INFO {key} started with pid {os.getpid()}")
        if self.child_pids:
            self.monitor()

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
            # pid = os.getpid()
            # print(f"Worker {worker_name} running with PID {pid}")
        
            print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - INFO {worker_name} started with pid {os.getpid()}")

            
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
            # pid, status = os.waitpid(-1, os.WNOHANG)
            pid = os.getpid()
            self.worker_exit_status[worker_name] = worker_name
            print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - INFO {worker_name} (PID: {pid}) exited with code {return_code}")
            sys.exit(1)
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
                    
                    # if pid > 0:
                    #     # Find which program this PID belongs to
                    #     prog_name = None
                    #     for name, p in list(self.child_pids.items()):
                    #         if p == pid:
                    #             prog_name = name
                    #             break
                        
                    #     if prog_name:
                    #         print(f"Program {prog_name} with PID {pid} has exited.")
                    #         # Remove from tracking
                    #         # del self.child_pids[prog_name]
                            
                    #         # Log exit status
                    #         if os.WIFEXITED(status):
                    #             exit_code = os.WEXITSTATUS(status)
                    #             # print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - {prog_name} (PID: {pid}) exited with code {exit_code}")
                    #         elif os.WIFSIGNALED(status):
                    #             sig = os.WTERMSIG(status)
                    #             print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - {prog_name} (PID: {pid}) terminated by signal {sig}")
                            
                    #         # Auto-restart if configured
                    #         # if self.programs[prog_name].get('autorestart', False):
                    #         #     print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - Restarting {prog_name}...")
                    #             # self.start(prog_name)
                    
                    time.sleep(0.5)  # Small sleep to avoid busy waiting
                    
                except ChildProcessError:
                    # No more children
                    break
                    
        except KeyboardInterrupt:
            print(f"\n{time.strftime('%Y-%m-%d %H:%M:%S')} - Shutting down supervisor...")
            self.stop(None)
    
