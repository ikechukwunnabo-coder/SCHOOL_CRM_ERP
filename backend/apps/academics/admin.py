from django.contrib import admin

from .models import AcademicSession, Arm, ClassEnrolment, ClassLevel, Subject, SubjectOffering, Term

for model in (AcademicSession, Term, ClassLevel, Arm, Subject, SubjectOffering, ClassEnrolment):
    admin.site.register(model)
