from rest_framework import serializers
from core.models import Gauge, Reading, Prediction


class GaugeSerializer(serializers.ModelSerializer):
    """
    Serializer for the Gauge model.
    """

    class Meta:
        model = Gauge
        fields = [
            "id",
            "gauge_id",
            "name",
            "latitude",
            "longitude",
            "country_code",
            "status",
        ]


class ReadingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Reading
        fields = ["id", "gauge", "timestamp", "water_level", "flow_rate"]


class PredictionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Prediction
        fields = ["id", "gauge", "prediction_for_timestamp", "water_level"]
