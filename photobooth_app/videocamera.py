import os
import time

import cv2
import threading
import pyzbar.pyzbar as pyzbar
from pyzbar.pyzbar import ZBarSymbol

from photobooth.settings import USEPICAMERA

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
            os.system('MP4Box -add '+filename+'.h264 '+filename+'.mp4')
            os.system('rm '+filename+'.h264')

        def snapshot(self, filename):
            filename = filename+'.jpg'
            self.camera.capture(filename,resize=self.camera.MAX_RESOLUTION)
            return filename
else:
    class WebcamVideoStream:
        def __init__(self, src=cv2.CAP_DSHOW):
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
            filename=filename+'.jpg'
            cv2.imwrite(filename,self.read())
            return filename


class VideoStream:
    def __init__(self, src=0, usePiCamera=False, resolution=(1280,720),
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
    def __init__(self,imageprocessor=None):
        self.imageprocessor = imageprocessor
        self.video = VideoStream(usePiCamera=USEPICAMERA).start()
        threading.Thread(target=self.run_qr_parser).start()
        self.allowed_qr_commands=[]
        self.pending_qr_commands=[]
        time.sleep(2)


    def __del__(self):
        self.video.stop()


    def run_qr_parser(self):
        while True:
            image = self.video.read()
            self.decodedObjects = pyzbar.decode(image, symbols=[ZBarSymbol.QRCODE])

            # Print results
            for obj in self.decodedObjects:
                command= obj.data.decode('ASCII')
                if command in self.allowed_qr_commands:
                    print(command)
                    self.pending_qr_commands.append(command)
                    self.pending_qr_commands = list(set(self.pending_qr_commands))
                else:
                    print(command)
            time.sleep(0.1)


    def get_frame(self):
        image = self.video.read()
        if self.imageprocessor is not None:
            image = self.imageprocessor(image)
        try:
            ret, jpeg = cv2.imencode(".jpg", image)
        except:
            return b''
        return jpeg.tobytes()

    def record(self, filename,seconds):
        self.video.record(filename,seconds)

    def snapshot(self, filename):
        return self.video.snapshot(filename)


