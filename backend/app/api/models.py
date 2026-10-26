
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone


class Counter(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        AVAILABLE = "AVAILABLE", "Available"
        CLOSED = "CLOSED", "Closed"
        UNKNOWN = "UNKNOWN", "Unknown"

    name = models.CharField(max_length=100, unique=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.UNKNOWN,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class QueueStatus(models.Model):
    counter = models.ForeignKey(
        Counter,
        on_delete=models.CASCADE,
        related_name="queue_statuses",
    )
    current_queue_count = models.PositiveIntegerField(
        default=0,
        validators=[MinValueValidator(0)],
    )
    daily_entries = models.PositiveIntegerField(
        default=0,
        validators=[MinValueValidator(0)],
    )
    daily_entries_date = models.DateField(default=timezone.localdate)
    total_entries = models.PositiveIntegerField(
        default=0,
        validators=[MinValueValidator(0)],
    )
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.counter.name} - Queue: {self.current_queue_count}"


class Camera(models.Model):
    name = models.CharField(max_length=100, unique=True)
    source = models.CharField(max_length=500)
    is_enabled = models.BooleanField(default=True)
    last_heartbeat = models.DateTimeField(null=True, blank=True)
    last_frame_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class QueueHistory(models.Model):
    queue_status = models.ForeignKey(
        QueueStatus,
        on_delete=models.CASCADE,
        related_name="history",
    )
    queue_count = models.PositiveIntegerField()
    recorded_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        ordering = ["-recorded_at"]
        indexes = [
            models.Index(fields=["queue_status", "recorded_at"]),
        ]

    def __str__(self):
        return f"{self.queue_status.counter.name}: {self.queue_count}"
