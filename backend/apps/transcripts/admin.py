from django.contrib import admin

from .models import Transcript, TranscriptEvent, TranscriptRequest, TranscriptVerification

admin.site.register(TranscriptRequest)
admin.site.register(Transcript)
admin.site.register(TranscriptEvent)
admin.site.register(TranscriptVerification)
