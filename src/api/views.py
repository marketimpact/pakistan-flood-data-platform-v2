from rest_framework import viewsets
from core.models import Gauge, Reading, Prediction
from .serializers import GaugeSerializer, ReadingSerializer, PredictionSerializer


class GaugeViewSet(viewsets.ReadOnlyModelViewSet):
    """
    A read-only API endpoint for viewing flood gauges.
    """

    queryset = Gauge.objects.all()
    serializer_class = GaugeSerializer


class ReadingViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Reading.objects.all()
    serializer_class = ReadingSerializer


class PredictionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Prediction.objects.all()
    serializer_class = PredictionSerializer
