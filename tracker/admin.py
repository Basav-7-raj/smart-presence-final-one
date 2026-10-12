from django.contrib import admin
from .models import PersonProfile,PresenceRecord,UnknownEvent,SystemEvent,SystemSetting,LocationSite
admin.site.register([PersonProfile,PresenceRecord,UnknownEvent,SystemEvent,SystemSetting,LocationSite])
