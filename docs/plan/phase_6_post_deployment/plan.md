# Phase 6: Post-Deployment Hardening & Observability

**Start State:** The application is deployed and running on Render.
**End State:** The application is enhanced with enterprise-grade monitoring, advanced testing, and documented operational procedures.

---

- [ ] **Prompt:** "Select an Application Performance Monitoring (APM) service (e.g., Sentry). Install its Python SDK and configure it in `src/config/settings/production.py` to capture errors and performance data."
- [ ] **Prompt:** "Create a new test file `src/core/tests/test_integration.py`. Write an integration test using `TransactionTestCase` that simulates a full data collection workflow: it calls the management command, which in turn calls a mocked service, which then writes to the test database. Assert that the entire transaction completes successfully."
- [ ] **Prompt:** "Install the `bandit` security scanner. Run `bandit -r src/` to scan the codebase for common security vulnerabilities and report the findings."
- [ ] **Prompt:** "In the project's `README.md`, add a 'Deployment' section. Document the process for rolling back to a previous deployment on Render by re-deploying a specific Git commit from the Render dashboard."
- [ ] **Prompt:** "Configure a production-grade email backend (e.g., SendGrid) in `src/config/settings/production.py`. This will be used for Django's built-in error reporting to admins."
- [ ] **Prompt:** "Stage all new files and create a Git commit with the message: `ops: Add APM integration and post-deployment hardening`."