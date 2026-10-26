
from django.contrib import admin
from django.urls import path

from app.api.views import (
    camera_heartbeat,
    camera_list,
    counter_list,
    counter_recommendations,
    create_counter,
    health_check,
    peak_hour_analytics,
    queue_status_detail,
    queue_status_list,
    record_customer_entry,
    record_entry_exit_event,
    update_camera_status,
    update_counter_status,
    update_queue_status,
)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/health/", health_check, name="health_check"),

    path("api/queue-status/", queue_status_list, name="queue_status_list"),
    path(
        "api/queue-status/<int:queue_status_id>/",
        queue_status_detail,
        name="queue_status_detail",
    ),
    path(
        "api/queue-status/<int:queue_status_id>/update/",
        update_queue_status,
        name="update_queue_status",
    ),
    path(
        "api/queue-status/<int:queue_status_id>/record-entry/",
        record_customer_entry,
        name="record_customer_entry",
    ),
    path(
        "api/queue-status/<int:queue_status_id>/entry-exit/",
        record_entry_exit_event,
        name="record_entry_exit_event",
    ),

    path("api/counters/", counter_list, name="counter_list"),
    path("api/counters/create/", create_counter, name="create_counter"),
    path(
        "api/counters/<int:counter_id>/status/",
        update_counter_status,
        name="update_counter_status",
    ),
    path(
        "api/counter-recommendations/",
        counter_recommendations,
        name="counter_recommendations",
    ),

    path("api/cameras/", camera_list, name="camera_list"),
    path(
        "api/cameras/<int:camera_id>/status/",
        update_camera_status,
        name="update_camera_status",
    ),
    path(
        "api/cameras/<int:camera_id>/heartbeat/",
        camera_heartbeat,
        name="camera_heartbeat",
    ),

    path(
        "api/analytics/peak-hours/",
        peak_hour_analytics,
        name="peak_hour_analytics",
    ),
]
