from django.contrib import admin
from .models import Profile, Plan, PlanItem, PlaceInfo
from django.contrib.auth.admin import UserAdmin

admin.site.register(Profile, UserAdmin)

admin.site.register(Plan)
admin.site.register(PlanItem)
admin.site.register(PlaceInfo)
