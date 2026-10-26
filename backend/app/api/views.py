
from datetime import timedelta

from django.db import IntegrityError, transaction
from django.db.models import Avg
from django.db.models.functions import ExtractHour
from django.shortcuts import get_object_or_404
from django.utils import timezone

from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import Camera, Counter, QueueHistory, QueueStatus


QUEUE_ALERT_THRESHOLD = 6
CAMERA_OFFLINE_AFTER_SECONDS = 15
HISTORY_MIN_INTERVAL_SECONDS = 60


def queue_data(item):
    count = item.current_queue_count

    if count >= QUEUE_ALERT_THRESHOLD:
        alert_level = "HIGH"
        alert_message = "Queue is crowded. Consider opening another counter."
    elif count >= max(1, QUEUE_ALERT_THRESHOLD // 2):
        alert_level = "MEDIUM"
        alert_message = "Queue is growing."
    else:
        alert_level = "NORMAL"
        alert_message = "Queue is under control."

    return {
        "id": item.id,
        "counter": item.counter.name,
        "counter_status": item.counter.status,
        "current_queue_count": count,
        "daily_entries": item.daily_entries,
        "total_entries": item.total_entries,
        "alert_level": alert_level,
        "alert_message": alert_message,
        "alert_threshold": QUEUE_ALERT_THRESHOLD,
        "updated_at": item.updated_at,
    }


def record_queue_history(item, force=False):
    now = timezone.now()
    last_record = (
        QueueHistory.objects.filter(queue_status=item)
        .order_by("-recorded_at")
        .first()
    )

    should_record = (
        force
        or last_record is None
        or last_record.queue_count != item.current_queue_count
        or (now - last_record.recorded_at).total_seconds()
        >= HISTORY_MIN_INTERVAL_SECONDS
    )

    if should_record:
        QueueHistory.objects.create(
            queue_status=item,
            queue_count=item.current_queue_count,
            recorded_at=now,
        )


def camera_data(camera):
    now = timezone.now()
    online = (
        camera.last_heartbeat is not None
        and (now - camera.last_heartbeat).total_seconds()
        <= CAMERA_OFFLINE_AFTER_SECONDS
    )

    if not camera.is_enabled:
        health_status = "DISABLED"
    elif online:
        health_status = "ONLINE"
    else:
        health_status = "OFFLINE"

    return {
        "id": camera.id,
        "name": camera.name,
        "source": camera.source,
        "is_enabled": camera.is_enabled,
        "is_online": online,
        "health_status": health_status,
        "last_heartbeat": camera.last_heartbeat,
        "last_frame_at": camera.last_frame_at,
        "created_at": camera.created_at,
        "updated_at": camera.updated_at,
    }


@api_view(["GET"])
def health_check(request):
    return Response({
        "status": "success",
        "message": "Queue Management System API is running",
    })


@api_view(["GET"])
def queue_status_list(request):
    statuses = QueueStatus.objects.select_related("counter").all()
    return Response([queue_data(item) for item in statuses])


@api_view(["GET"])
def queue_status_detail(request, queue_status_id):
    item = get_object_or_404(
        QueueStatus.objects.select_related("counter"),
        id=queue_status_id,
    )
    return Response(queue_data(item))


@api_view(["PATCH"])
def update_queue_status(request, queue_status_id):
    item = get_object_or_404(
        QueueStatus.objects.select_related("counter"),
        id=queue_status_id,
    )

    allowed = {"current_queue_count", "total_entries"}
    if not request.data or set(request.data.keys()) - allowed:
        return Response(
            {"error": "Provide current_queue_count and/or total_entries only."},
            status=400,
        )

    if item.counter.status not in {
        Counter.Status.ACTIVE,
        Counter.Status.AVAILABLE,
    }:
        return Response(
            {"error": "Queue status cannot be updated because the counter is not active or available."},
            status=400,
        )

    for field, value in request.data.items():
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            return Response(
                {"error": f"{field} must be a non-negative integer."},
                status=400,
            )
        setattr(item, field, value)

    item.save()
    record_queue_history(item)

    return Response({
        **queue_data(item),
        "message": "Queue status updated successfully",
    })


@api_view(["POST"])
def record_customer_entry(request, queue_status_id):
    with transaction.atomic():
        item = get_object_or_404(
            QueueStatus.objects.select_for_update().select_related("counter"),
            id=queue_status_id,
        )

        if item.counter.status not in {
            Counter.Status.ACTIVE,
            Counter.Status.AVAILABLE,
        }:
            return Response(
                {"error": "Cannot record an entry for an inactive counter."},
                status=400,
            )

        today = timezone.localdate()
        if item.daily_entries_date != today:
            item.daily_entries = 0
            item.daily_entries_date = today

        item.daily_entries += 1
        item.total_entries += 1
        item.save(update_fields=[
            "daily_entries",
            "daily_entries_date",
            "total_entries",
            "updated_at",
        ])

    return Response({
        **queue_data(item),
        "message": "Customer entry recorded successfully",
    })


@api_view(["POST"])
def record_entry_exit_event(request, queue_status_id):
    event_type = request.data.get("event_type")

    if event_type not in {"ENTRY", "EXIT"}:
        return Response(
            {"error": "event_type must be ENTRY or EXIT."},
            status=400,
        )

    with transaction.atomic():
        item = get_object_or_404(
            QueueStatus.objects.select_for_update().select_related("counter"),
            id=queue_status_id,
        )

        if item.counter.status not in {
            Counter.Status.ACTIVE,
            Counter.Status.AVAILABLE,
        }:
            return Response(
                {"error": "Cannot record an event for an inactive counter."},
                status=400,
            )

        if event_type == "ENTRY":
            today = timezone.localdate()
            if item.daily_entries_date != today:
                item.daily_entries = 0
                item.daily_entries_date = today

            item.daily_entries += 1
            item.total_entries += 1

            item.save(update_fields=[
                "daily_entries",
                "daily_entries_date",
                "total_entries",
                "updated_at",
            ])

    return Response({
        **queue_data(item),
        "event_type": event_type,
        "message": f"{event_type.title()} event recorded successfully",
    })


@api_view(["GET"])
def counter_list(request):
    counters = Counter.objects.all().order_by("id")
    return Response([
        {
            "id": counter.id,
            "name": counter.name,
            "status": counter.status,
            "created_at": counter.created_at,
            "updated_at": counter.updated_at,
        }
        for counter in counters
    ])


@api_view(["POST"])
def create_counter(request):
    name = request.data.get("name")
    status = request.data.get("status", Counter.Status.UNKNOWN)
    valid_statuses = [choice.value for choice in Counter.Status]

    if not isinstance(name, str) or not name.strip():
        return Response(
            {"error": "A valid counter name is required."},
            status=400,
        )

    if not isinstance(status, str) or status not in valid_statuses:
        return Response({
            "error": "Invalid counter status.",
            "valid_statuses": valid_statuses,
        }, status=400)

    name = name.strip()
    if Counter.objects.filter(name__iexact=name).exists():
        return Response(
            {"error": "A counter with this name already exists."},
            status=400,
        )

    try:
        with transaction.atomic():
            counter = Counter.objects.create(name=name, status=status)
            item = QueueStatus.objects.create(counter=counter)
    except IntegrityError:
        return Response(
            {"error": "Could not create counter; it may already exist."},
            status=400,
        )

    return Response({
        "id": counter.id,
        "name": counter.name,
        "status": counter.status,
        "queue_status_id": item.id,
        "current_queue_count": item.current_queue_count,
        "total_entries": item.total_entries,
        "message": "Counter and queue status created successfully",
    }, status=201)


@api_view(["PATCH"])
def update_counter_status(request, counter_id):
    counter = get_object_or_404(Counter, id=counter_id)

    if set(request.data.keys()) != {"status"}:
        return Response(
            {"error": "Provide only the status field."},
            status=400,
        )

    status = request.data["status"]
    valid_statuses = [choice.value for choice in Counter.Status]

    if not isinstance(status, str) or status not in valid_statuses:
        return Response({
            "error": "Invalid counter status.",
            "valid_statuses": valid_statuses,
        }, status=400)

    counter.status = status
    counter.save(update_fields=["status", "updated_at"])

    return Response({
        "id": counter.id,
        "name": counter.name,
        "status": counter.status,
        "message": "Counter status updated successfully",
    })


@api_view(["GET"])
def camera_list(request):
    cameras = Camera.objects.all().order_by("id")
    return Response([camera_data(camera) for camera in cameras])


@api_view(["PATCH"])
def update_camera_status(request, camera_id):
    camera = get_object_or_404(Camera, id=camera_id)

    if set(request.data.keys()) != {"is_enabled"}:
        return Response(
            {"error": "Provide only the is_enabled field."},
            status=400,
        )

    enabled = request.data["is_enabled"]
    if not isinstance(enabled, bool):
        return Response(
            {"error": "is_enabled must be true or false."},
            status=400,
        )

    camera.is_enabled = enabled
    camera.save(update_fields=["is_enabled", "updated_at"])

    return Response({
        "id": camera.id,
        "name": camera.name,
        "is_enabled": camera.is_enabled,
        "message": "Camera status updated successfully",
    })


@api_view(["POST"])
def camera_heartbeat(request, camera_id):
    camera = get_object_or_404(Camera, id=camera_id)

    if not camera.is_enabled:
        return Response({"error": "Camera is disabled."}, status=400)

    now = timezone.now()
    camera.last_heartbeat = now
    camera.last_frame_at = now
    camera.save(update_fields=[
        "last_heartbeat",
        "last_frame_at",
        "updated_at",
    ])

    return Response({
        "id": camera.id,
        "health_status": "ONLINE",
        "last_heartbeat": camera.last_heartbeat,
        "message": "Camera heartbeat received",
    })


@api_view(["GET"])
def peak_hour_analytics(request):
    today = timezone.localdate()
    start = timezone.make_aware(
        timezone.datetime.combine(
            today,
            timezone.datetime.min.time(),
        )
    )
    end = start + timedelta(days=1)

    rows = (
        QueueHistory.objects
        .filter(recorded_at__gte=start, recorded_at__lt=end)
        .annotate(hour=ExtractHour("recorded_at"))
        .values("hour")
        .annotate(average_queue=Avg("queue_count"))
        .order_by("hour")
    )

    hours = [
        {
            "hour": row["hour"],
            "label": f"{row['hour']:02d}:00",
            "average_queue": round(row["average_queue"] or 0, 2),
        }
        for row in rows
    ]

    peak_hour = max(
        hours,
        key=lambda row: row["average_queue"],
        default=None,
    )

    return Response({
        "date": str(today),
        "hours": hours,
        "peak_hour": peak_hour,
        "message": (
            "Analytics are based on recorded queue snapshots."
            if hours
            else "No queue history recorded today yet. Keep the detector running."
        ),
    })


@api_view(["GET"])
def counter_recommendations(request):
    statuses = list(
        QueueStatus.objects.select_related("counter").all()
    )
    total_queue = sum(
        item.current_queue_count for item in statuses
    )

    available = [
        item.counter.name
        for item in statuses
        if item.counter.status == Counter.Status.AVAILABLE
    ]
    active = [
        item.counter.name
        for item in statuses
        if item.counter.status == Counter.Status.ACTIVE
    ]

    should_open = (
        total_queue >= QUEUE_ALERT_THRESHOLD and bool(available)
    )

    if should_open:
        recommendation = available[0]
        message = (
            f"Consider opening {recommendation}. "
            f"Combined queue count is {total_queue}."
        )
    elif total_queue >= QUEUE_ALERT_THRESHOLD:
        recommendation = None
        message = (
            "Queue is crowded, but no counter is marked AVAILABLE. "
            "Check staffing and counter status."
        )
    else:
        recommendation = None
        message = (
            "No additional counter is needed based on the current threshold."
        )

    return Response({
        "total_queue_count": total_queue,
        "alert_threshold": QUEUE_ALERT_THRESHOLD,
        "active_counters": active,
        "available_counters": available,
        "should_open_counter": should_open,
        "recommended_counter": recommendation,
        "message": message,
    })
