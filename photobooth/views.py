import os
import time

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