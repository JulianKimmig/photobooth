import os
import threading
import time

import cv2
from django.http import StreamingHttpResponse
from django.shortcuts import render

from photobooth.settings import BASE_DIR


def index(request):
    context = {}
    return render(request, 'index.html', context)


def new_photo(request):
    tempdir=os.path.join(BASE_DIR,"temp")
    if not os.path.exists(tempdir):
        os.makedirs(tempdir)
    os.chdir(tempdir)
    os.system("gphoto2 --force-overwrite --capture-image-and-download")
    return render(request, 'index.html')


VIDEOFEED = None

def video_feed(request):
    global VIDEOFEED
    try:
        if VIDEOFEED is None:
            VIDEOFEED = VideoCamera()
        return StreamingHttpResponse(
            gen(VIDEOFEED),
            content_type="multipart/x-mixed-replace;boundary=frame",
        )
    except:  # This is bad! replace it with proper handling
        pass



def gen(camera):
    while True:
        frame = camera.get_frame()
        yield (b"--frame\r\n" b"Content-Type: image/jpeg\r\n\r\n" + frame + b"\r\n\r\n")

class VideoCamera(object):
    def __init__(self, autosave=True):
        self.autosave = autosave
        self.video = cv2.VideoCapture(0)
        (self.grabbed, self.frame) = self.video.read()

        if self.autosave:
            threading.Thread(target=self.update, args=()).start()

    def __del__(self):
        self.video.release()



    def get_frame(self):
        image = self.frame
        ret, jpeg = cv2.imencode(".jpg", image)
        return jpeg.tobytes()

    def update(self):
        while True:
            (self.grabbed, self.frame) = self.video.read()
