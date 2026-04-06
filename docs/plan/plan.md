# Pakistan Flood Data Platform - Professional Architecture Plan (v4)

This document outlines a revised, production-grade plan for the Flood Data Platform, incorporating Django best practices for security, performance, and maintainability.

**Methodology:** The project will be built using a strict Test-Driven Development (TDD) approach, organized into features, and deployed with separate environments.

### 1. Core Architectural Changes

Based on the architectural review, the following patterns will be enforced:

1.  **Feature-Based App Structure:** We will organize by application feature, not by data models.
    *   `core`: For shared models, base functionality, and the service layer.
    *   `users`: For the custom User model and user-related logic.
    *   `api`: For the Django REST Framework (DRF) endpoints.
    *   `dashboard`: For the user-facing web pages and views.
2.  **Service Layer:** All business logic (e.g., interacting with Google APIs, data processing) will be isolated in a `services` directory, decoupled from views and models.
3.  **Environment-Specific Settings:** The `settings.py` file will be split into a `settings/` directory (`base.py`, `development.py`, `production.py`).
4.  **Custom User Model:** We will implement a custom `User` model extending `AbstractUser` from the start.
5.  **API-First with DRF:** The primary interface for data will be a versioned API built with Django REST Framework.

### 2. Database & Model Enhancements

*   **Primary Keys:** All models will use `UUIDField` as their primary key.
*   **Indexing:** `db_index=True` will be added to all foreign keys and frequently queried fields.
*   **Field Choices:** Fields with a limited set of options will use Django's `choices` option.
*   **Model Validation:** `clean()` methods will be used for complex validation.

### 3. Security & Production Readiness

*   **Production Settings:** `production.py` will enforce `DEBUG = False`, `SECURE_SSL_REDIRECT = True`, `SESSION_COOKIE_SECURE = True`, and `CSRF_COOKIE_SECURE = True`.
*   **Admin URL:** The default `/admin/` URL will be changed to a non-guessable path.
*   **Health Checks:** A dedicated `/health/` endpoint will be created for monitoring.
*   **Error Handling & Retries:** The data collection service will implement robust error logging and a retry mechanism for external API calls.
*   **Transactions:** Database writes will be wrapped in `transaction.atomic()` blocks.

### 4. Performance Optimizations

*   **Efficient Data Export:** CSV exports will use `queryset.iterator()` to stream data directly from the database.
*   **Pagination:** All API list endpoints will have pagination enforced.
*   **Caching (Future):** The architecture will be designed to easily accommodate Redis for caching in a future phase.

---
*This revised plan supersedes all previous versions and will be used as the blueprint for the phased implementation.*
