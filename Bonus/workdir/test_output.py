#!/usr/bin/env python3
import time
import sys

print("Test process started - generating output every 2 seconds...")
print("This is a test process for attach/detach functionality")
sys.stdout.flush()

counter = 0
while True:
    counter += 1
    print(f"Output #{counter} - {time.strftime('%H:%M:%S')}")
    sys.stdout.flush()
    time.sleep(2)