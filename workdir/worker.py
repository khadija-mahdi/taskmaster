import sys
import time


time.sleep(5)
sys.exit(1)



# # # worker.py - Background worker example
# import time
# import logging
# import os
# import random

# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger('worker')

# def main():
#     logger.info(f"Worker started with PID: {os.getpid()}")
#     counter = 0
    
#     try:
#         while True:
#             counter += 1
#             # Simulate work
#             work_time = random.uniform(1, 5)
#             logger.info(f"Worker processing task {counter} (takes {work_time:.2f}s)")
#             time.sleep(work_time)
            
#             # Simulate occasional errors
#             if random.random() < 0.1:
#                 logger.error("Simulated worker error!")
                
#     except KeyboardInterrupt:
#         logger.info("Worker shutting down gracefully")
#     except Exception as e:
#         logger.error(f"Worker crashed: {e}")
#         raise

# if __name__ == '__main__':
#     main()