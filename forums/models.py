import uuid

from django.db import models
from django.db.models.signals import pre_delete
from django.dispatch import receiver

from inferencebackend.settings import FORUM_FILE_LOCATION

class Forums(models.Model):
    '''
    Forums model. Stores CSV file for forum and other related information

    Fields
        - id
        - csv_file*
        - date_created
    '''

    id = models.UUIDField(
        primary_key=True,
        unique=True,
        blank=False,
        default=uuid.uuid4,
        editable=False
    )
    
    csv_file = models.FileField(blank=False, upload_to=FORUM_FILE_LOCATION)

    date_created = models.DateTimeField(auto_now_add=True, editable=False)

    def get_file_name(self):
        '''
        Get the name of the forum CSV file
        '''

        full_file = self.csv_file.name.split('/')[-1]

        return full_file.replace('.csv', '')

    def __str__(self):
        return f'{self.id} saved at {self.csv_file.name}'

@receiver(pre_delete, sender=Forums)
def pre_delete_forums_file(sender, instance, **kwargs):
    '''
    Delete CSV file when forums object is deleted
    '''
    
    instance.csv_file.storage.delete(instance.csv_file.name)
