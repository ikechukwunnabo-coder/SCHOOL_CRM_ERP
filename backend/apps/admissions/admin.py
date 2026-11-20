from django.contrib import admin

from .models import AdmissionDecision, Application, ApplicationDocument, Enquiry

admin.site.register(Enquiry)
admin.site.register(Application)
admin.site.register(AdmissionDecision)
admin.site.register(ApplicationDocument)
