import json
from hashlib import md5

from django.db import models
from django.core.urlresolvers import reverse


class Payload(models.Model):
    payload_hash = models.CharField(max_length=32, unique=True,
                                    blank=True, null=True)
    payload = models.TextField()
    created = models.DateTimeField(auto_now_add=True)
    last_viewed = models.DateTimeField(blank=True, null=True)

    def _presave(self):
        self.payload_hash = md5(self.payload.encode('utf-8')).hexdigest()

    def save(self):
        self._presave()
        super(Payload, self).save()

    def get_absolute_url(self):
        return reverse("testbed_main",
                       kwargs={'payload_hash': self.payload_hash})

    def __unicode__(self):
        payload = json.loads(self.payload)
        handler = payload.get('handler', None)
        if handler:
            return u"{}-{}".format(handler, self.payload_hash[-8:])
        else:
            return self.payload_hash[-8:]
