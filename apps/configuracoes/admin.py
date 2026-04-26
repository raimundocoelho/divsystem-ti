from django.contrib import admin

from .models import Setting


@admin.register(Setting)
class SettingAdmin(admin.ModelAdmin):
    list_display = ("key", "tenant", "updated_at")
    list_filter = ("tenant",)
    search_fields = ("key", "value")
