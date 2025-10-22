

import os
import errno

def pid_exists(pid: int):
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        # ESRCH: no such process
        return "ESRCH: no such process"
    except PermissionError:
        # EPERM: process exists but we don't have permission to signal it
        return "EPERM: process exists but no permission to signal it"
    except OSError as e:
        # be explicit about other OS errors
        if e.errno == errno.ESRCH:
            return "ESRCH: no such process"
        # raise
    else:
        return "Process exists"
print(pid_exists(60734))
