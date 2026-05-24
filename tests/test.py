import sys 
import time
sys.path.extend(['./src/', '../src/'])
from recognize_bricks import find_bricks

image_path = 'img_test_lib/s-l1200.png'
start = time.time()
results = find_bricks(image_path)
duration = time.time() - start
print(f"took {duration:.2f}s")