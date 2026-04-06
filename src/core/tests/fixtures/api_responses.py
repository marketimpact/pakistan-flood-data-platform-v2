"""Sample API response fixtures for Google Flood Hub testing."""

# Sample gauge response from Google Flood Hub API
SAMPLE_GAUGE_RESPONSE = {
    "gaugeId": "hybas_4121489010",
    "siteName": "Chitral River Station",
    "location": {"latitude": 35.8462, "longitude": 71.7839},
    "river": "Chitral River",
    "qualityVerified": True,
    "hasModel": True,
    "source": "HYBAS",
}

# Sample threshold response from gaugeModels endpoint
SAMPLE_THRESHOLD_RESPONSE = {
    "thresholds": {
        "warningLevel": 10.0,
        "dangerLevel": 15.0,
        "extremeDangerLevel": 20.0,
    },
    "gaugeValueUnit": "CUBIC_METERS_PER_SECOND",
    "returnPeriods": {"2year": 8.5, "5year": 12.0, "20year": 18.0},
}

# Sample flood status response
SAMPLE_FLOOD_STATUS_RESPONSE = {
    "gaugeId": "hybas_4121489010",
    "currentValue": 7.5,
    "severity": "NORMAL",
    "timestamp": "2025-07-16T12:00:00Z",
    "trend": "RISING",
    "forecastedPeak": {"value": 9.0, "timestamp": "2025-07-17T06:00:00Z"},
}

# Additional Pakistani gauge samples
PAKISTANI_GAUGE_SAMPLES = [
    {
        "gaugeId": "hybas_4120570410",
        "siteName": "Indus River at Tarbela",
        "location": {"latitude": 34.0885, "longitude": 72.6986},
        "river": "Indus River",
        "qualityVerified": True,
        "hasModel": True,
        "source": "HYBAS",
    },
    {
        "gaugeId": "hybas_4120890123",
        "siteName": "Jhelum River Station",
        "location": {"latitude": 32.9328, "longitude": 73.7315},
        "river": "Jhelum River",
        "qualityVerified": False,
        "hasModel": True,
        "source": "HYBAS",
    },
    {
        "gaugeId": "hybas_4121234567",
        "siteName": "Chenab River Monitor",
        "location": {"latitude": 31.4180, "longitude": 73.0790},
        "river": "Chenab River",
        "qualityVerified": True,
        "hasModel": False,
        "source": "HYBAS",
    },
]

# Error response samples
ERROR_RESPONSES = {
    "not_found": {
        "error": {"code": 404, "message": "Gauge not found", "status": "NOT_FOUND"}
    },
    "rate_limited": {
        "error": {
            "code": 429,
            "message": "Rate limit exceeded",
            "status": "RESOURCE_EXHAUSTED",
            "details": [{"retryDelay": "60s"}],
        }
    },
    "server_error": {
        "error": {"code": 500, "message": "Internal server error", "status": "INTERNAL"}
    },
}

# Malformed response samples for edge case testing
MALFORMED_RESPONSES = {
    "missing_location": {
        "gaugeId": "hybas_4121111111",
        "siteName": "Incomplete Gauge"
        # Missing location field
    },
    "invalid_coordinates": {
        "gaugeId": "hybas_4122222222",
        "location": {"latitude": "not_a_number", "longitude": 70.0},
    },
    "empty_response": {},
    "null_values": {
        "gaugeId": "hybas_4123333333",
        "siteName": None,
        "location": None,
        "qualityVerified": None,
    },
}
