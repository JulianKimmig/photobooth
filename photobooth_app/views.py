import time

import cv2
import numpy as np
import os

import shutil
import subprocess
from collections import namedtuple
from django.http import StreamingHttpResponse, JsonResponse
from django.shortcuts import render, redirect
from django.views import View

from photobooth.settings import USEGPHOTO, TEMPDIR, STATICFILES_DIRS, ALLOW_PRINTING, SHOWBUTTONS, MARK_QR_CODES, \
    JCONFIG
from photobooth_app.models import Photo, Media
from photobooth_app.videocamera import VideoCamera

if ALLOW_PRINTING:
    import cups

VIDEOFEED = None

def commands(request):
    return JsonResponse({"opencommands": VIDEOFEED.pending_qr_commands if VIDEOFEED is not None else []})

def index(request):
    global VIDEOFEED
    if VIDEOFEED is None:
        VIDEOFEED = VideoCamera(imageprocessor=qr_code_command_parser)
    context = {'showbuttons':request.GET.get("showbuttons",SHOWBUTTONS)}
    VIDEOFEED.allowed_qr_commands=['photo']
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

ACTIVE_FILTERS=[]
Filter = namedtuple('Filter',['name','matrix','alpha'])


SEPIA_FILTER=Filter(name='sepia',matrix=np.matrix([[0.272, 0.534, 0.131],
                                            [ 0.349, 0.686, 0.168],
                                            [ 0.393, 0.769, 0.189]
                                            ]),alpha=0.3)


if "sepia" in JCONFIG.get("settings","photobooth","filters",default=[]):
    ACTIVE_FILTERS.append(SEPIA_FILTER)

def cropimage(image,ratio=3.0625/3.125):
    height = int(min(image.shape[0],image.shape[1]/ratio))
    width = int(min(image.shape[1],height*ratio))

    x1=int((image.shape[1]-width)/2)
    x2=int(image.shape[1]-x1)
    y1=int((image.shape[0]-height)/2)
    y2=int(image.shape[0]-y1)
    return image[y1:y2, x1:x2]

def qr_code_command_parser(image):
    if MARK_QR_CODES:
        image = display(image, VIDEOFEED.decodedObjects)

    image = cropimage(image)

    for filter in ACTIVE_FILTERS:
        overlay = cv2.transform( image, filter.matrix )
        image = cv2.addWeighted(overlay, filter.alpha, image, 1 - filter.alpha,0)
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

    media_file=os.path.join(TEMPDIR,filename)
    photo = Photo.objects.create(media=media_file,edited_media=os.path.splitext(media_file)[0]+"_filtered_"+os.path.splitext(media_file)[1])

    shutil.copyfile(photo.media,photo.edited_media)
    image = cv2.imread(photo.edited_media)
    image = cropimage(image)
    if len(ACTIVE_FILTERS)>0:
        for filter in ACTIVE_FILTERS:
            overlay = cv2.transform( image, filter.matrix )
            image = cv2.addWeighted(overlay, filter.alpha, image, 1 - filter.alpha,0)

    cv2.imwrite(photo.edited_media,image)
    response = redirect("photobooth_app:postproduction",id = photo.id)
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
        VIDEOFEED.allowed_qr_commands=['delete',"save",]
        if ALLOW_PRINTING:
            VIDEOFEED.allowed_qr_commands.append("print")

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

        path = os.path.relpath(media.edited_media,STATICFILES_DIRS[0])
        return render(request,'postproduction.html', {'image_path': path,'showbuttons':request.GET.get("showbuttons",SHOWBUTTONS)})

    def post(self,request,id):
        VIDEOFEED.pending_qr_commands = []
        VIDEOFEED.allowed_qr_commands=[]
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
        if action == 'save' or action == 'print':
            try: VIDEOFEED.pending_qr_commands.remove('save')
            except:pass
            newdir = os.path.join(STATICFILES_DIRS[0],"media",os.path.basename(media.media))
            shutil.move(media.media,newdir)
            media.media = newdir

            newdir = os.path.join(STATICFILES_DIRS[0],"media",os.path.basename(media.edited_media))
            shutil.move(media.edited_media,newdir)
            media.edited_media = newdir

            media.save()

        if action == 'print':
            try: VIDEOFEED.pending_qr_commands.remove('print')
            except:pass

            conn = cups.Connection()
            printers = conn.getPrinters ()
            if len(printers)>0:
                printer_name=list(printers.keys())[0]
                conn.printFile (printer_name, media.edited_media, "Photobooth Image", {})


        if action == 'delete':
            try:os.remove(media.media)
            except:pass
            try:os.remove(media.edited_media)
            except:pass
            media.delete()

        response =  redirect('photobooth_app:index')
        response['Location'] += '?'+'&'.join([str(key)+"="+str(value) for key,value in request.GET.items()])
        return response