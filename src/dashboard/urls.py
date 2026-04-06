from django.urls import path
from .views import (
    DashboardView,
    ExportReadingsCSVView,
    CollectDataView,
    UpdateReadingsView,
)

urlpatterns = [
    path("", DashboardView.as_view(), name="dashboard"),
    path(
        "export/readings/", ExportReadingsCSVView.as_view(), name="export_readings_csv"
    ),
    path("collect-data/", CollectDataView.as_view(), name="collect_data"),
    path("update-readings/", UpdateReadingsView.as_view(), name="update_readings"),
]
