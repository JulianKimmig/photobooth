import io
import os
import threading
import time

import cv2
from django.http import StreamingHttpResponse
from django.shortcuts import render, redirect

from photobooth.settings import BASE_DIR, USEPICAMERA,USEGPHOTO


def index(request):
    context = {}
    return render(request, 'index.html', context)


def new_photo(request):
    tempdir=os.path.join(BASE_DIR,"temp")
    if not os.path.exists(tempdir):
        os.makedirs(tempdir)
    os.chdir(tempdir)

    if USEGPHOTO:
        os.system("gphoto2 --force-overwrite --capture-image-and-download")
    else:
        global VIDEOFEED
        if VIDEOFEED is None:
            VIDEOFEED = VideoCamera()
        VIDEOFEED.snapshot(str(int(time.time())))
    return redirect("index")

def recordvideo(request):
    tempdir=os.path.join(BASE_DIR,"temp")
    t = 10
    try:
        t = int(request.GET.get("t",t))
    except:pass

    if not os.path.exists(tempdir):
        os.makedirs(tempdir)
    os.chdir(tempdir)
    if USEGPHOTO:
        os.system("gphoto2 --force-overwrite --capture-image-and-download")
    else:
        global VIDEOFEED
        if VIDEOFEED is None:
            VIDEOFEED = VideoCamera()
        VIDEOFEED.record(str(int(time.time())),seconds=t)

    return redirect("index")


def file_list(request):
    tempdir=os.path.join(BASE_DIR,"temp")
    if not os.path.exists(tempdir):
        os.makedirs(tempdir)
    img_list =os.listdir(tempdir)
    return render(request,'gallery.html', {'images': img_list})

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
    except:
        pass



def gen(camera):
    while True:
        try:
            yield (b"--frame\r\n" b"Content-Type: image/jpeg\r\n\r\n" + camera.get_frame() + b"\r\n\r\n")
        except:
            pass

if USEPICAMERA:
    from picamera.array import PiRGBArray
    from picamera import PiCamera

    class PiVideoStream:
        def __init__(self, resolution=(320, 240), framerate=32):
            # initialize the camera and stream
            self.camera = PiCamera()
            self.camera.resolution = resolution
            self.camera.framerate = framerate
            self.rawCapture = PiRGBArray(self.camera, size=resolution)
            self.stream = self.camera.capture_continuous(self.rawCapture,
                                                         format="bgr", use_video_port=True)

            # initialize the frame and the variable used to indicate
            # if the thread should be stopped
            self.frame = None
            self.stopped = False

        def start(self):
            # start the thread to read frames from the video stream
            threading.Thread(target=self.update, args=()).start()
            return self

        def update(self):
            # keep looping infinitely until the thread is stopped
            for f in self.stream:
                # grab the frame from the stream and clear the stream in
                # preparation for the next frame
                self.frame = f.array
                self.rawCapture.truncate(0)

                # if the thread indicator variable is set, stop the thread
                # and resource camera resources
                if self.stopped:
                    self.stream.close()
                    self.rawCapture.close()
                    self.camera.close()
                    return

        def read(self):
            # return the frame most recently read
            return self.frame

        def stop(self):
            # indicate that the thread should be stopped
            self.stopped = True

        def record(self, filename,seconds):
            self.camera.start_recording(filename+'.h264')
            self.camera.wait_recording(seconds)
            self.camera.stop_recording()

        def snapshot(self, filename):
            print(filename)
            self.camera.capture(filename+'.jpg',use_video_port=True, splitter_port=1)
            print(filename)
else:
    class WebcamVideoStream:
        def __init__(self, src=0):
            # initialize the video camera stream and read the first frame
            # from the stream
            self.stream = cv2.VideoCapture(src)
            (self.grabbed, self.frame) = self.stream.read()

            # initialize the variable used to indicate if the thread should
            # be stopped
            self.stopped = False
        def start(self):
            # start the thread to read frames from the video stream
            threading.Thread(target=self.update, args=()).start()
            return self

        def update(self):
            # keep looping infinitely until the thread is stopped
            while True:
                # if the thread indicator variable is set, stop the thread
                if self.stopped:
                    return

                # otherwise, read the next frame from the stream
                (self.grabbed, self.frame) = self.stream.read()

        def read(self):
            # return the frame most recently read
            return self.frame

        def stop(self):
            # indicate that the thread should be stopped
            self.stopped = True

        def record(self, filename,seconds):
            pass

        def snapshot(self, filename):
            pass


class VideoStream:
    def __init__(self, src=0, usePiCamera=False, resolution=(1024,768),
                 framerate=32):
        # check to see if the picamera module should be used
        if usePiCamera:

            # initialize the picamera stream and allow the camera
            # sensor to warmup
            self.stream = PiVideoStream(resolution=resolution,
                                        framerate=framerate)
        else:
            self.stream = WebcamVideoStream(src=src)

    def start(self):
        # start the threaded video stream
        return self.stream.start()

    def update(self):
        # grab the next frame from the stream
        self.stream.update()

    def read(self):
        # return the current frame
        return self.stream.read()

    def stop(self):
        # stop the thread and release any resources
        self.stream.stop()

class VideoCamera:
    def __init__(self):
        self.video = VideoStream(usePiCamera=USEPICAMERA).start()
        time.sleep(2)

    def __del__(self):
        self.video.stop()



    def get_frame(self):
        image = self.video.read()
        try:
            ret, jpeg = cv2.imencode(".jpg", image)
        except:
            return b''
        return jpeg.tobytes()

    def record(self, filename,seconds):
        self.video.record(filename,seconds)

    def snapshot(self, filename):
        self.video.snapshot(filename)
