import os
from cv2 import namedWindow, VideoCapture, imshow, waitKey, destroyWindow
from PIL import Image
from numpy import array, uint8
from recognize_bricks import get_brick_feed
import time

def webcam_feed():
    window_name = "Let's sort several cubic metres of LEGO (fast (hopefully)) !"
    namedWindow(window_name)
    vc = VideoCapture(0)
    #0: macos webcam, 1: iphone

    if vc.isOpened(): 
        # try to get the first frame
        rval, frame = vc.read()
    else:
        rval = False

    while rval:
        rval, frame = vc.read()

        img = Image.fromarray(uint8(frame))#.convert('RGB')
        # TODO correct the mirror effect of the feed and the color weird stuff happening
        temp_image_path = './tmp/webcam_capture.jpg'
        if not os.path.exists('./tmp/'):
            os.mkdir('./tmp/')
        img.save(temp_image_path)

        image = get_brick_feed(temp_image_path)
        time.sleep(0.4) # to avoid too many API calls
        imshow(window_name, array(image))

        key = waitKey(20)
        if key == 27: # exit on ESC
            break

    destroyWindow(window_name)
    vc.release()