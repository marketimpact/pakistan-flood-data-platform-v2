"""Test factories for creating test data."""

import factory
from factory.django import DjangoModelFactory
from core.models import Gauge, Reading, Prediction
from django.utils import timezone
import datetime
from django.contrib.auth import get_user_model


User = get_user_model()


class UserFactory(DjangoModelFactory):
    """Factory for creating test users."""

    class Meta:
        model = User

    username = factory.Sequence(lambda n: f"testuser_{n}")
    email = factory.LazyAttribute(lambda obj: f"{obj.username}@example.com")
    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    is_active = True
    is_staff = False
    is_superuser = False


class AdminUserFactory(UserFactory):
    """Factory for creating admin users."""

    is_staff = True
    is_superuser = True


class GaugeFactory(DjangoModelFactory):
    """Factory for creating test gauges."""

    class Meta:
        model = Gauge

    gauge_id = factory.Sequence(lambda n: f"gauge_{n:04d}")
    name = factory.Faker("company")
    latitude = factory.Faker("latitude")
    longitude = factory.Faker("longitude")
    country_code = "PK"
    source = Gauge.Source.GOOGLE_FLOOD_HUB
    status = Gauge.Status.ACTIVE
    location = factory.Faker("city")
    quality_verified = factory.Faker("boolean")
    has_model = factory.Faker("boolean")


class QualityVerifiedGaugeFactory(GaugeFactory):
    """Factory for creating quality-verified gauges."""

    quality_verified = True
    has_model = True


class ReadingFactory(DjangoModelFactory):
    """Factory for creating test readings."""

    class Meta:
        model = Reading

    gauge = factory.SubFactory(GaugeFactory)
    timestamp = factory.Faker("date_time_this_year", tzinfo=datetime.timezone.utc)
    water_level = factory.Faker("pyfloat", min_value=0, max_value=20, right_digits=2)
    flow_rate = factory.Faker("pyfloat", min_value=0, max_value=100, right_digits=2)


class PredictionFactory(DjangoModelFactory):
    """Factory for creating test predictions."""

    class Meta:
        model = Prediction

    gauge = factory.SubFactory(GaugeFactory)
    prediction_for_timestamp = factory.Faker(
        "future_datetime", tzinfo=datetime.timezone.utc
    )
    water_level = factory.Faker("pyfloat", min_value=0, max_value=25, right_digits=2)


class PakistanGaugeFactory(GaugeFactory):
    """Factory for creating Pakistani flood gauges with realistic data."""

    gauge_id = factory.Sequence(lambda n: f"hybas_{4120000000 + n}")
    name = factory.Faker(
        "random_element",
        elements=[
            "Indus River Station",
            "Chitral River Gauge",
            "Jhelum River Monitor",
            "Chenab River Station",
            "Ravi River Gauge",
            "Sutlej River Monitor",
        ],
    )
    latitude = factory.Faker("pyfloat", min_value=24.0, max_value=37.0, right_digits=6)
    longitude = factory.Faker("pyfloat", min_value=61.0, max_value=77.0, right_digits=6)
    location = factory.Faker(
        "random_element",
        elements=[
            "Punjab Province",
            "Sindh Province",
            "Khyber Pakhtunkhwa",
            "Balochistan Province",
            "Islamabad Capital Territory",
            "Azad Kashmir",
        ],
    )
    country_code = "PK"
