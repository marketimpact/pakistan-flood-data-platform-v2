import csv
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView
from django.http import StreamingHttpResponse, JsonResponse
from django.views import View
from django.contrib import messages
from django.shortcuts import redirect
from django.core.management import call_command
from django.utils import timezone
from datetime import timedelta
from django.db.models import Max, Avg, F, Q, Count
from django.core.paginator import Paginator
from core.models import Reading, Gauge, Prediction


class HomeView(TemplateView):
    """
    Home page view.
    """

    template_name = "dashboard/home.html"


class DashboardView(TemplateView):
    """
    Displays the main dashboard page.
    Now publicly accessible to show flood data.
    """

    template_name = "dashboard/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Basic statistics
        context["gauge_count"] = Gauge.objects.count()
        context["verified_gauge_count"] = Gauge.objects.filter(
            quality_verified=True
        ).count()
        context["reading_count"] = Reading.objects.count()
        context["prediction_count"] = Prediction.objects.count()
        
        # Calculate gauges with data
        gauges_with_readings = Gauge.objects.filter(readings__isnull=False).distinct().count()
        context["gauges_with_readings"] = gauges_with_readings
        context["gauges_without_readings"] = context["gauge_count"] - gauges_with_readings
        
        # Define Pakistani provinces
        PAKISTANI_PROVINCES = [
            'Punjab', 'Sindh', 'Balochistan', 'Khyber Pakhtunkhwa',
            'Gilgit-Baltistan', 'Azad Jammu and Kashmir', 
            'Islamabad Capital Territory'
        ]
        
        # Geographic statistics (Pakistan only)
        province_stats = Gauge.objects.filter(
            province__isnull=False,
            province__in=PAKISTANI_PROVINCES
        ).exclude(
            province=""
        ).values('province').annotate(
            count=Count('id')
        ).order_by('-count')
        
        context["province_stats"] = province_stats
        context["provinces_covered"] = province_stats.count()
        
        # District coverage (Pakistan only)
        district_count = Gauge.objects.filter(
            district__isnull=False,
            province__in=PAKISTANI_PROVINCES
        ).exclude(
            district=""
        ).values('district').distinct().count()
        context["districts_covered"] = district_count
        
        # Pakistan gauge count
        pakistan_gauge_count = Gauge.objects.filter(
            province__in=PAKISTANI_PROVINCES
        ).count()
        context["pakistan_gauge_count"] = pakistan_gauge_count

        # Get all gauges with pagination
        gauges_all = Gauge.objects.all().order_by("-updated_at")
        
        # Pagination
        page_number = self.request.GET.get('page', 1)
        paginator = Paginator(gauges_all, 50)  # Show 50 gauges per page
        page_obj = paginator.get_page(page_number)
        
        context["page_obj"] = page_obj
        context["total_pages"] = paginator.num_pages
        
        gauges_with_status = []
        gauges = page_obj.object_list

        # Define warning thresholds
        WARNING_LEVEL_THRESHOLD = 10.0  # meters - adjust based on actual data
        CRITICAL_LEVEL_THRESHOLD = 15.0  # meters - adjust based on actual data
        STALE_DATA_HOURS = 48  # Consider data stale if older than 48 hours

        now = timezone.now()
        stale_threshold = now - timedelta(hours=STALE_DATA_HOURS)

        # Statistics for warnings
        warning_count = 0
        critical_count = 0
        stale_count = 0
        no_data_count = 0

        for gauge in gauges:
            # Get latest reading for this gauge
            latest_reading = (
                Reading.objects.filter(gauge=gauge).order_by("-timestamp").first()
            )

            gauge_info = {
                "gauge": gauge,
                "latest_reading": latest_reading,
                "status": "active",
                "warning_level": None,
                "last_update": None,
                "is_stale": False,
                "time_since_update": None,
            }

            if latest_reading:
                gauge_info["last_update"] = latest_reading.timestamp

                # Calculate time since last update
                time_diff = now - latest_reading.timestamp
                hours_diff = int(time_diff.total_seconds() / 3600)

                if hours_diff < 1:
                    gauge_info["time_since_update"] = "Less than 1 hour ago"
                elif hours_diff < 24:
                    gauge_info["time_since_update"] = f"{hours_diff} hours ago"
                else:
                    days_diff = int(hours_diff / 24)
                    gauge_info["time_since_update"] = f"{days_diff} days ago"

                # Check if data is stale
                if latest_reading.timestamp < stale_threshold:
                    gauge_info["is_stale"] = True
                    gauge_info["status"] = "stale"
                    stale_count += 1

                # Check water level warnings
                if latest_reading.water_level >= CRITICAL_LEVEL_THRESHOLD:
                    gauge_info["warning_level"] = "critical"
                    gauge_info["status"] = "critical"
                    critical_count += 1
                elif latest_reading.water_level >= WARNING_LEVEL_THRESHOLD:
                    gauge_info["warning_level"] = "warning"
                    gauge_info["status"] = "warning"
                    warning_count += 1
                elif not gauge_info["is_stale"]:
                    gauge_info["warning_level"] = "normal"
            else:
                gauge_info["status"] = "no_data"
                gauge_info["time_since_update"] = "No data"
                no_data_count += 1

            gauges_with_status.append(gauge_info)

        # Add to context
        context["gauges_with_status"] = gauges_with_status
        context["warning_count"] = warning_count
        context["critical_count"] = critical_count
        context["stale_count"] = stale_count
        context["no_data_count"] = no_data_count
        context["total_alerts"] = (
            warning_count + critical_count + stale_count + no_data_count
        )

        # Recent readings for the activity feed (show last 20)
        context["recent_readings"] = Reading.objects.select_related("gauge").order_by(
            "-timestamp"
        )[:20]
        
        # Recent predictions for future flood forecasts
        context["recent_predictions"] = Prediction.objects.select_related("gauge").order_by(
            "-prediction_for_timestamp"
        )[:10]

        # Recent gauges for the activity feed (show last 20)
        context["recent_gauges"] = Gauge.objects.order_by("-created_at")[:20]
        
        # Latest data update time
        latest_reading = Reading.objects.order_by("-created_at").first()
        context["last_data_update"] = latest_reading.created_at if latest_reading else None

        return context


class Echo:
    """An object that implements just the write method of the file-like protocol."""

    def write(self, value):
        """Write the value by returning it, instead of storing in a buffer."""
        return value


def generate_readings_csv(readings):
    """A generator function to stream CSV data."""
    pseudo_buffer = Echo()
    writer = csv.writer(pseudo_buffer)

    # Write header
    yield writer.writerow(
        ["Gauge ID", "Gauge Name", "Timestamp", "Water Level (m)", "Flow Rate (m³/s)"]
    )

    # Write data rows
    for reading in readings.iterator():
        yield writer.writerow(
            [
                reading.gauge.gauge_id,
                reading.gauge.name,
                reading.timestamp.isoformat(),
                reading.water_level,
                reading.flow_rate,
            ]
        )


class ExportReadingsCSVView(View):
    """
    A view to stream a CSV export of all Reading data.
    Now publicly accessible.
    """

    def get(self, request, *args, **kwargs):
        readings = Reading.objects.select_related("gauge").all()
        response = StreamingHttpResponse(
            generate_readings_csv(readings), content_type="text/csv"
        )
        response["Content-Disposition"] = 'attachment; filename="readings_export.csv"'
        return response


class CollectDataView(LoginRequiredMixin, View):
    """
    View to trigger forecast data collection from Google Flood Hub.
    Restricted to admin users only.
    """

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_staff:
            messages.error(request, "Access denied. Admin privileges required.")
            return redirect("dashboard")
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        """Redirect GET requests to dashboard"""
        return redirect("dashboard")

    def post(self, request, *args, **kwargs):
        try:
            # Get the number of days and batch size from form
            days = request.POST.get("days", "7")
            batch_size = request.POST.get("batch_size", "100")
            
            try:
                days_int = int(days)
                batch_size_int = int(batch_size)
            except ValueError:
                days_int = 7
                batch_size_int = 100

            # Run the new forecast collection command
            call_command("collect_forecast_data", days=days_int, batch_size=batch_size_int)
            
            # Get updated counts
            total_gauges = Gauge.objects.count()
            total_readings = Reading.objects.count()
            total_predictions = Prediction.objects.count()
            
            messages.success(
                request,
                f"Successfully collected forecast data for {total_gauges} gauges! "
                f"Created/updated {total_readings} readings and {total_predictions} predictions "
                f"for the last {days_int} days.",
            )
        except Exception as e:
            messages.error(request, f"Error collecting forecast data: {str(e)}")

        return redirect("dashboard")


# ClearDataView has been removed for safety - we don't want to accidentally delete all data
# class ClearDataView(LoginRequiredMixin, View):
#     """
#     View to clear all gauge and reading data.
#     """
#     def get(self, request, *args, **kwargs):
#         """Redirect GET requests to dashboard"""
#         return redirect('dashboard')
#
#     def post(self, request, *args, **kwargs):
#         try:
#             # Get counts before deletion
#             gauge_count = Gauge.objects.count()
#             reading_count = Reading.objects.count()
#             prediction_count = Prediction.objects.count()
#
#             # Delete all data
#             Reading.objects.all().delete()
#             Prediction.objects.all().delete()
#             Gauge.objects.all().delete()
#
#             messages.success(
#                 request,
#                 f'Successfully cleared all data: {gauge_count} gauges, {reading_count} readings, {prediction_count} predictions'
#             )
#         except Exception as e:
#             messages.error(request, f'Error clearing data: {str(e)}')
#
#         return redirect('dashboard')


class UpdateReadingsView(LoginRequiredMixin, View):
    """
    View to trigger daily readings update using forecast data.
    Restricted to admin users only.
    """

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_staff:
            messages.error(request, "Access denied. Admin privileges required.")
            return redirect("dashboard")
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        """Redirect GET requests to dashboard"""
        return redirect("dashboard")

    def post(self, request, *args, **kwargs):
        force_update = request.POST.get("force_update", False)

        try:
            # Run the updated daily readings command (now uses forecast data)
            if force_update:
                call_command("update_daily_readings", force=True)
                messages.success(
                    request,
                    "Successfully updated readings for all gauges using latest forecast data (forced update)!",
                )
            else:
                call_command("update_daily_readings")
                messages.success(
                    request, "Successfully updated daily readings using latest forecast data!"
                )
        except Exception as e:
            messages.error(request, f"Error updating readings: {str(e)}")

        return redirect("dashboard")
