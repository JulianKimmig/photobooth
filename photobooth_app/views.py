import time

import cv2
import numpy as np
import os

import shutil
import subprocess
from django.http import StreamingHttpResponse, JsonResponse
from django.shortcuts import render, redirect
from django.views import View


from photobooth.settings import USEGPHOTO, TEMPDIR, STATICFILES_DIRS, ALLOW_PRINTING, SHOWBUTTONS
from photobooth_app.models import Photo, Media
from photobooth_app.videocamera import VideoCamera

VIDEOFEED = None

def commands(request):
    return JsonResponse({"opencommands": VIDEOFEED.pending_qr_commands if VIDEOFEED is not None else []})

def index(request):
    global VIDEOFEED
    if VIDEOFEED is None:
        VIDEOFEED = VideoCamera(imageprocessor=qr_code_command_parser)
    context = {'showbuttons':request.GET.get("showbuttons",SHOWBUTTONS)}
    VIDEOFEED.allowed_qr_commands=['Photo']
    return render(request, 'index.html', context)

def display(im, decodedObjects):
    for decodedObject in decodedObjects:
        points = decodedObject.polygon
        # If the points do not form a quad, find convex hull
        if len(points) > 4 :
            hull = cv2.convexHull(np.array([point for point in points], dtype=np.float32))
            hull = list(map(tuple, np.squeeze(hull)))
        else :
            hull = points

        # Number of points in the convex hull
        n = len(hull)

        # Draw the convext hull
        for j in range(0,n):
            cv2.line(im, hull[j], hull[ (j+1) % n], (255,0,0),)
    return im

def qr_code_command_parser(image):
#    image = display(image, VIDEOFEED.decodedObjects)
    return image


def new_photo(request):
    os.chdir(TEMPDIR)
    filename = str(int(time.time()))
    if USEGPHOTO:
        filename=filename+".jpg"
        p = subprocess.Popen(('gphoto2','--force-overwrite', '--capture-image-and-download' ,'--filename',filename))
        p.wait()
#        os.system("gphoto2 --force-overwrite --capture-image-and-download --filename \""+filename+"\"")
    else:
        global VIDEOFEED
        if VIDEOFEED is None:
            VIDEOFEED = VideoCamera(imageprocessor=qr_code_command_parser)
        filename = VIDEOFEED.snapshot(filename)

    photo = Photo.objects.create(media=os.path.join(TEMPDIR,filename))

    response = redirect("photobooth_app:postproduction",id = photo.id)
    print(request.GET)
    response['Location'] += '?'+'&'.join([str(key)+"="+str(value) for key,value in request.GET.items()])
    return response

def recordvideo(request):
    t = 10
    os.chdir(TEMPDIR)
    if USEGPHOTO:
        os.system("gphoto2 --force-overwrite --capture-image-and-download")
    else:
        global VIDEOFEED
        if VIDEOFEED is None:
            VIDEOFEED = VideoCamera(imageprocessor=qr_code_command_parser)
        VIDEOFEED.record(str(int(time.time())),seconds=t)

    response =  redirect('photobooth_app:index')
    response['Location'] += '?'+'&'.join([str(key)+"="+str(value) for key,value in request.GET.items()])
    return response

def file_list(request):
    img_list =os.listdir(TEMPDIR)
    return render(request,'gallery.html', {'images': img_list})


def video_feed(request):
    global VIDEOFEED
    try:
        if VIDEOFEED is None:
            VIDEOFEED = VideoCamera(imageprocessor=qr_code_command_parser)
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


class PostProduction(View):
    def get(self,request,id):
        global VIDEOFEED
        if VIDEOFEED is None:
            VIDEOFEED = VideoCamera(imageprocessor=qr_code_command_parser)

        VIDEOFEED.pending_qr_commands = []
        VIDEOFEED.allowed_qr_commands=['Delete',"Save",]
        if ALLOW_PRINTING:
            VIDEOFEED.allowed_qr_commands.append("Print")

        try:
           media = Media.objects.get(id=id)
        except:
            media = None
        if media is None:
            response =  redirect('photobooth_app:index')
            response['Location'] += '?'+'&'.join([str(key)+"="+str(value) for key,value in request.GET.items()])
            return response

        if not os.path.exists(media.media):
            media.delete()
            response =  redirect('photobooth_app:index')
            response['Location'] += '?'+'&'.join([str(key)+"="+str(value) for key,value in request.GET.items()])
            return response

        path = os.path.relpath(media.media,STATICFILES_DIRS[0])
        return render(request,'postproduction.html', {'image_path': path,'showbuttons':request.GET.get("showbuttons",SHOWBUTTONS)})

    def post(self,request,id):
        try:
            media = Media.objects.get(id=id)
        except:
            media = None

        if media is None:
            response =  redirect('photobooth_app:index')
            response['Location'] += '?'+'&'.join([str(key)+"="+str(value) for key,value in request.GET.items()])
            return response

        if not os.path.exists(media.media):
            media.delete()
            response =  redirect('photobooth_app:index')
            response['Location'] += '?'+'&'.join([str(key)+"="+str(value) for key,value in request.GET.items()])
            return response

        action = request.POST.get('action',)
        if action == 'save':
            newdir = os.path.join(STATICFILES_DIRS[0],"media",os.path.basename(media.media))
            shutil.move(media.media,newdir)
            media.media = newdir
            media.save()
        elif action == 'delete':
            os.remove(media.media)
            media.delete()

        response =  redirect('photobooth_app:index')
        response['Location'] += '?'+'&'.join([str(key)+"="+str(value) for key,value in request.GET.items()])
        return response