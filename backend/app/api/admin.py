
from django.contrib import admin

from .models import Camera, Counter, QueueStatus


@admin.register(Counter)
class CounterAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "status", "created_at")
    list_filter = ("status",)
    search_fields = ("name",)


@admin.register(QueueStatus)
class QueueStatusAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "counter",
        "current_queue_count",
        "total_entries",
        "updated_at",
    )
    list_filter = ("counter",)
    search_fields = ("counter__name",)


@admin.register(Camera)
class CameraAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "source",
        "is_enabled",
        "created_at",
    )
    list_filter = ("is_enabled",)
    search_fields = ("name", "source")
