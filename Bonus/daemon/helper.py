import os
import sys
import time
import signal
import shutil



def get_path(path):
    if path is None:
        return None
    _expanded = os.path.expandvars(path)
    return _expanded.replace("$PWD", os.getcwd())


def exec_child_process(program, program_name, is_attach):
    """Execute the child process. This runs in the child after fork."""
    try:

        cmd = get_path(program.get('cmd'))
        if not cmd:
            print(
                f"INFO Error: no command specified for program '{program_name}'", file=sys.stderr)
            sys.exit(1)

        parts = cmd.split()
        command_path = parts[0]

        if not os.path.isabs(command_path):
            if not shutil.which(command_path):
                print(
                    f"INFO Error: can't find command '{command_path}'", file=sys.stderr)
                sys.exit(1)
        else:
            if not os.path.exists(command_path):
                print(
                    f"INFO Error: can't find command '{command_path}'", file=sys.stderr)
                sys.exit(1)
            if not os.access(command_path, os.X_OK):
                print(
                    f"INFO Error: command '{command_path}' is not executable", file=sys.stderr)
                sys.exit(1)

        workingdir = get_path(program.get('workingdir')) or os.getcwd()
        umask = program.get('umask', 0o022)
        os.umask(umask)
        stdout_path = program.get('stdout')
        print(f"DEBUG: is_attach = {is_attach}", file=sys.stderr )
        if  not is_attach:
            if stdout_path:
                try:
                    sys.stdout.flush()
                    fd_out = os.open(stdout_path, os.O_WRONLY |
                                    os.O_CREAT | os.O_APPEND, 0o666)
                    os.dup2(fd_out, sys.stdout.fileno())
                    os.close(fd_out)
                except Exception as e:
                    print(
                        f"INFO Error: can't redirect stdout to '{stdout_path}': {e}", file=sys.stderr)
                    sys.exit(1)

            stderr_path = program.get('stderr')
            if stderr_path:
                try:
                    sys.stderr.flush()
                    fd_err = os.open(stderr_path, os.O_WRONLY |
                                    os.O_CREAT | os.O_APPEND, 0o666)
                    os.dup2(fd_err, sys.stderr.fileno())
                    os.close(fd_err)
                except Exception as e:
                    print(
                        f"INFO Error: can't redirect stderr to '{stderr_path}': {e}", file=sys.stderr)
                    sys.exit(1)
        env = os.environ.copy()
        for k, v in (program.get('env') or {}).items():
            env[k] = str(v)

        try:
            os.chdir(workingdir)
        except Exception as e:
            print(
                f"INFO Error: can't chdir to '{workingdir}': {e}", file=sys.stderr)
            sys.exit(1)

        start_delay = program.get('startdelay', 0)
        if start_delay > 0:
            time.sleep(start_delay)

        os.execvpe(parts[0], parts, env)

    except Exception as e:
        print(
            f"INFO Error: unexpected error in child process: {e}", file=sys.stderr)
        sys.exit(1)


def cleanup_failed_process(program_name, pid, running_processes, process_info):
    """Update process state to STOPPED when it fails."""
    try:
        try:
            os.waitpid(pid, os.WNOHANG)
        except:
            pass

        if program_name in running_processes:
            if pid in running_processes[program_name]:
                running_processes[program_name].remove(pid)

        # Find and update the process state, close master_fd if exists
        for key, info in process_info.items():
            if info.get('pid') == pid:
                info['state'] = 'STOPPED'
                # Close master_fd if it exists
                master_fd = info.get('master_fd')
                if master_fd:
                    try:
                        os.close(master_fd)
                    except:
                        pass
                    info['master_fd'] = None
                break

    except Exception as e:
        print(f"Warning: Error during cleanup of process {pid}: {e}")


def cleanup_program(program_name, running_processes, process_info):
    """Update process state to FATAL and clean up running processes."""
    try:
        if program_name in running_processes:
            for pid in list(running_processes[program_name]):
                try:
                    os.kill(pid, signal.SIGTERM)
                    time.sleep(0.5)
                    try:
                        os.kill(pid, signal.SIGKILL)
                    except:
                        pass
                    os.waitpid(pid, os.WNOHANG)
                except:
                    pass

            running_processes[program_name] = []

        # Update process state to FATAL and close master_fds
        for key in list(process_info.keys()):
            if key.startswith(f"{program_name}_") or key == program_name:
                process_info[key]["state"] = "FATAL"
                # Close master_fd if it exists
                master_fd = process_info[key].get('master_fd')
                if master_fd:
                    try:
                        os.close(master_fd)
                    except:
                        pass
                    process_info[key]['master_fd'] = None

    except Exception as e:
        print(
            f"Warning: Error during program cleanup for '{program_name}': {e}")


def stop_process(pid, stopsignal, stoptime):
    """Stop a specific process with given signal and timeout."""
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


def should_autorestart(autorestart_value):
    if isinstance(autorestart_value, str):
        val = autorestart_value.lower()
        if val == "always":
            return True
        elif val == "never":
            return False
        elif val == "unexpected":
            return True
    return bool(autorestart_value)


def run_process(program, indexed_name,is_attach=False):
    """Fork and exec a program, returning the child PID."""
    pid = os.fork()
    if pid == 0:
        try:
            print(f"DEBUG: is_attach = {is_attach}", file=sys.stderr )
            exec_child_process(program, indexed_name, is_attach)
        except Exception as e:
            print(f"ERR exec failed in child '{indexed_name}': {e}")
            sys.exit(1)
    return pid


def isalive_process(pid):
    """Return (alive: bool, exit_code: int or None)."""
    try:
        pid_result, exit_status = os.waitpid(pid, os.WNOHANG)
        if pid_result != 0:
            if os.WIFEXITED(exit_status):
                return False, os.WEXITSTATUS(exit_status)
            elif os.WIFSIGNALED(exit_status):
                return False, -os.WTERMSIG(exit_status)
            return False, -1
        os.kill(pid, 0)
        return True, None
    except ProcessLookupError:
        return False, None
    except ChildProcessError:
        return False, None


def register_process(running_processes, process_info, program_name, indexed_name, pid, retry_count, state="RUNNING", master_fd=None):
    """Record process details with optional PTY master file descriptor."""
    if program_name not in running_processes:
        running_processes[program_name] = []
    if pid not in running_processes[program_name]:
        running_processes[program_name].append(pid)

    process_info[indexed_name] = {
        "retries": retry_count,
        "start_time": time.time(),
        "pid": pid,
        "state": state,
        "program_name": program_name,
        "master_fd": master_fd  # Store the PTY master file descriptor for attach functionality
    }


def log_event(event_type, message):
    """Log events to a file with timestamp."""
    import datetime
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] {event_type}: {message}\n"

    log_dir = "/home/kmahdi/Desktop/taskmaster/Bonus/logger"
    os.makedirs(log_dir, exist_ok=True)

    log_file = os.path.join(log_dir, "taskmaster.log")
    try:
        with open(log_file, 'a') as f:
            f.write(log_entry)
    except Exception as e:
        print(f"Warning: Could not write to log file: {e}")
