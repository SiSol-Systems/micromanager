from django.db import models
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey

class TaggedItem(models.Model):
    tag = models.CharField(max_length=20)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True)

    class Meta:
        unique_together=("content_type","object_id","tag","user")

    def __str__(self):
        return self.tag
