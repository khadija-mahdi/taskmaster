# monitor.py - Health monitoring service
import time
import requests
import logging
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('monitor')

def check_services():
    services = [
        ('webapp', 'http://localhost:5000/health'),
        ('api', 'http://localhost:5001/')
    ]
    
    for name, url in services:
        try:
            response = requests.get(url, timeout=5)
            status = 'UP' if response.status_code == 200 else 'DOWN'
            logger.info(f"Service {name} is {status} (HTTP {response.status_code})")
        except Exception as e:
            logger.warning(f"Service {name} is DOWN: {e}")

def main():
    logger.info(f"Monitor started with PID: {os.getpid()}")
    
    try:
        while True:
            check_services()
            time.sleep(10)  # Check every 10 seconds
            
    except KeyboardInterrupt:
        logger.info("Monitor shutting down gracefully")

if __name__ == '__main__':
    main()