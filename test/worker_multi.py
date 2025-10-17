# worker_multi.py
import time
import os
import signal
import sys
import random

def handle_signal(signum, frame):
    print(f"📢 Worker Multi received signal {signum}, cleaning up...")
    sys.exit(0)

# Register signal handler
signal.signal(signal.SIGUSR1, handle_signal)

def main():
    worker_id = os.getpid()
    print(f"🚀 Worker Multi instance started with PID: {worker_id}")
    
    task_counter = 0
    
    try:
        while True:
            task_counter += 1
            
            # Each instance does different work
            work_type = random.choice(['processing_data', 'sending_emails', 'cleaning_cache'])
            work_time = random.uniform(1, 4)
            
            print(f"Worker Multi (PID: {worker_id}): Task {task_counter} - {work_type} for {work_time:.1f}s")
            
            # Simulate work
            time.sleep(work_time)
            
            # Simulate occasional failures for testing
            if random.random() < 0.05:  # 5% chance of failure
                print(f"❌ Worker Multi (PID: {worker_id}): Simulating failure!")
                sys.exit(2)  # Exit with error code 2
                
    except KeyboardInterrupt:
        print(f"Worker Multi (PID: {worker_id}): Shutting down gracefully")
    except Exception as e:
        print(f"Worker Multi (PID: {worker_id}): Error - {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()