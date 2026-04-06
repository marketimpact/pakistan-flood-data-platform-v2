# Phase 5: Admin, Deployment & Finalization

**Start State:** A fully featured and tested Django application.
**End State:** The application is deployed to Render and is publicly accessible and operational.

---

- [ ] **Prompt:** "In `src/users/admin.py` and `src/core/admin.py`, register all models (`User`, `Gauge`, `Reading`, `Prediction`) with the Django admin site. Customize the `list_display` for each to show relevant fields."
- [ ] **Prompt:** "In `src/config/urls.py`, change the path for the admin site from `/admin/` to a secret, non-guessable path (e.g., `/` followed by a randomly generated UUID)."
- [ ] **Prompt:** "In `src/config/settings/production.py`, add the additional security headers (`SECURE_CONTENT_TYPE_NOSNIFF`, `SECURE_HSTS_SECONDS`, etc.) and set `CONN_MAX_AGE` for database connection pooling."
- [ ] **Prompt:** "In `src/config/settings/production.py`, configure `WhiteNoiseMiddleware` to serve static files."
- [ ] **Prompt:** "Create a `render.yaml` file in the project root. Configure it for a web service and a cron job. The web service's `buildCommand` must include `pip install -r requirements.txt` and `python src/manage.py collectstatic --noinput`. The `startCommand` should be `gunicorn config.wsgi:application`. The cron job should run the `collect_data` command hourly."
- [ ] **Prompt:** "Create a new application on Render using the `render.yaml` file. Set the required environment variables (`DATABASE_URL`, `SECRET_KEY`, `GOOGLE_API_KEY`, `DJANGO_SETTINGS_MODULE='config.settings.production'`) in the Render dashboard."
- [ ] **Prompt:** "The deployment should trigger automatically. Monitor the deployment logs to ensure the build and migration steps complete successfully."
- [ ] **Prompt:** "Verify the deployment by accessing the public URL, the admin panel, and the API documentation. Manually trigger the cron job from the Render dashboard and verify that new data appears in the database."
- [ ] **Prompt:** "Stage the `render.yaml` file and create a Git commit with the message: `chore: Add Render deployment configuration`."