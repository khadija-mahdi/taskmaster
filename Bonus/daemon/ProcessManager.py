import pty
import os
import select
import sys

class ProcessManager:
    def __init__(self):
        self.processes = {}  # pid -> fd

    def start_interactive_process(self, command):
        pid, fd = pty.fork()
        if pid == 0:
            os.execvp(command[0], command)
        else:
            self.processes[pid] = fd
            return pid, fd

    def attach_process(self, pid):
        """
        Attach to a running process's pty, forwarding I/O.
        Ctrl+C to detach.
        """
        fd = self.processes.get(pid)
        if fd is None:
            print("No such process")
            return
        try:
            while True:
                rlist, _, _ = select.select([fd, sys.stdin], [], [])
                if fd in rlist:
                    data = os.read(fd, 1024)
                    if data:
                        os.write(sys.stdout.fileno(), data)
                if sys.stdin in rlist:
                    user_input = os.read(sys.stdin.fileno(), 1024)
                    if user_input:
                        os.write(fd, user_input)
        except KeyboardInterrupt:
            print("\nDetached from process.")

    def detach_process(self, pid):
        """
        Detach from the process (handled by exiting attach loop).
        """
        pass

    def attach_process(self, pid):
        fd = self.processes.get(pid)
        if fd is None:
            print("No such process")
            return
        try:
            while True:
                rlist, _, _ = select.select([fd, sys.stdin], [], [])
                if fd in rlist:
                    data = os.read(fd, 1024)
                    if data:
                        os.write(sys.stdout.fileno(), data)
                if sys.stdin in rlist:
                    user_input = os.read(sys.stdin.fileno(), 1024)
                    if user_input:
                        os.write(fd, user_input)
        except KeyboardInterrupt:
            print("\nDetached from process.")

    def detach_process(self, pid):
        # Just exit the attach loop; process keeps running
        pass