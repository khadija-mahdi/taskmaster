import os
import signal
import subprocess
import sys
import time


# class Supervisor:
#     def __init__(self, programs: dict, cmd):
#         self.programs = programs
#         self.cmd = cmd[0]
#         self.arg = cmd[1] if len(cmd) > 1 else None
#         self.pid = None
#         self.supervise(self.cmd, self.arg)
#         self.child_pids = {}


#     def supervise(self, cmd: str, arg: str):
#         if cmd == "start":
#             self.start(arg)
#         elif cmd == "restart":
#             self.restart()
#         # elif cmd == "stop":
#         #     self.stop()
#         elif cmd == "status":
#             ...
#         elif cmd == "reload":
#             ...
#         elif cmd == "exit":
#             ...
#         elif cmd == "stop":
#             self.stop(arg)
#         elif cmd == "help":
#             ...
#         else:
#             print("Invalid command")
        
    
#     def start(self, arg=None):
#         for key, value in self.programs.items():
#             if value.get('autostart', True) == True and (arg is None or arg == key):
#                 try:
#                     pid = os.fork()
#                 except OSError as e:
#                     print(f"fork failed: {e}")
#                     sys.exit(1)
                
#                 if pid == 0:
#                     # Child process
#                     self.worker(key)
#                 else:
#                     # Parent process
#                     self.child_pids[key] = pid
#                     print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - INFO supervisord started {key} with pid {pid}")
                    
#                     # Don't wait here in the parent - this would block starting other processes
#                     # Instead, you might want to implement a reaper elsewhere
    
#     def worker(self, worker_name):
#         try:
#             pid = os.getpid()
#             print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - Worker process (PID: {pid}) starting for: {worker_name}")
#             self.programs[worker_name]['pid'] = pid
            
#             # Execute the command
#             subprocess.run(f"{self.programs[worker_name]['cmd']}", shell=True)
            
#         except OSError as e:
#             print(f"execvp failed: {e}")
#             sys.exit(1)
    
#     def stop(self, worker_name=None):
#         if worker_name is None:
#             # Stop all workers
#             for name, pid in self.child_pids.items():
#                 self._stop_worker(name, pid)
#             self.child_pids.clear()
#         else:
#             # Stop specific worker
#             pid = self.child_pids.get(worker_name)
#             if pid:
#                 self._stop_worker(worker_name, pid)
#                 del self.child_pids[worker_name]
#             else:
#                 print(f"{worker_name}: ERROR (not running)")
    
#     def _stop_worker(self, worker_name, pid):
#         """Stop a worker process gracefully"""
#         try:
#             # First try graceful termination (SIGTERM)
#             os.kill(pid, signal.SIGTERM)
#             print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - Sent SIGTERM to {worker_name} (PID: {pid})")
            
#             # Wait a bit for graceful shutdown
#             time.sleep(2)
            
#             # Check if process is still alive
#             try:
#                 os.kill(pid, 0)  # This will raise OSError if process doesn't exist
#                 # Process still exists, force kill
#                 os.kill(pid, signal.SIGKILL)
#                 print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - Sent SIGKILL to {worker_name} (PID: {pid})")
#             except OSError:
#                 # Process already terminated
#                 print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - {worker_name} (PID: {pid}) terminated gracefully")
                
#         except OSError as e:
#             if e.errno == 3:  # ESRCH - No such process
#                 print(f"{worker_name}: ERROR (no such process)")
#             else:
#                 print(f"Error stopping {worker_name}: {e}")
    
#     def stop_graceful(self, worker_name=None, timeout=10):
#         """More graceful shutdown with configurable timeout"""
#         if worker_name is None:
#             workers = list(self.child_pids.items())
#         else:
#             workers = [(worker_name, self.child_pids.get(worker_name))]
        
#         for name, pid in workers:
#             if not pid:
#                 continue
                
#             try:
#                 # Send SIGTERM
#                 os.kill(pid, signal.SIGTERM)
#                 print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - Sent SIGTERM to {name} (PID: {pid})")
                
#                 # Wait for process to terminate
#                 start_time = time.time()
#                 while time.time() - start_time < timeout:
#                     try:
#                         os.kill(pid, 0)  # Check if process exists
#                         time.sleep(0.1)  # Short delay before checking again
#                     except OSError:
#                         # Process terminated
#                         print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - {name} (PID: {pid}) terminated gracefully")
#                         if name in self.child_pids:
#                             del self.child_pids[name]
#                         break
#                 else:
#                     # Timeout reached, force kill
#                     try:
#                         os.kill(pid, signal.SIGKILL)
#                         print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - Force killed {name} (PID: {pid}) after timeout")
#                         if name in self.child_pids:
#                             del self.child_pids[name]
#                     except OSError as e:
#                         print(f"Error force killing {name}: {e}")
                        
#             except OSError as e:
#                 print(f"Error stopping {name}: {e}")

# # def start(program):
# #     ...



# # def restart(program):
# #     ...

# # def supervise(programs: dict, action: str):
# #     # for program in
# #     ...


import os
import subprocess
import sys
import time


class Supervisor:
    def __init__(self, programs: dict, cmd):
        self.programs = programs
        self.cmd = cmd[0]
        self.arg = cmd[1] if len(cmd) > 1 else None
        self.pid = None
        self.supervise(self.cmd, self.arg)
        self.child_pids = {}


    def supervise(self, cmd: str, arg: str):
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
        elif cmd == "stop":
            self.stop(arg)
        elif cmd == "help":
            ...
        else:
            print("Invalid command")
        


    def start(self, arg=None):
        for key, value in self.programs.items():
            if value.get('autostart', True) == True and (arg is None or arg == key):
                try:
                    self.pid = os.fork()
                except OSError as e:
                    print(f"fork failed: {e}")
                    sys.exit(1)
                
                if self.pid == 0:
                    self.worker(key)
                else:
                    self.child_pids[key] = self.pid
                    print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - INFO supervisord started with pid {self.pid}")
        
        for child_key, child_pid in self.child_pids.items():
            try:
                pid_ret, status = os.waitpid(child_pid, 0)  # Wait for the child to terminate
                print(f"Parent process: waitpid returned PID {pid_ret} with status {status}")
                
                if pid_ret == self.pid:
                    if os.WIFEXITED(status):
                        exit_code = os.WEXITSTATUS(status)
                        print(f"Child exited normally with status {exit_code}")
                    elif os.WIFSIGNALED(status):
                        sig = os.WTERMSIG(status)
                        print(f"Child terminated by signal {sig}")
                    else:
                        print(f"Child exited with status {status}")
                print("Parent process: Child finished.")
            except OSError as e:
                print(f"waitpid failed: {e}")
                sys.exit(1)
            # os.waitpid(child_pid, 0)

    def worker(self, worker_name):
        try:
            pid = os.getpid()
            print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - Worker process (PID: {pid}) starting for: {worker_name}")
            self.programs[worker_name]['pid'] = pid
            subprocess.run(f"{self.programs[worker_name]['cmd']}", shell=True)
            print("Child process: Command execution completed.")
            sys.exit(0)  # Exit child process successfully after command execution
        except OSError as e:
            print(f"execvp failed: {e}")
            sys.exit(1)  # Use sys.exit instead of return in forked process
    







    def stop(self, worker_name=None):
        if not worker_name:
            subprocess.run(f"kill {self.pid}", shell=True)
        else:
            pid = self.programs[worker_name].get('pid')
            if pid:
                subprocess.run(f"kill {pid}", shell=True)
                print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - INFO Stopped {worker_name}")
            else:
                print(f"{worker_name}: ERROR (not running)")

    def _log(self, worker_name):
        try:
            self.file_for_stdout = open(self.programs.get('stdout', f"./logs/{worker_name}"), "w")
            self.file_for_stderr = open(self.programs.get('stderr', f"./logs/{worker_name}"), "w")
            # Duplicate the file descriptor of the opened file to stdout (fd 1)
            # This effectively redirects all subsequent prints to this file
            os.dup2(self.file_for_stdout.fileno(), sys.stdout.fileno())
            os.dup2(self.file_for_stderr.fileno(), sys.stderr.fileno())

            print("This will now go to redirected_stdout.txt")

        except Exception as e:
            print(f"Logging failed for {worker_name}: {e}")

# def start(program):
#     ...



# def restart(program):
#     ...

# def supervise(programs: dict, action: str):
#     # for program in
#     ...


