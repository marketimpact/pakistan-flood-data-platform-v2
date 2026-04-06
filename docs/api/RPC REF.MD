Home
Products
Flood Forecasting API
RPC Reference
Was this helpful?

Flood Forecasting API

bookmark_border
floodforecasting.googleapis.com API.

Service: floodforecasting.googleapis.com
The Service name floodforecasting.googleapis.com is needed to create RPC client stubs.

google.research.floodforecasting.v1.FloodsApi
Methods
BatchGetGaugeModels	Get the current hydrological model metadata for multiple gauges.
BatchGetGauges	Get metadata about multiple gauges.
GetGauge	Get metadata about a gauge.
GetGaugeModel	Get the current hydrological model metadata for a given gauge.
GetSerializedPolygon	Get a serialized polygon.
QueryGaugeForecasts	Query gauge forecasts.
QueryLatestFloodStatusByGaugeIds	Query latest flood status by gauge ids.
SearchGaugesByArea	Search for gauges by geographical area.
SearchLatestFloodStatusByArea	Search latest flood status by geographical area.
Home
Products
Flood Forecasting API
RPC Reference
Was this helpful?

Package google.research.floodforecasting.v1

bookmark_border
Index
FloodsApi (interface)
BatchGetGaugeModelsRequest (message)
BatchGetGaugeModelsResponse (message)
BatchGetGaugesRequest (message)
BatchGetGaugesResponse (message)
FloodStatus (message)
FloodStatus.ForecastChange (message)
FloodStatus.ForecastChange.ValueChange (message)
FloodStatus.ForecastTrend (enum)
FloodStatus.InundationMap (message)
FloodStatus.InundationMap.InundationLevel (enum)
FloodStatus.InundationMapSet (message)
FloodStatus.InundationMapType (enum)
FloodStatus.MapInferenceType (enum)
FloodStatus.Severity (enum)
Forecast (message)
ForecastSet (message)
ForecastTimedValue (message)
Gauge (message)
GaugeModel (message)
GaugeModel.GaugeValueUnit (enum)
GetGaugeModelRequest (message)
GetGaugeRequest (message)
GetSerializedPolygonRequest (message)
Loop (message)
QueryGaugeForecastsRequest (message)
QueryGaugeForecastsResponse (message)
QueryLatestFloodStatusByGaugeIdsRequest (message)
QueryLatestFloodStatusByGaugeIdsResponse (message)
SearchGaugesByAreaRequest (message)
SearchGaugesByAreaResponse (message)
SearchLatestFloodStatusByAreaRequest (message)
SearchLatestFloodStatusByAreaResponse (message)
SerializedPolygon (message)
Thresholds (message)
TimeRange (message)
FloodsApi
An external API service for Flood Forecasting.

BatchGetGaugeModels
rpc BatchGetGaugeModels(BatchGetGaugeModelsRequest) returns (BatchGetGaugeModelsResponse)

Get the current hydrological model metadata for multiple gauges.

BatchGetGauges
rpc BatchGetGauges(BatchGetGaugesRequest) returns (BatchGetGaugesResponse)

Get metadata about multiple gauges.

GetGauge
rpc GetGauge(GetGaugeRequest) returns (Gauge)

Get metadata about a gauge.

GetGaugeModel
rpc GetGaugeModel(GetGaugeModelRequest) returns (GaugeModel)

Get the current hydrological model metadata for a given gauge.

GetSerializedPolygon
rpc GetSerializedPolygon(GetSerializedPolygonRequest) returns (SerializedPolygon)

Get a serialized polygon. IDs for these will appear in other API Responses, and you'll be able to use these IDs here. For example, see InundationMap in FloodStatus.

QueryGaugeForecasts
rpc QueryGaugeForecasts(QueryGaugeForecastsRequest) returns (QueryGaugeForecastsResponse)

Query gauge forecasts.

QueryLatestFloodStatusByGaugeIds
rpc QueryLatestFloodStatusByGaugeIds(QueryLatestFloodStatusByGaugeIdsRequest) returns (QueryLatestFloodStatusByGaugeIdsResponse)

Query latest flood status by gauge ids.

SearchGaugesByArea
rpc SearchGaugesByArea(SearchGaugesByAreaRequest) returns (SearchGaugesByAreaResponse)

Search for gauges by geographical area.

Note: Gauges are occasionally added or removed, so the result of this API should not be cached or stored for long periods of time. Consider no more than a day to be relatively safe.

SearchLatestFloodStatusByArea
rpc SearchLatestFloodStatusByArea(SearchLatestFloodStatusByAreaRequest) returns (SearchLatestFloodStatusByAreaResponse)

Search latest flood status by geographical area. Note: Returns flood statuses whose gauge is within the given area, as opposed to e.g., affected area intersecting with the given area. This is subject to change in the future.

BatchGetGaugeModelsRequest
The request of BatchGetGaugeModels.

Fields
names[]	
string

Required. The gauge model names to retrieve. Name format: gaugeModels/{gauge_id}. The supported list size is limited to 20,000. If a list larger than 20,000 is provided it may fail, and soon we will also enforce the limit by returning an INVALID_REQUEST error.

BatchGetGaugeModelsResponse
The response of BatchGetGaugeModels.

Fields
gauge_models[]	
GaugeModel

The requested gauge models.

BatchGetGaugesRequest
The request of BatchGetGauges.

Fields
names[]	
string

Required. The gauge names to retrieve. Name format: gauges/{gauge_id}. The supported list size is limited to 100,000. If a list larger than 100,000 is provided it may fail, and soon we will also enforce the limit by returning an INVALID_REQUEST error.

BatchGetGaugesResponse
The response of BatchGetGauges.

Fields
gauges[]	
Gauge

The requested gauges.

FloodStatus
A Flood Status issued by the system. Represents the flooding status forecasted by the system for an area, with attributes such as severity, the forecast change, inundation maps and others. See below for more details.

Fields
gauge_id	
string

The id of the gauge this status was issued for.

quality_verified	
bool

True if the gauge this flood status was issued for does not have a model, or if it has a model and the model is quality-verified. Please use with caution when this value is set to false.

gauge_location	
LatLng

The location of the gauge this status was issued for.

issued_time	
string

The time this status was issued as string (ISO 8601), e.g., "2023-06-17T10:34:00Z".

forecast_time_range	
TimeRange

The time range for which the forecast is predicting.

forecast_change	
ForecastChange

The forecast value change from the last known state to the forecast. Currently only available for Water Level models.

forecast_trend	
ForecastTrend

The trend of the forecast.

map_inference_type	
MapInferenceType

The type of inference this map was created by.

severity	
Severity

The severity of the status.

inundation_map_set	
InundationMapSet

The inferred inundation map set.

source	
string

The organization responsible for the data of this gauge, e.g., GRDC, CWC, etc.

serialized_notification_polygon_id	
string

An ID of the serialized notification polygon, which represents the geographic area Google uses to determine when to alert its users. Use GetSerializedPolygon to get the serialized polygon itself.

ForecastChange
The forecasted value change from the last known state to the forecast. Currently only available for Water Level models.

Fields
value_change	
ValueChange

The forecasted change in values.

reference_time_range	
TimeRange

Time range of the last known state, from which we predict the value change from. For example, we may have a reference time range set to yesterday, and a value change of 25-30cm. This means the water level rise of 25-30cm is compared to its value yesterday, not from its value now.

ValueChange
The forecasted change in values - an upper and lower bound.

Fields
lower_bound	
double

The lower bound of the forecast change in meters. If the change is between 20 and 30, this value would be 20. If the change is between -30 and -20, this value would be -30.

upper_bound	
double

The upper bound of the forecast change in meters. If the change is between 20 and 30, this value would be 30. If the change is between -30 and -20, this value would be -20.

ForecastTrend
An enum which represents the trend of the forecast.

Enums
FORECAST_TREND_UNSPECIFIED	Default value. This value is unused.
RISE	This indicates a rise in the forecasted value.
FALL	This indicates a fall in the forecasted value.
NO_CHANGE	This indicates no change in the forecasted value.
InundationMap
One inundation map.

Fields
level	
InundationLevel

The level of the inundation map - See documentation based on the InundationMapType.

serialized_polygon_id	
string

An ID of the serialized polygon representing this inundation risk map. Use GetSerializedPolygon to get the serialized polygon itself.

InundationLevel
An enum which represents inundation levels.

Enums
INUNDATION_LEVEL_UNSPECIFIED	Default value. This value is unused.
HIGH	See documentation based on the InundationMapType.
MEDIUM	See documentation based on the InundationMapType.
LOW	See documentation based on the InundationMapType.
InundationMapSet
A set of inundation maps.

Fields
inundation_maps[]	
InundationMap

The inundation maps, one for each inundation level.

inundation_maps_time_range	
TimeRange

The time range of the state to which the inundation maps refer.

inundation_map_type	
InundationMapType

The type of the inundation map.

InundationMapType
An enum which represents the type of the inundation map.

Enums
INUNDATION_MAP_TYPE_UNSPECIFIED	Default value. This value is unused.
PROBABILITY	A map of type probability. The InundationLevel represents the map probability - high/medium/low probability of flooding. The high probability polygon is contained within the medium probability polygon and the medium probability polygon is contained within the low probability polygon.
DEPTH	A map of type depth. The InundationLevel represents the map depth - high/medium/low depth per location. The high depth polygon is contained within the medium depth polygon and the medium depth polygon is contained within the low depth polygon.
MapInferenceType
An enum which represents types of map inferences.

Enums
MAP_INFERENCE_TYPE_UNSPECIFIED	Default value. This value is unused.
MODEL	This indicates that this inference was created using a model.
IMAGE_CLASSIFICATION	This indicates that this inference was created using an image classification.
Severity
An enum which represents the severity of the status.

Enums
SEVERITY_UNSPECIFIED	Default value. This value is unused.
EXTREME	This indicates a forecasted extreme status.
SEVERE	This indicates a forecasted severe status.
ABOVE_NORMAL	This indicates a forecasted above normal status.
NO_FLOODING	This indicates a forecast of no flooding.
UNKNOWN	This indicates that we don't have enough information to determine the severity.
Forecast
A single gauge's forecast for several lead times. For example, a forecast could have issue time of 5pm, and include forecasts for 6pm, 7pm, 8pm, etc.

Note: Some of the forecast ranges can potentially be earlier than the issued time. This can happen due to e.g., lags in input data for the model. With the above example, it could be that the issue time is 5pm, and the forecast ranges are for 4pm, 5pm, 6pm, etc.

Note: Ranges vary in length, and in distance between them. Some examples of possible ranges are:

[5pm - 5pm], [6pm - 6pm], [7pm - 7pm]

[Mar 1 12am - Mar 2 12am], [Mar 2 12am - Mar 3 12am], [Mar 3 12am - Mar 4 12am]

Fields
forecast_ranges[]	
ForecastTimedValue

A forecast consists of several "forecast ranges", which are different forecast values pertaining to different time ranges. When the start and end of a range are equal, it means it's a time instant.

gauge_id	
string

The ID of the gauge this forecast is for.

issued_time	
string

The issued time of the forecast (ISO 8601), e.g. "2023-06-17T10:34:00Z". The issued time is the time the forecast was generated.

ForecastSet
A set of forecasts for a gauge.

Fields
forecasts[]	
Forecast

The forecasts.

ForecastTimedValue
A forecast value pertaining to a time range. Its units are defined by the GaugeModel it is associated with. If the start and end are equal, it means it's a time instant.

Fields
value	
double

The value of the forecast.

forecast_start_time	
string

The start of the interval.

forecast_end_time	
string

The end of the interval.

Gauge
Metadata of a gauge.

Fields
location	
LatLng

The physical location of the gauge.

site_name	
string

The name of the site at which this gauge is located, in English. This is not a unique identifier; there may be several gauges in nearby locations with the same site name. Not always present.

source	
string

The organization responsible for the data of this gauge, e.g. GRDC, CWC, etc.

river	
string

The gauge's river name in English. Not always present.

country_code	
string

The country code of the gauge's country (ISO 3166 Alpha-2).

gauge_id	
string

The ID of the gauge.

quality_verified	
bool

This field is true if the gauge does not have a model, or if it has a model and the model is quality-verified. Please use with caution when this value is set to false.

has_model	
bool

This field is true if the gauge has a model. If the gauge has a model, it's possible to get this gauges's GaugeModel using GetGaugeModel or BatchGetGaugeModels. And also getting its forecasts using QueryGaugeForecasts.

GaugeModel
Metadata of a gauge's model.

Fields
gauge_id	
string

The ID of the gauge.

gauge_model_id	
string

The ID of the gauge's model. From time to time, the model for a gauge may change, and in that case we'll assign a new ID and new thresholds to the new model. Please use caution when comparing old forecasts to new ones if they were produced by different models.

thresholds	
Thresholds

The thresholds of the gauge.

gauge_value_unit	
GaugeValueUnit

The value unit of the gauge's model.

quality_verified	
bool

Whether this model is quality verified. Please use with caution when this value is set to false.

GaugeValueUnit
Possible gauge value units.

Enums
GAUGE_VALUE_UNIT_UNSPECIFIED	Default value. This value is unused.
METERS	Meters.
CUBIC_METERS_PER_SECOND	Cubic meters per second.
GetGaugeModelRequest
The request of GetGaugeModel.

Fields
name	
string

Required. The gauge model name to retrieve. Name format: gaugeModels/{gauge_id}.

GetGaugeRequest
The request of GetGauge.

Fields
name	
string

Required. The name of the gauge to retrieve. Name format: gauges/{gauge_id}.

GetSerializedPolygonRequest
The request of GetSerializedPolygon.

Fields
name	
string

Required. The name of the serialized polygon to retrieve. Name format: serializedPolygons/{polygon_id}

Loop
A loop on the map. Represents a simple spherical polygon. It consists of a single chain of vertices where the first vertex is implicitly connected to the last.

Fields
vertices[]	
LatLng

Required. The vertices of the loop.

QueryGaugeForecastsRequest
The request of QueryGaugeForecasts.

Fields
gauge_ids[]	
string

Required. A list of gauge ids. The supported list size is limited to 500. If a list larger than 500 is provided it may fail, and soon we will also enforce the limit by returning an INVALID_REQUEST error.

issued_time_start	
string

Optional. The earliest forecast issued time as string (ISO 8601), e.g. "2023-06-17T10:34:00Z" or a date string e.g. "2023-10-13". Start time cannot be earlier than "2023-10-01". Default is one week ago.

issued_time_end	
string

Optional. The latest forecast issued time as string (ISO 8601), e.g. "2023-06-17T10:34:00Z" or a date string e.g. "2023-10-13". Default is now.

QueryGaugeForecastsResponse
The response of QueryGaugeForecasts.

Fields
forecasts	
map<string, ForecastSet>

A map from gauge id to forecast set.

QueryLatestFloodStatusByGaugeIdsRequest
The request of QueryLatestFloodStatusByGaugeIds.

Fields
gauge_ids[]	
string

Required. A list of gauge ids. The supported list size is limited to 20,000. If a list larger than 20,000 is provided it may fail, and soon we will also enforce the limit by returning an INVALID_REQUEST error.

QueryLatestFloodStatusByGaugeIdsResponse
The response of QueryLatestFloodStatusByGaugeIds.

Fields
flood_statuses[]	
FloodStatus

The latest flood statuses for the requested gauges.

SearchGaugesByAreaRequest
The request of SearchGaugesByArea.

Fields
page_size	
int32

Optional. The maximum number of gauges to return. The service may return fewer than this value. If unspecified, at most 50,000 gauges will be returned. The maximum value is 50,000; values above 50,000 will be coerced to 50,000. The maximum value is currently not enforced by the API, but will be in the future.

page_token	
string

Optional. A page token, received from a previous SearchGauges call. Provide this to retrieve the subsequent page. When paginating, all other parameters provided to SearchGauges must match the call that provided the page token.

Union field search_by.

search_by can be only one of the following:

region_code	
string

Search for all gauges within a region by region code. Use https://cldr.unicode.org/ (list https://www.iana.org/assignments/language-subtag-registry/language-subtag-registry).

loop	
Loop

Search for all gauges within a loop (a simple spherical polygon, see Loop).

include_non_quality_verified	
bool

Optional. Include in the result gauges that aren't quality verified. Please use with caution. Default is false.

include_gauges_without_hydro_model	
bool

Optional. Include in the result gauges that don't have a Google in-house hydro model. Default is false.

SearchGaugesByAreaResponse
The response of SearchGaugesByArea.

Fields
gauges[]	
Gauge

Gauges found in the requested area.

next_page_token	
string

Optional. A token that can be sent as page_token to retrieve the next page. If this field is omitted, there are no subsequent pages.

SearchLatestFloodStatusByAreaRequest
The request of SearchLatestFloodStatusByArea.

Fields
page_token	
string

Optional. A page token, received from a previous SearchLatestFloodStatusByArea call. Provide this to retrieve the subsequent page. When paginating, all other parameters provided to SearchLatestFloodStatusByArea must match the call that provided the page token.

page_size	
int32

Optional. The maximum number of flood statuses to return. The service may return fewer than this value. If unspecified, at most 20,000 flood statuses will be returned. The maximum value is 20,000; values above 20,000 will be coerced to 20,000. The maximum value is currently not enforced by the API, but will be in the future.

Union field area_type.

area_type can be only one of the following:

region_code	
string

The region by which to query flood statuses. Using CLDR, e.g., 'US'.

loop	
Loop

The loop by which to query flood statuses.

include_non_quality_verified	
bool

Optional. Include in the result gauges that aren't quality verified. Please use with caution. Default is false.

SearchLatestFloodStatusByAreaResponse
The response of SearchLatestFloodStatusByArea.

Fields
flood_statuses[]	
FloodStatus

The latest flood statuses in the requested area. Currently, this is determined by the location of the gauges, this is subject to change in the future.

next_page_token	
string

Optional. A token that can be sent as page_token to retrieve the next page. If this field is omitted, there are no subsequent pages.

SerializedPolygon
A serialized polygon.

Fields
polygon_id	
string

The id of the polygon.

kml	
string

The KML string representation of the polygon.

Thresholds
Thresholds of a gauge's model.

Fields
warning_level	
double

Warning level.

danger_level	
double

Danger level.

extreme_danger_level	
double

Extreme danger level. Not always present.

TimeRange
A time range.

Fields
start	
string

The start of the time range. Represented as ISO 8601, e.g., "2023-06-17T10:34:00Z".

end	
string

The end of the time range. Represented as ISO 8601, e.g., "2023-06-17T10:34:00Z".

Home
Products
Flood Forecasting API
RPC Reference
Was this helpful?

Package google.type

bookmark_border
Index
LatLng (message)
LatLng
An object that represents a latitude/longitude pair. This is expressed as a pair of doubles to represent degrees latitude and degrees longitude. Unless specified otherwise, this object must conform to the WGS84 standard. Values must be within normalized ranges.

Fields
latitude	
double

The latitude in degrees. It must be in the range [-90.0, +90.0].

longitude	
double

The longitude in degrees. It must be in the range [-180.0, +180.0].

Was this helpful?

