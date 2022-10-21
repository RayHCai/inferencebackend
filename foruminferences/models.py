import uuid

from django.db import models
from django.db.models.signals import pre_delete
from django.dispatch import receiver

from inferencebackend.settings import INFERENCES_FILE_LOCATION

from forums.models import Forums

class ForumInferences(models.Model):
    '''
    Forum Inferences model. Stores forum answer inferences.

    Fields
        - id
        - forum*
        - infereces
        - data_created
    '''

    id = models.UUIDField(
        primary_key=True, 
        unique=True, 
        blank=False, 
        default=uuid.uuid4, 
        editable=False
    )

    forum = models.ForeignKey(Forums, on_delete=models.CASCADE)

    inferences = models.FileField(upload_to=INFERENCES_FILE_LOCATION)

    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'Inferences for {self.forum.get_file_name()}'

@receiver(pre_delete, sender=ForumInferences)
def pre_delete_forums_inference(sender, instance, **kwargs):
    '''
    Delete inference JSON file when forums inference object is deleted
    '''

    instance.inferences.storage.delete(instance.inferences.name)
