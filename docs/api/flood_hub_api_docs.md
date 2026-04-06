# Google Flood Hub API Documentation

## Overview

The Google Flood Forecasting API provides comprehensive flood monitoring and prediction data through a RESTful interface. This API enables developers to access real-time flood status information, gauge measurements, and predictive models to help communities prepare for and respond to flooding events.

**Base URL**: `https://floodforecasting.googleapis.com/v1/`

## Table of Contents

1. [Resources Overview](#resources-overview)
2. [FloodStatus API](#floodstatus-api)
3. [Gauges API](#gauges-api)
4. [GaugeModels API](#gaugemodels-api)
5. [SerializedPolygons API](#serializedpolygons-api)
6. [Common Data Types](#common-data-types)
7. [Error Handling](#error-handling)
8. [Best Practices](#best-practices)

## Resources Overview

The API provides four main resources:

1. **FloodStatus**: Real-time flood status information including severity levels and forecasts
2. **Gauges**: Metadata about water measurement gauges including location and identification
3. **GaugeModels**: Hydrological model metadata including thresholds and measurement units
4. **SerializedPolygons**: KML polygon data for geographical areas

## FloodStatus API

The FloodStatus resource provides real-time flood risk information for specific geographical areas.

### FloodStatus Object Structure

```json
{
  "gaugeId": "string",
  "issuedTime": "2025-07-18T12:00:00Z",
  "severity": "ABOVE_NORMAL",
  "forecastTrend": "RISE",
  "inundationMapSet": {
    // Detailed flood risk maps
  }
}
```

### Key Fields

- **gaugeId**: Unique identifier for the monitoring gauge
- **issuedTime**: Timestamp when the status was issued (ISO 8601 format)
- **severity**: Flood risk level
  - `EXTREME`
  - `SEVERE`
  - `ABOVE_NORMAL`
  - `NO_FLOODING`
  - `UNKNOWN`
- **forecastTrend**: Water level trend
  - `RISE`
  - `FALL`
  - `NO_CHANGE`
- **inundationMapSet**: Detailed flood risk maps with probability and depth information

### Endpoints

#### 1. queryLatestFloodStatusByGaugeIds

Get flood status for specific gauge IDs.

**HTTP Method**: GET  
**Endpoint**: `/floodStatus:queryLatestFloodStatusByGaugeIds`

**Query Parameters**:
- `gaugeIds[]` (required): List of gauge IDs (max 20,000)

**Request Example**:
```
GET https://floodforecasting.googleapis.com/v1/floodStatus:queryLatestFloodStatusByGaugeIds?gaugeIds[]=gauge123&gaugeIds[]=gauge456
```

**Response Structure**:
```json
{
  "floodStatuses": [
    {
      "gaugeId": "gauge123",
      "issuedTime": "2025-07-18T12:00:00Z",
      "severity": "ABOVE_NORMAL",
      "forecastTrend": "RISE"
    }
  ]
}
```

#### 2. searchLatestFloodStatusByArea

Search flood status by geographical region.

**HTTP Method**: POST  
**Endpoint**: `/floodStatus:searchLatestFloodStatusByArea`

**Request Body**:
```json
{
  "regionCode": "US",  // OR use "loop" for geographical loop
  "pageSize": 100,
  "pageToken": "string",
  "includeNonQualityVerified": false
}
```

**Parameters**:
- `regionCode`: Country code (e.g., 'US', 'PK')
- `loop`: Alternative to regionCode - geographical loop object
- `pageSize` (optional): Max 20,000 flood statuses
- `pageToken` (optional): For pagination
- `includeNonQualityVerified` (optional): Include unverified data (default: false)

**Response Structure**:
```json
{
  "floodStatuses": [
    {
      "gaugeId": "gauge123",
      "issuedTime": "2025-07-18T12:00:00Z",
      "severity": "NO_FLOODING",
      "forecastTrend": "NO_CHANGE"
    }
  ],
  "nextPageToken": "string"
}
```

## Gauges API

The Gauges resource provides metadata about water measurement gauges.

### Gauge Object Structure

```json
{
  "gaugeId": "unique_identifier",
  "location": {
    "latitude": 29.5729,
    "longitude": 65.7312
  },
  "siteName": "Example Gauge",
  "source": "GRDC",
  "river": "Indus River",
  "countryCode": "PK",
  "qualityVerified": true,
  "hasModel": true
}
```

### Key Fields

- **gaugeId**: Unique identifier for the gauge
- **location**: Geographic coordinates (LatLng object)
- **siteName**: Name of the gauge site (not unique)
- **source**: Organization responsible for gauge data
- **river**: River name (optional)
- **countryCode**: Two-letter country code
- **qualityVerified**: Indicates data reliability
- **hasModel**: Indicates if predictive modeling is available

### Endpoints

#### 1. get

Get metadata about a single gauge.

**HTTP Method**: GET  
**Endpoint**: `/gauges/{gaugeId}`

**Path Parameters**:
- `gaugeId`: The gauge identifier

**Request Example**:
```
GET https://floodforecasting.googleapis.com/v1/gauges/gauge123
```

**Response**: Returns a Gauge object

#### 2. batchGet

Retrieve metadata for multiple gauges.

**HTTP Method**: GET  
**Endpoint**: `/gauges:batchGet`

**Query Parameters**:
- `names[]` (required): List of gauge names in format `gauges/{gaugeId}` (max 100,000)

**Request Example**:
```
GET https://floodforecasting.googleapis.com/v1/gauges:batchGet?names[]=gauges/gauge123&names[]=gauges/gauge456
```

**Response Structure**:
```json
{
  "gauges": [
    {
      "gaugeId": "gauge123",
      "location": { "latitude": 29.5729, "longitude": 65.7312 },
      "siteName": "Example Gauge"
    }
  ]
}
```

#### 3. searchGaugesByArea

Find gauges in a specific geographic region.

**HTTP Method**: POST  
**Endpoint**: `/gauges:searchGaugesByArea`

**Request Body**:
```json
{
  "regionCode": "PK",  // OR use "loop"
  "pageSize": 100,
  "pageToken": "string",
  "includeNonQualityVerified": false,
  "includeGaugesWithoutHydroModel": false
}
```

**Parameters**:
- `regionCode` or `loop`: Search area specification
- `pageSize` (optional): Max 50,000 gauges
- `pageToken` (optional): For pagination
- `includeNonQualityVerified` (optional): Include unverified gauges
- `includeGaugesWithoutHydroModel` (optional): Include gauges without models

**Response Structure**:
```json
{
  "gauges": [
    {
      "gaugeId": "gauge123",
      "location": { "latitude": 29.5729, "longitude": 65.7312 }
    }
  ],
  "nextPageToken": "string"
}
```

**Note**: Results should not be cached for more than one day.

#### 4. queryGaugeForecasts

Retrieve forecast data for specific gauges.

**HTTP Method**: GET  
**Endpoint**: `/gauges:queryGaugeForecasts`

**Query Parameters**:
- `gaugeIds[]` (required): List of gauge IDs (max 500)
- `issuedTimeStart` (optional): Earliest forecast time (ISO 8601, min: 2023-10-01)
- `issuedTimeEnd` (optional): Latest forecast time (ISO 8601)

**Default Values**:
- Start time: One week ago
- End time: Current time

**Request Example**:
```
GET https://floodforecasting.googleapis.com/v1/gauges:queryGaugeForecasts?gaugeIds[]=gauge123&issuedTimeStart=2025-07-01T00:00:00Z
```

**Response Structure**:
```json
{
  "forecasts": {
    "gauge123": {
      "forecasts": [
        {
          "gaugeId": "gauge123",
          "issuedTime": "2025-07-17T10:34:00Z",
          "forecastRanges": [
            {
              "startTime": "2025-07-17T12:00:00Z",
              "endTime": "2025-07-17T13:00:00Z",
              "value": 125.5
            }
          ]
        }
      ]
    }
  }
}
```

## GaugeModels API

The GaugeModels resource provides hydrological model metadata.

### GaugeModel Object Structure

```json
{
  "gaugeId": "gauge123",
  "gaugeModelId": "model_v2",
  "thresholds": {
    "warningLevel": 100.0,
    "dangerLevel": 150.0,
    "extremeDangerLevel": 200.0
  },
  "gaugeValueUnit": "CUBIC_METERS_PER_SECOND",
  "qualityVerified": true
}
```

### Key Fields

- **gaugeId**: Unique identifier for the gauge
- **gaugeModelId**: Identifier for the current model version
- **thresholds**: Water level classifications
  - `warningLevel`
  - `dangerLevel`
  - `extremeDangerLevel`
- **gaugeValueUnit**: Measurement units
  - `METERS`
  - `CUBIC_METERS_PER_SECOND`
- **qualityVerified**: Indicates model reliability

### Endpoints

#### 1. get

Get hydrological model metadata for a single gauge.

**HTTP Method**: GET  
**Endpoint**: `/gaugeModels/{gaugeId}`

**Path Parameters**:
- `gaugeId`: The gauge identifier

**Request Example**:
```
GET https://floodforecasting.googleapis.com/v1/gaugeModels/gauge123
```

**Response**: Returns a GaugeModel object

#### 2. batchGet

Get model metadata for multiple gauges.

**HTTP Method**: GET  
**Endpoint**: `/gaugeModels:batchGet`

**Query Parameters**:
- `names[]` (required): List of model names in format `gaugeModels/{gaugeId}` (max 20,000)

**Request Example**:
```
GET https://floodforecasting.googleapis.com/v1/gaugeModels:batchGet?names[]=gaugeModels/gauge123&names[]=gaugeModels/gauge456
```

**Response Structure**:
```json
{
  "gaugeModels": [
    {
      "gaugeId": "gauge123",
      "gaugeModelId": "model_v2",
      "thresholds": {
        "warningLevel": 100.0
      }
    }
  ]
}
```

**Important Note**: Use caution when comparing old forecasts to new ones if they were produced by different models.

## SerializedPolygons API

The SerializedPolygons resource provides KML polygon data for geographical areas.

### SerializedPolygon Object Structure

```json
{
  "polygonId": "polygon_123",
  "kml": "<kml>...</kml>"
}
```

### Fields

- **polygonId**: Unique identifier for the polygon
- **kml**: KML string representation of the polygon

### Endpoints

#### get

Get a serialized polygon.

**HTTP Method**: GET  
**Endpoint**: `/serializedPolygons/{polygonId}`

**Path Parameters**:
- `polygonId`: The polygon identifier

**Request Example**:
```
GET https://floodforecasting.googleapis.com/v1/serializedPolygons/polygon_123
```

**Response**: Returns a SerializedPolygon object

**Note**: This endpoint is used to retrieve polygon data referenced in other API responses.

## Common Data Types

### LatLng Object
```json
{
  "latitude": 29.5729,
  "longitude": 65.7312
}
```

### Timestamp Format
All timestamps use ISO 8601 format: `YYYY-MM-DDTHH:MM:SSZ`

Example: `2025-07-18T12:00:00Z`

## Error Handling

The API uses standard HTTP status codes:

- **200 OK**: Request successful
- **400 Bad Request**: Invalid parameters or request format
- **404 Not Found**: Resource not found
- **429 Too Many Requests**: Rate limit exceeded
- **500 Internal Server Error**: Server error

### Common Error Scenarios

1. **Exceeding List Limits**: 
   - gaugeIds > 20,000 in floodStatus queries
   - names > 100,000 in gauge batch requests
   - Returns INVALID_REQUEST error

2. **Invalid Time Ranges**:
   - Start time before 2023-10-01 in forecast queries
   - Invalid ISO 8601 format

3. **Missing Required Parameters**:
   - Missing gaugeIds in queries
   - Missing regionCode or loop in area searches

## Best Practices

### 1. Batch Operations
- Use batch endpoints when querying multiple items
- Stay within documented limits to avoid errors

### 2. Caching
- Cache gauge metadata for up to 24 hours
- Do not cache flood status data for extended periods
- Forecast data can be cached until new forecasts are issued

### 3. Pagination
- Always check for `nextPageToken` in responses
- Use `pageSize` to control response size
- Default page sizes are optimized for performance

### 4. Error Handling
- Implement exponential backoff for rate limiting
- Validate parameters before making requests
- Handle missing or null fields gracefully

### 5. Performance Tips
- Use specific gauge IDs when possible instead of area searches
- Filter by quality verification when appropriate
- Request only the time ranges needed for forecasts

### 6. Data Quality
- Prefer `qualityVerified: true` data for critical applications
- Note model changes when comparing historical forecasts
- Consider `includeNonQualityVerified` carefully based on use case

## Usage Examples

### Example 1: Check Current Flood Status for Multiple Gauges

```python
import requests

gauge_ids = ['gauge123', 'gauge456', 'gauge789']
params = {'gaugeIds[]': gauge_ids}

response = requests.get(
    'https://floodforecasting.googleapis.com/v1/floodStatus:queryLatestFloodStatusByGaugeIds',
    params=params
)

flood_data = response.json()
for status in flood_data['floodStatuses']:
    print(f"Gauge {status['gaugeId']}: {status['severity']}")
```

### Example 2: Search for Gauges in Pakistan

```python
import requests

data = {
    'regionCode': 'PK',
    'pageSize': 100,
    'includeNonQualityVerified': False
}

response = requests.post(
    'https://floodforecasting.googleapis.com/v1/gauges:searchGaugesByArea',
    json=data
)

gauges = response.json()
for gauge in gauges['gauges']:
    print(f"Found gauge: {gauge['gaugeId']} at {gauge['siteName']}")
```

### Example 3: Get Forecast Data with Time Range

```python
import requests
from datetime import datetime, timedelta

# Get forecasts for the last 3 days
end_time = datetime.utcnow()
start_time = end_time - timedelta(days=3)

params = {
    'gaugeIds[]': ['gauge123'],
    'issuedTimeStart': start_time.isoformat() + 'Z',
    'issuedTimeEnd': end_time.isoformat() + 'Z'
}

response = requests.get(
    'https://floodforecasting.googleapis.com/v1/gauges:queryGaugeForecasts',
    params=params
)

forecasts = response.json()
```

## Additional Notes

1. **gRPC Transcoding**: The API uses gRPC Transcoding syntax, allowing flexible interaction patterns.

2. **Regional Availability**: Some features may have regional restrictions or availability.

3. **Data Sources**: Gauge data comes from various organizations (e.g., GRDC) as indicated in the `source` field.

4. **Model Updates**: Gauge models may be updated over time. Always check `gaugeModelId` when comparing historical data.

5. **Real-time Nature**: Flood status data is real-time and should be fetched frequently for critical applications.

---

*This documentation is based on the Google Flood Forecasting API v1. For the most up-to-date information, please refer to the official Google documentation.*