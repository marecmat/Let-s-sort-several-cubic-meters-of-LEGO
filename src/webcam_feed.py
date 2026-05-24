from cv2 import namedWindow, VideoCapture, imshow, waitKey, destroyWindow

window_name = "window_name"
namedWindow(window_name)
vc = VideoCapture(0)

if vc.isOpened(): 
    # try to get the first frame
    rval, frame = vc.read()
else:
    rval = False

while rval:
    imshow(window_name, frame)
    rval, frame = vc.read()

    # Put the code here 

    
    key = waitKey(20)
    if key == 27: # exit on ESC
        break

destroyWindow(window_name)
vc.release()