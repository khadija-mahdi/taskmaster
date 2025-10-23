#!/usr/bin/env python3
import sys

print("Echo test process started")
print("Type something and press Enter - I'll echo it back")
print()

while True:
    try:
        line = sys.stdin.readline()
        if not line:  # EOF
            break
        
        line = line.strip()
        if line:
            print(f"You said: {line}")
            sys.stdout.flush()
            
    except (KeyboardInterrupt, EOFError, OSError):
        print("\nProcess terminated")
        sys.stdout.flush()
        break