import uuid
from django.db import models


class Gauge(models.Model):
    """
    Represents a single flood monitoring gauge.
    """

    class Source(models.TextChoices):
        GOOGLE_FLOOD_HUB = "google_flood_hub", "Google Flood Hub"
        MANUAL = "manual", "Manual Input"

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        INACTIVE = "inactive", "Inactive"
        MAINTENANCE = "maintenance", "Maintenance"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    gauge_id = models.CharField(
        max_length=100,
        unique=True,
        db_index=True,
        help_text="The unique identifier for the gauge from its source.",
    )
    source = models.CharField(
        max_length=50, choices=Source.choices, default=Source.GOOGLE_FLOOD_HUB
    )
    name = models.CharField(max_length=255)
    location = models.CharField(max_length=255, blank=True)
    latitude = models.FloatField()
    longitude = models.FloatField()
    country_code = models.CharField(max_length=2)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.ACTIVE
    )
    quality_verified = models.BooleanField(
        default=False, help_text="Google Flood Hub quality verification status"
    )
    has_model = models.BooleanField(
        default=False, help_text="Has hydrological model for predictions"
    )
    
    # Administrative boundaries
    province = models.CharField(
        max_length=100, blank=True, null=True, 
        help_text="Province name (e.g., Punjab, Sindh)"
    )
    district = models.CharField(
        max_length=100, blank=True, null=True,
        help_text="District name"
    )
    tehsil = models.CharField(
        max_length=100, blank=True, null=True,
        help_text="Tehsil/Taluka name"
    )
    union_council = models.CharField(
        max_length=100, blank=True, null=True,
        help_text="Union Council name"
    )
    
    # Warning levels
    warning_level = models.FloatField(
        null=True, blank=True,
        help_text="Water level threshold for warning (meters)"
    )
    danger_level = models.FloatField(
        null=True, blank=True,
        help_text="Water level threshold for danger (meters)"
    )
    extreme_danger_level = models.FloatField(
        null=True, blank=True,
        help_text="Water level threshold for extreme danger (meters)"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Flood Gauge"
        verbose_name_plural = "Flood Gauges"

    def __str__(self):
        return f"{self.name} ({self.gauge_id})"


class Reading(models.Model):
    """
    Represents a water level reading from a gauge.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    gauge = models.ForeignKey(Gauge, on_delete=models.CASCADE, related_name="readings")
    timestamp = models.DateTimeField()
    water_level = models.FloatField(help_text="Water level in meters")
    flow_rate = models.FloatField(null=True, blank=True, help_text="Flow rate in m³/s")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-timestamp"]
        verbose_name = "Reading"
        verbose_name_plural = "Readings"

    def __str__(self):
        return f"{self.gauge.name} - {self.timestamp}"


class Prediction(models.Model):
    """
    Represents a predicted water level for a gauge.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    gauge = models.ForeignKey(
        Gauge, on_delete=models.CASCADE, related_name="predictions"
    )
    prediction_for_timestamp = models.DateTimeField()
    water_level = models.FloatField(help_text="Predicted water level in meters")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["prediction_for_timestamp"]
        verbose_name = "Prediction"
        verbose_name_plural = "Predictions"

    def __str__(self):
        return f"{self.gauge.name} - Prediction for {self.prediction_for_timestamp}"
