# Phase 4: Dashboard & Data Collection Commands (TDD)

**Start State:** A working v1 API.
**End State:** A login-protected dashboard, an efficient CSV export, and management commands connected to the service layer.

---

- [ ] **Prompt:** "Create a new app named `dashboard` within the `src` directory."
- [ ] **Prompt:** "In `src/dashboard/tests/test_views.py`, write a test that makes a `GET` request to `/dashboard/`. Assert that the response is a 302 redirect to the login page. This test must fail (404)."
- [ ] **Prompt:** "In `src/dashboard/views.py`, create a `DashboardView` that inherits from `LoginRequiredMixin` and renders a template. Create a `dashboard.html` template. In `src/dashboard/urls.py`, define the URL for this view and include it in the main `urls.py`."
- [ ] **Prompt:** "Run the dashboard view test. It must now pass."
- [ ] **Prompt:** "In `src/dashboard/tests/test_views.py`, write a new test for the CSV export view at `/dashboard/export/readings/`. The test should assert that an unauthenticated request is redirected, and an authenticated request returns a response with a `Content-Type` of `text/csv`. This test must fail."
- [ ] **Prompt:** "In `src/dashboard/views.py`, create the `ExportReadingsCSVView`. It must use `StreamingHttpResponse` and `queryset.iterator()` to efficiently stream the CSV data."
- [ ] **Prompt:** "Run the export view tests. They must now pass."
- [ ] **Prompt:** "In `src/core/tests/test_commands.py`, write a test for the `collect_data` management command. Use `unittest.mock.patch` to mock the `DataCollectionService` and assert that its `collect_gauge_data` method is called. This test must fail."
- [ ] **Prompt:** "In `src/core/management/commands/collect_data.py`, create the `collect_data` command. It should be a simple wrapper that calls the `collect_gauge_data` method from the `DataCollectionService`."
- [ ] **Prompt:** "Run the management command test. It must now pass."
- [ ] **Prompt:** "Stage all new files and create a Git commit with the message: `feat: Build dashboard, CSV export, and management commands`."