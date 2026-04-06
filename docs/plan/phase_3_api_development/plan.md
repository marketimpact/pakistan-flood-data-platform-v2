# Phase 3: API Development with DRF (TDD)

**Start State:** Core models and services are defined.
**End State:** A versioned, browsable, and secure API for all models, with documentation, throttling, and CORS configured.

---

- [ ] **Prompt:** "Create a new app named `api` within the `src` directory."
- [ ] **Prompt:** "In `src/config/settings/base.py`, add `rest_framework`, `drf_spectacular`, and `corsheaders` to `INSTALLED_APPS`. Configure the `REST_FRAMEWORK` dictionary with `DEFAULT_AUTHENTICATION_CLASSES` (for JWT), `DEFAULT_PERMISSION_CLASSES` (for `IsAuthenticated`), and `DEFAULT_THROTTLE_CLASSES` and `DEFAULT_THROTTLE_RATES`."
- [ ] **Prompt:** "In `src/api/tests/test_serializers.py`, write a test to serialize a `Gauge` model instance and assert the output contains the correct fields and data. This test must fail."
- [ ] **Prompt:** "In `src/api/serializers.py`, create a `GaugeSerializer` for the `Gauge` model."
- [ ] **Prompt:** "Run the serializer tests. They must now pass."
- [ ] **Prompt:** "In `src/api/tests/test_views.py`, write a test using `APIClient` to perform a `GET` request to `/api/v1/gauges/`. Assert that it returns a 401 Unauthorized status code. This test must fail (404)."
- [ ] **Prompt:** "In `src/api/views.py`, create a `GaugeViewSet` using `ReadOnlyModelViewSet`. In `src/api/urls.py`, create a router and register the viewset. In the main `src/config/urls.py`, include the `api.urls` under a `v1/` namespace and also include the `drf-spectacular` URLs for API documentation."
- [ ] **Prompt:** "Run the viewset test again. It must now pass with a 401 status code."
- [ ] **Prompt:** "Write a new test that creates a user, authenticates the `APIClient` for that user, and performs a `GET` request to `/api/v1/gauges/`. Assert a 200 OK status code and that the response data is a list."
- [ ] **Prompt:** "Repeat the TDD cycle (serializers and viewsets) for the `Reading` and `Prediction` models."
- [ ] **Prompt:** "Stage all new files and create a Git commit with the message: `feat: Implement v1 API with DRF for core models`."