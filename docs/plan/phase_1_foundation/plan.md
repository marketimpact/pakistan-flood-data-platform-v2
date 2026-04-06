# Phase 1: Professional Project Setup (TDD)

**Start State:** An empty project directory (`flood-data-platform`) with only `docs`, `memory-bank`, `GEMINI.md`, and `CLAUDE.md` files.
**End State:** A fully initialized Django project with a professional file structure, a custom User model, environment-aware settings, and passing tests, all committed to a new Git repository.

---

- [ ] **Prompt:** "Initialize a new Git repository in the current directory."
- [ ] **Prompt:** "Create a `.gitignore` file suitable for a professional Django project. It should ignore environment files (`.env`), virtual environment directories (`venv/`), IDE folders (`.idea/`, `.vscode/`), byte-compiled files (`__pycache__/`, `*.pyc`), and media/static asset directories."
- [ ] **Prompt:** "Create a `requirements.txt` file and add the following core dependencies: `django`, `djangorestframework`, `psycopg2-binary`, `gunicorn`, `python-dotenv`, `python-json-logger`, `whitenoise`, `drf-spectacular`, `django-cors-headers`."
- [ ] **Prompt:** "Create a new Django project named `config` in the current directory. Then, create two apps named `core` and `users`."
- [ ] **Prompt:** "Create a `src` directory. Move the `config`, `core`, and `users` directories into the `src` directory. Move the `manage.py` file into the `src` directory as well."
- [ ] **Prompt:** "In `src/manage.py` and `src/config/wsgi.py`, update the necessary paths to reflect the new `src` directory structure."
- [ ] **Prompt:** "Create the `settings/` directory within `src/config`. Move `src/config/settings.py` to `src/config/settings/base.py`. Create empty `development.py` and `production.py` files in the new settings directory. Update `src/config/asgi.py` and `src/config/wsgi.py` to point to the new settings path."
- [ ] **Prompt:** "In `src/users/tests.py`, write a test class `UserTests` with a method `test_create_user` that attempts to create an instance of a custom `User` model. This test must fail because the model does not exist yet."
- [ ] **Prompt:** "In `src/users/models.py`, create a `User` model that inherits from `django.contrib.auth.models.AbstractUser`. Add a `id` field of type `UUIDField` as the primary key."
- [ ] **Prompt:** "In `src/config/settings/base.py`, set `AUTH_USER_MODEL = 'users.User'`."
- [ ] **Prompt:** "Run the test for the `users` app. It must now pass."
- [ ] **Prompt:** "Run the `makemigrations` and `migrate` commands to create the initial database schema."
- [ ] **Prompt:** "Stage all the new project files and create a Git commit with the message: `feat: Initialize Django project with professional structure and custom user model`."