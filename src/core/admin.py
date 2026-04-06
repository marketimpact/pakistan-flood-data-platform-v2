from django.contrib import admin
from django.core.management import call_command
from django.contrib import messages
from django.shortcuts import redirect
from django.urls import path, reverse
from django.http import HttpResponseRedirect
from django.template.response import TemplateResponse
from .models import Gauge, Reading, Prediction


@admin.register(Gauge)
class GaugeAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "gauge_id",
        "quality_verified",
        "has_model",
        "source",
        "status",
        "country_code",
    )
    list_filter = ("source", "status", "quality_verified", "has_model", "country_code")
    search_fields = ("name", "gauge_id", "location")
    actions = ['collect_forecast_data_action', 'update_readings_action']

    def get_queryset(self, request):
        return super().get_queryset(request).order_by("-quality_verified", "name")
    
    def collect_forecast_data_action(self, request, queryset):
        """Admin action to collect forecast data"""
        try:
            call_command('collect_forecast_data', days=7, batch_size=100)
            self.message_user(request, 'Successfully collected forecast data for 7 days!')
        except Exception as e:
            self.message_user(request, f'Error collecting forecast data: {str(e)}', level='ERROR')
    collect_forecast_data_action.short_description = "🔄 Collect forecast data (7 days)"
    
    def update_readings_action(self, request, queryset):
        """Admin action to update daily readings"""
        try:
            call_command('update_daily_readings')
            self.message_user(request, 'Successfully updated daily readings!')
        except Exception as e:
            self.message_user(request, f'Error updating readings: {str(e)}', level='ERROR')
    update_readings_action.short_description = "📈 Update daily readings"


@admin.register(Reading)
class ReadingAdmin(admin.ModelAdmin):
    list_display = ("gauge", "timestamp", "water_level", "flow_rate")
    list_filter = ("gauge__name",)
    search_fields = ("gauge__name", "gauge__gauge_id")
    date_hierarchy = "timestamp"


@admin.register(Prediction)
class PredictionAdmin(admin.ModelAdmin):
    list_display = ("gauge", "prediction_for_timestamp", "water_level")
    list_filter = ("gauge__name",)
    search_fields = ("gauge__name", "gauge__gauge_id")
    date_hierarchy = "prediction_for_timestamp"


