from django.db import models


class Media(models.Model):
    media = models.FilePathField()

class Photo(Media):
    pass

