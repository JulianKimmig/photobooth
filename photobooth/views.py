import io
import os
import threading
import time

import cv2
from django.http import StreamingHttpResponse
from django.shortcuts import render


from photobooth.settings import BASE_DIR, USEPICAMERA


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
    #try:
    if VIDEOFEED is None:
        VIDEOFEED = VideoCamera2()
    return StreamingHttpResponse(
        gen(VIDEOFEED),
        content_type="multipart/x-mixed-replace;boundary=frame",
    )
 #   except:  # This is bad! replace it with proper handling
 #       pass
#


def gen(camera):
    while True:
        try:
            frame = camera.get_frame()
            yield (b"--frame\r\n" b"Content-Type: image/jpeg\r\n\r\n" + frame + b"\r\n\r\n")
        except:
            pass

class StreamingOutput(object):
    def __init__(self):
        self.frame = None
        self.buffer = io.BytesIO()
        self.condition = threading.Condition()

    def write(self, buf):
        if buf.startswith(b'\xff\xd8'):
            # New frame, copy the existing buffer's content and notify all
            # clients it's available
            self.buffer.truncate()
            with self.condition:
                frame =  self.buffer.getvalue()
                if frame is not None:
                    self.frame = frame
                self.condition.notify_all()
            self.buffer.seek(0)
        return self.buffer.write(buf)

if USEPICAMERA:
    import picamera
    class PiVideoStream:
        def __init__(self, resolution=(320, 240), framerate=32):
            # initialize the camera and stream
            self.camera = picamera.PiCamera()
            self.camera.resolution = resolution
            self.camera.framerate = framerate
            self.rawCapture = picamera.PiRGBArray(self.camera, size=resolution)
            self.stream = self.camera.capture_continuous(self.rawCapture,
                                                         format="bgr", use_video_port=True)

            # initialize the frame and the variable used to indicate
            # if the thread should be stopped
            self.frame = None
            self.stopped = False
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


class VideoStream:
    def __init__(self, src=0, usePiCamera=False, resolution=(320, 240),
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

class VideoCamera2:
    def __init__(self, autosave=True):
        self.autosave = autosave
        self.video = VideoStream(usePiCamera=USEPICAMERA).start()
        (self.grabbed, self.frame) = self.video.read()

        if self.autosave:
            threading.Thread(target=self.update, args=()).start()

    def __del__(self):
        self.video.stop()



    def get_frame(self):
        image = self.frame
        ret, jpeg = cv2.imencode(".jpg", image)
        return jpeg.tobytes()

    def update(self):
        while True:
            (self.grabbed, self.frame) = self.video.read()

class VideoCamera(object):
    def __init__(self, autosave=True):
        self.autosave = autosave
        if USEPICAMERA:
            import io
            self.stream = StreamingOutput()
            self.video = picamera.PiCamera()
            self.video.capture_continuous(self.stream, format='jpeg',resize=(320, 240))
            #self.video.start_preview()
            #time.sleep(0.1)
        else:
            self.video = cv2.VideoCapture(0)
            (self.grabbed, self.frame) = self.video.read()

        if self.autosave:
            threading.Thread(target=self.update, args=()).start()

    def __del__(self):
        if USEPICAMERA:
            self.video.stop_recording()
            self.video.close()
        else:
            self.video.release()



    def get_frame(self):
        if USEPICAMERA:
            return self.frame

        image = self.frame
        ret, jpeg = cv2.imencode(".jpg", image)
        return jpeg.tobytes()

    def update(self):
        while True:
            if USEPICAMERA:
                with self.stream.condition:
                    self.stream.condition.wait()
                    self.frame = self.stream.frame
            else:
                (self.grabbed, self.frame) = self.video.read()
