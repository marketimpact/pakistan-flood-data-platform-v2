# Phase 2: Core Models & Service Layer (TDD)

**Start State:** A Django project with a custom User model and a `core` app.
**End State:** All core data models (`Gauge`, `Reading`, `Prediction`) are defined and tested. The data collection service layer is structured and has initial, tested functions.

---

- [ ] **Prompt:** "In `src/core/tests/test_models.py`, write a test `test_create_gauge` that attempts to create a `Gauge` model instance. The test should assert that the `id` is a UUID and that a `created_at` timestamp is automatically set. This test must fail."
- [ ] **Prompt:** "In `src/core/models.py`, define the `Gauge` model. It must have a `UUIDField` primary key, a `gauge_id` CharField with a database index, `latitude` and `longitude` FloatFields, and other fields as specified in the architecture. Use Django's `TextChoices` for the `source` field."
- [ ] **Prompt:** "Run the `core` app's model tests. They must now pass."
- [ ] **Prompt:** "Repeat the TDD cycle (write failing test, write model code, run passing test) for the `Reading` and `Prediction` models. Ensure foreign keys to `Gauge` are indexed."
- [ ] **Prompt:** "Create a new directory `src/core/services/`. Inside, create an empty `__init__.py` and a `data_collection.py` file."
- [ ] **Prompt:** "In `src/core/tests/test_services.py`, write a test class `DataCollectionServiceTests`. The first test, `test_update_gauges_from_api`, should mock a call to an external API and assert that the service function creates a new `Gauge` object in the database. This test must fail."
- [ ] **Prompt:** "In `src/core/services/data_collection.py`, create a function `update_gauges_from_api` that takes mock data and creates a `Gauge` instance from it. Write the minimal code required to make the test pass."
- [ ] **Prompt:** "Run the service tests. They must now pass."
- [ ] **Prompt:** "Run `makemigrations` and `migrate` for the `core` app."
- [ ] **Prompt:** "Stage all new files and create a Git commit with the message: `feat: Implement core data models and initial service layer`."