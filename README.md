# Process Supervisor - Detailed Explanation

## What is a Process Supervisor?

A **process supervisor** is a program that acts as a "babysitter" for other programs. It:
- Launches programs automatically
- Monitors if they're running
- Restarts them if they crash
- Manages their lifecycle (start/stop/restart)
- Handles their output (stdout/stderr)

Think of it like a parent watching over children - if a child (process) falls down (crashes), the parent (supervisor) helps them get back up (restarts them).

---

## The Shell Interface

### 1. **Status Command**
```bash
$ status
webapp          RUNNING   pid 1234, uptime 0:05:23
database        STOPPED   Not started
worker          FATAL     Exited too quickly (process log may have details)
api             RUNNING   pid 5678, uptime 1:23:45
```

Shows you:
- Which programs are running/stopped/crashed
- Their process IDs (PIDs)
- How long they've been running
- Any error states

### 2. **Start Command**
```bash
$ start database
database: started
```

Launches a stopped program according to its configuration.

### 3. **Stop Command**
```bash
$ stop webapp
webapp: stopped
```

Gracefully shuts down a running program (sends the configured stop signal).

### 4. **Restart Command**
```bash
$ restart api
api: stopped
api: started
```

Stops and then starts a program (useful after code updates).

### 5. **Reload Command**
```bash
$ reload
Reloading configuration...
Configuration loaded successfully
```

Re-reads the config file **without stopping the supervisor itself** or the running programs. This allows you to:
- Add new programs to supervise
- Change settings for existing programs
- Remove programs from supervision

**Without** having to restart everything and cause downtime.

### 6. **Quit/Exit Command**
```bash
$ quit
Shutting down supervisor...
Stopping all processes...
Goodbye!
```

Cleanly shuts down the supervisor and all supervised programs.

---

## Configuration File Options - Deep Dive

### Basic Execution Settings

#### **command** - The Program to Run
```yaml
cmd=/usr/bin/python3 /opt/myapp/app.py --port 8000
```

The exact command line that will be executed. This is like typing the command in your terminal.

**Example:**
```yaml
cmd=/usr/bin/node server.js
cmd=/usr/bin/php /var/www/worker.php
cmd=/usr/local/bin/my-custom-script
```

---

#### **numprocs** - Number of Instances
```yaml
numprocs=4
```

How many **copies** of this program should run simultaneously.

**Why use this?**
- **Load balancing**: Run 4 web server processes to handle more requests
- **Parallel processing**: Run 8 worker processes to process jobs faster
- **Redundancy**: If one crashes, others keep working

**Example scenario:**
```yaml
[program:api_server]
command=/usr/bin/node api.js
numprocs=3
```
This creates 3 separate processes all running the same API server, perhaps listening on different ports or using a load balancer.

---

#### **autostart** - Start on Launch
```yaml
autostart=true   # Start when supervisor starts
autostart=false  # Don't start automatically
```

**When to use `true`:**
- Critical services (web servers, databases)
- Always-needed background workers

**When to use `false`:**
- Maintenance scripts you run manually
- Programs you only need occasionally
- Programs that depend on other systems being ready first

---

#### **workingdir** - Working Directory
```yaml
workingdir=/opt/myapp
```

The directory the program will run in (like using `cd /opt/myapp` before running the command).

**Why this matters:**
- Programs often look for config files in their current directory
- Relative file paths will be relative to this directory
- Log files might be written to the current directory

**Example:**
```yaml
command=./start.sh
workingdir=/home/user/project
```
This runs `/home/user/project/start.sh`

---

#### **env** - Environment Variables
```yaml
env=PATH=/usr/bin:/usr/local/bin,DATABASE_URL=postgres://localhost/mydb,DEBUG=1
```

Sets environment variables before starting the program.

**Common uses:**
```yaml
# Set configuration
env=NODE_ENV=production

# Database connections
env=DB_HOST=localhost,DB_PORT=5432,DB_NAME=myapp

# API keys (though better to use secrets management)
env=API_KEY=abc123xyz

# Path modifications
env=PATH=/usr/local/bin:/usr/bin,LD_LIBRARY_PATH=/opt/lib
```

**Why this is useful:**
Programs read environment variables to know:
- Which database to connect to
- Whether to run in debug or production mode
- Where to find libraries or other executables

---

#### **umask** - File Permission Mask
```yaml
umask=022
```

Controls default permissions for files the program creates.

**Understanding umask:**
- `022` means created files are readable by everyone, writable only by owner
- `077` means created files are only accessible by owner (more secure)
- `002` means created files are readable/writable by owner and group

**Binary explanation:**
```
umask 022:
- Files created: 644 (rw-r--r--)
- Dirs created:  755 (rwxr-xr-x)

umask 077:
- Files created: 600 (rw-------)
- Dirs created:  700 (rwx------)
```

---

### Restart Behavior Settings

#### **autorestart** - When to Restart
```yaml
autorestart=always      # Always restart, even on clean exits
autorestart=never       # Never restart automatically
autorestart=unexpected  # Only restart on crashes/errors
```

**`always`** - Use for services that should always run:
```yaml
[program:web_server]
command=/usr/bin/nginx
autorestart=always  # Web server should never stay down
```

**`never`** - Use for one-time tasks:
```yaml
[program:database_migration]
command=/usr/bin/python3 migrate.py
autorestart=never  # Only run once
```

**`unexpected`** - Use for most applications:
```yaml
[program:worker]
command=/usr/bin/python3 worker.py
autorestart=unexpected  # Restart on crashes, but not if admin stops it
exitcodes=0             # Exit code 0 is "expected" (clean shutdown)
```

---

#### **exitcodes** - Expected Exit Codes
```yaml
exitcodes=0,2
```

Defines which exit codes mean "the program exited normally."

**Understanding exit codes:**
- `0` = Success (standard convention)
- `1` = Generic error
- `2` = Misuse of shell command
- `130` = Terminated by Ctrl+C

**Example scenario:**
```yaml
[program:batch_job]
command=/usr/bin/python3 process.py
autorestart=unexpected
exitcodes=0,2,3
```

This means:
- Exit code 0, 2, or 3 = "Job completed successfully, don't restart"
- Exit code 1, 4, 5... = "Something went wrong, restart the job"

**Why this matters:**
Some programs use specific exit codes to signal different completion states. For example:
- 0 = All work done
- 2 = No work available right now (not an error)
- 1 = Actual error occurred

---

#### **startsecs** - Successful Start Duration
```yaml
startsecs=5
```

The program must run for **at least** this many seconds to be considered "successfully started."

**Why this prevents restart loops:**

**Without startsecs:**
```
00:00 - Start program
00:00 - Program crashes immediately (bug in code)
00:00 - Supervisor thinks: "It started! But now it's dead, restart it!"
00:00 - Start program
00:00 - Program crashes immediately
00:00 - Start program
... infinite crash loop ...
```

**With startsecs=5:**
```
00:00 - Start program
00:00 - Program crashes immediately
00:00 - Supervisor thinks: "It didn't run for 5 seconds, that's a failed start"
00:00 - Try restart #2
00:00 - Program crashes immediately
00:00 - Try restart #3
00:00 - Program crashes immediately
00:00 - Max retries reached, mark as FATAL, stop trying
```

**Practical example:**
```yaml
[program:api]
command=/usr/bin/node api.js
startsecs=10
```

The API server needs to:
1. Load configuration (2 seconds)
2. Connect to database (3 seconds)
3. Start HTTP server (1 second)
4. Run for 4 more seconds = Total 10 seconds

Only then is it considered "successfully started" and safe.

---

#### **startretries** - Maximum Restart Attempts
```yaml
startretries=3
```

How many times to attempt restarting before giving up and marking the program as FATAL.

**Example scenario:**
```yaml
[program:flaky_service]
command=/usr/bin/python3 service.py
autorestart=unexpected
startsecs=5
startretries=3
```

Timeline:
```
Attempt 1: Start -> crash after 2 seconds (< 5 sec) -> FAIL
Attempt 2: Start -> crash after 1 second (< 5 sec) -> FAIL
Attempt 3: Start -> crash after 3 seconds (< 5 sec) -> FAIL
Result: Mark as FATAL, stop trying, alert admin
```

**Good practice:**
- Set to `3` for most applications
- Set to `0` for critical services (never give up)
- Set to `1` for experimental/unstable programs

---

### Stop/Kill Behavior

#### **stopsignal** - Graceful Stop Signal
```yaml
stopsignal=SIGTERM  # Most common
stopsignal=SIGINT   # Like pressing Ctrl+C
stopsignal=SIGQUIT  # Request quit
```

**What are signals?**
Signals are messages the operating system sends to programs to tell them to do something.

**Common signals:**

| Signal | Number | Meaning | Can be caught? |
|--------|--------|---------|----------------|
| SIGTERM | 15 | "Please terminate gracefully" | Yes |
| SIGINT | 2 | "Interrupt (Ctrl+C)" | Yes |
| SIGKILL | 9 | "Die immediately" | No (forceful) |
| SIGHUP | 1 | "Hang up (reload config)" | Yes |
| SIGQUIT | 3 | "Quit and dump core" | Yes |



**Example:**
```yaml
[program:web_api]
command=/usr/bin/node api.js
stopsignal=SIGTERM  # Give it a chance to close connections
stopwaitsecs=30     # Wait 30 seconds for graceful shutdown
```

---

#### **stopwaitsecs** - Graceful Stop Timeout
```yaml
stopwaitsecs=10
```

How long to wait for the program to exit after sending the stop signal before sending SIGKILL (force kill).



**Choosing the right value:**
- **5 seconds**: Fast services (simple scripts)
- **10 seconds**: Standard web servers
- **30 seconds**: Database servers (need time to flush)
- **60+ seconds**: Long-running transactions, batch jobs

---

### Output Management

#### **stdout** - Standard Output
```yaml
stdout=/var/log/myapp/output.log  # Write to file
stdout=/dev/null                   # Discard (throw away)
stdout=AUTO                        # Let supervisor decide
```

**What is stdout?**
Everything a program prints normally (using `print()`, `console.log()`, etc.)

**Options:**

**1. Redirect to file:**
```yaml
stdout=/var/log/webapp/access.log
```
All output goes to this file. Useful for debugging and auditing.

**2. Discard:**
```yaml
stdout=/dev/null
```
Output is thrown away. Use for very chatty programs where you don't need the output.

**3. AUTO:**
```yaml
stdout=AUTO
```
Supervisor handles it (usually buffers it and provides it through its own logging interface).

**Example:**
```yaml
[program:api]
command=/usr/bin/node api.js
stdout=/var/log/api/access.log
stdout_maxbytes=50MB      # Rotate after 50MB
stdout_backups=10          # Keep 10 old log files
```

---

#### **stderr** - Error Output
```yaml
stderr=/var/log/myapp/errors.log  # Write errors to file
stderr=/dev/null                   # Discard errors
stderr=AUTO                        # Let supervisor decide
```

**What is stderr?**
Everything a program prints as errors or warnings.

**Why separate from stdout?**
```python
print("Processing record 100")          # Goes to stdout
print("ERROR: Database timeout", file=sys.stderr)  # Goes to stderr
```

You can:
- Send normal logs to one file
- Send errors to another file
- Make it easier to find problems

**Example configuration:**
```yaml
[program:worker]
command=/usr/bin/python3 worker.py
stdout=/var/log/worker/info.log   # Normal operations
stderr=/var/log/worker/errors.log # Errors and warnings
```

Now you can quickly check `errors.log` to see if anything went wrong without wading through normal operational logs.

---

## Complete Real-World Example
```yaml
[program:ecommerce_api]
# What to run
command=/usr/bin/node /opt/ecommerce/api.js --port 3000

# How many instances
numprocs=4  # Run 4 API servers for load balancing

# Start behavior
autostart=true  # Start when supervisor starts
workingdir=/opt/ecommerce
umask=022  # Standard file permissions

# Environment
env=NODE_ENV=production,DATABASE_URL=postgres://localhost/ecommerce,PORT=3000

# Restart behavior
autorestart=unexpected  # Only restart on crashes
exitcodes=0  # Only exit code 0 is "normal"
startsecs=15  # Must run 15 seconds to be "successfully started"
startretries=3  # Try 3 times before giving up

# Stop behavior
stopsignal=SIGTERM  # Graceful shutdown
stopwaitsecs=30  # Wait 30 seconds before force kill (long enough for requests to finish)

# Logging
stdout=/var/log/ecommerce/api.log
stderr=/var/log/ecommerce/api_errors.log
```

**What this configuration does:**

1. **Launches 4 API servers** automatically when the supervisor starts
2. **Each server runs** from `/opt/ecommerce` directory
3. **Environment is set** for production with database connection
4. **If a server crashes**, it automatically restarts (up to 3 attempts)
5. **A server must run for 15 seconds** before being considered stable
6. **When stopping**, servers get 30 seconds to finish requests gracefully
7. **Logs are separated** - normal operations in one file, errors in another

This ensures high availability, automatic recovery, and clean monitoring for a production e-commerce API.

---

## Why Use a Process Supervisor?

### Without a supervisor:
```bash
# Start manually
$ node api.js &
[1] 1234

# API crashes at 3 AM
# ... nobody notices until morning ...
# ... customers can't access site ...
```

### With a supervisor:
```bash
# Start supervisor once
$ ./supervisor start

# Supervisor manages everything
03:00 - API crashes
03:00 - Supervisor detects crash
03:00 - Supervisor restarts API automatically
03:00 - API back online (5 second downtime)
```

\