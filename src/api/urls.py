from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import GaugeViewSet, ReadingViewSet, PredictionViewSet

router = DefaultRouter()
router.register(r"gauges", GaugeViewSet, basename="gauge")
router.register(r"readings", ReadingViewSet, basename="reading")
router.register(r"predictions", PredictionViewSet, basename="prediction")

urlpatterns = [
    path("", include(router.urls)),
]
