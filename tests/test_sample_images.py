import sys 
import time
sys.path.extend(['./src/', '../src/'])
from recognize_bricks import find_bricks, show_bricks_found
import numpy as np


# image_path = 'img_test_lib/s-l1200.png'
image_path = 'img_test_lib/s-l1200.png'
if True:
    start = time.time()
    results = find_bricks(image_path)
    np.save('results.npy', results) # save results to test without API calls
    duration = time.time() - start
    print(f"took {duration:.2f}s")
results = np.load('results.npy', allow_pickle=True) # load results from previous test

show_bricks_found(results, image_path)