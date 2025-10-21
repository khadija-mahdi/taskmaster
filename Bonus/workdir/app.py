# app.py
from flask import Flask
import time
import os

app = Flask(__name__)

@app.route('/')
def hello():
    return f"""
    <h1>Hello from Supervisord!</h1>
    <p>Server time: {time.ctime()}</p>
    <p>Process ID: {os.getpid()}</p>
    <p>Running on: {os.uname().nodename}</p>
    """

@app.route('/health')
def health():
    return {'status': 'healthy', 'timestamp': time.time()}

if __name__ == '__main__':
    print(f"Starting Flask app on process {os.getpid()}")
    app.run(
        host='0.0.0.0', 
        port=5000, 
        debug=False  # Set to False in production
    )


# app.py - Simple test application
# import time
# import sys
# import os

# print(f"Application starting with PID: {os.getpid()}")

# try:
#     counter = 0
#     while True:
#         counter += 1
#         print(f"Counter: {counter} - Time: {time.ctime()}")
#         sys.stdout.flush()  # Ensure output is sent immediately
        
#         # Write to stderr every 5 iterations
#         if counter % 5 == 0:
#             print(f"Error simulation iteration {counter}", file=sys.stderr)
#             sys.stderr.flush()
        
#         time.sleep(2)
        
# except KeyboardInterrupt:
#     print("Received interrupt signal - shutting down")
# except Exception as e:
#     print(f"Error: {e}", file=sys.stderr)
#     sys.exit(1)