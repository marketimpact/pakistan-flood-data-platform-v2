.PHONY: help install test test-coverage test-fast test-integration clean lint format security-check pre-commit setup-dev

help:
	@echo "Available commands:"
	@echo "  make install          Install all dependencies"
	@echo "  make test            Run all tests"
	@echo "  make test-coverage   Run tests with coverage report"
	@echo "  make test-fast       Run fast tests only (no integration)"
	@echo "  make test-integration Run integration tests only"
	@echo "  make lint            Run linting checks"
	@echo "  make format          Format code with black and isort"
	@echo "  make security-check  Run security vulnerability scan"
	@echo "  make clean           Clean up generated files"
	@echo "  make setup-dev       Complete development setup"

install:
	pip install -r requirements.txt
	pip install -r requirements-dev.txt

test:
	cd src && pytest -v

test-coverage:
	cd src && pytest --cov=. --cov-report=html --cov-report=term --cov-fail-under=80

test-fast:
	cd src && pytest -v -m "not slow and not integration"

test-integration:
	cd src && pytest -v core/tests/test_integration_*

test-unit:
	cd src && pytest -v -k "not integration"

test-security:
	cd src && pytest -v core/tests/test_integration_security.py

test-performance:
	cd src && pytest -v core/tests/test_integration_performance.py

lint:
	cd src && flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
	cd src && flake8 . --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics
	cd src && isort . --check-only --diff
	cd src && black . --check

format:
	cd src && isort .
	cd src && black .

security-check:
	safety check --json
	cd src && bandit -r . -ll

clean:
	find . -type f -name '*.pyc' -delete
	find . -type d -name '__pycache__' -delete
	find . -type d -name '.pytest_cache' -exec rm -rf {} +
	find . -type d -name 'htmlcov' -exec rm -rf {} +
	find . -name '.coverage' -delete
	find . -name 'coverage.xml' -delete
	find . -name 'coverage.json' -delete

migrate:
	cd src && python manage.py migrate

makemigrations:
	cd src && python manage.py makemigrations

createsuperuser:
	cd src && python manage.py createsuperuser

runserver:
	cd src && python manage.py runserver

shell:
	cd src && python manage.py shell

collectstatic:
	cd src && python manage.py collectstatic --noinput

setup-dev: install
	pre-commit install
	cd src && python manage.py migrate
	cd src && python manage.py ensure_admin
	@echo "Development environment setup complete!"

# Docker commands (if using Docker)
docker-build:
	docker-compose build

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

docker-test:
	docker-compose run --rm web pytest

docker-shell:
	docker-compose run --rm web python manage.py shell

# Database commands
db-reset:
	cd src && python manage.py reset_db --noinput
	cd src && python manage.py migrate
	cd src && python manage.py ensure_admin

db-backup:
	cd src && python manage.py dbbackup

db-restore:
	cd src && python manage.py dbrestore

# Deployment commands
deploy-check:
	cd src && python manage.py check --deploy

# Performance commands
profile:
	cd src && python -m cProfile -o profile.stats manage.py runserver --noreload

benchmark:
	cd src && pytest core/tests/test_integration_performance.py --benchmark-only

# Documentation commands
docs-serve:
	mkdocs serve

docs-build:
	mkdocs build