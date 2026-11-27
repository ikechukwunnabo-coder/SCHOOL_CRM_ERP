from django.contrib import admin

from .models import CmsMenuItem, CmsPage, CmsPost

admin.site.register(CmsPage)
admin.site.register(CmsPost)
admin.site.register(CmsMenuItem)
