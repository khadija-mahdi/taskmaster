import os
import subprocess
import sys
import time


class Supervisor:
    def __init__(self, programs: dict, cmd):
        self.programs = programs
        self.cmd = cmd[0]
        self.arg = cmd[1] if len(cmd) > 1 else None
        
        self.supervise(self.cmd, self.arg)


    def supervise(self, cmd: str, arg: str):
        # print the programs dict
        print(f"Supervising command: {cmd} with argument: {arg}")
        # print(f"Programs: {self.programs}")
        # print(len(self.programs['api']))
        # for program in self.programs:
        #     print(f"**************** {program} ****************")
        #     for key, value in self.programs[program].items():
        #         print(f"{key}")
        #     print("******************************************")
            # print(f"")
        
        if cmd == "start":
            self.start()
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
        


    def start(self):
        for key, value in self.programs.items():
            if value.get('autostart', True) == True:
                try:
                    pid = os.fork()
                except OSError as e:
                    print(f"fork failed: {e}")
                    sys.exit(1)
                
                if pid == 0:
                    self.worker(key)
                else:
                    print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - INFO supervisord started with pid {pid}")
                    try:
                        pid_ret, status = os.waitpid(pid, 0)  # Wait for the child to terminate
                        print(f"Parent process: waitpid returned PID {pid_ret} with status {status}")
                        
                        if pid_ret == pid:
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

    def worker(self, worker_name):
        # args = ["ls", "-l"]  # Corrected: separate command and argument
        try:
            print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - Worker process (PID: {os.getpid()}) starting for: {worker_name}")
            subprocess.run(f"{self.programs[worker_name]['cmd']}", shell=True)
            # subprocess.run(["ls", "l"])
            # os.execvp()
        except OSError as e:
            print(f"execvp failed: {e}")
            sys.exit(1)  # Use sys.exit instead of return in forked process
                #send a signal to the parent process about the failure
                
                
                # print(f"execvp failed: {e}")
                # sys.exit(1)
            # print(f"Child process (PID: {os.getpid()}) running as: {worker_name}")
            # time.sleep(5) # Simulate some work
            # print(f"Child process (PID: {os.getpid()}) exiting.")
    def _log(self, worker_name):
        try:
            self.file_for_stdout = open(self.programs.get('stdout', f"./logs/{worker_name}"), "w")
            self.file_for_stderr = open(self.programs.get('stderr', f"./logs/{worker_name}"), "w")
            # Duplicate the file descriptor of the opened file to stdout (fd 1)
            # This effectively redirects all subsequent prints to this file
            os.dup2(self.file_for_stdout.fileno(), sys.stdout.fileno())
            os.dup2(slef.file_for_stderr.fileno(), sys.stderr.fileno())

            print("This will now go to redirected_stdout.txt")

            file_for_stdout.close()
        except Exception as e:
            print(f"Logging failed for {worker_name}: {e}")





# def start(program):
#     ...



# def restart(program):
#     ...


# def stop(program):
#     ...


# def supervise(programs: dict, action: str):
#     # for program in
#     ...


