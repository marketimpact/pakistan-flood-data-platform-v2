# Pakistan Flood Data Platform - Testing Guide

## 📚 Table of Contents
1. [Overview](#overview)
2. [Test Architecture](#test-architecture)
3. [Running Tests](#running-tests)
4. [Writing Tests](#writing-tests)
5. [Test Categories](#test-categories)
6. [Best Practices](#best-practices)
7. [CI/CD Integration](#cicd-integration)
8. [Troubleshooting](#troubleshooting)

## Overview

The Pakistan Flood Data Platform uses a comprehensive testing framework to ensure reliability, security, and performance. Our testing approach follows Test-Driven Development (TDD) principles with a target of 90%+ code coverage.

### Key Metrics
- **Total Test Files**: 40+
- **Total Test Methods**: 600+
- **Code Coverage**: 90%+
- **Test Execution Time**: < 3 minutes

## Test Architecture

### Directory Structure
```
src/
├── core/
│   └── tests/
│       ├── __init__.py
│       ├── base.py                    # Base test classes
│       ├── factories.py               # Test data factories
│       ├── fixtures/                  # Mock data
│       │   └── api_responses.py
│       ├── helpers.py                 # Test utilities
│       ├── test_api_integration.py    # API tests
│       ├── test_models_*.py          # Model tests
│       ├── test_*_command_*.py       # Command tests
│       └── test_integration_*.py     # Integration tests
├── dashboard/
│   └── tests/
│       ├── test_views_*.py           # View tests
│       └── test_export*.py           # Export tests
├── api/
│   └── tests/
│       ├── test_api_authentication.py
│       ├── test_*_api.py             # Endpoint tests
│       └── test_serializers.py
└── users/
    └── tests/
        └── test_*.py                  # User/auth tests
```

### Test Dependencies
```python
# requirements-dev.txt
pytest==7.4.0
pytest-django==4.5.2
pytest-cov==4.1.0
factory-boy==3.3.0
faker==19.2.0
freezegun==1.2.2
responses==0.23.3
```

## Running Tests

### Basic Commands
```bash
# Install test dependencies
pip install -r requirements-dev.txt

# Run all tests
cd src && pytest

# Run with coverage
pytest --cov=. --cov-report=html

# Run specific test file
pytest core/tests/test_models_comprehensive.py

# Run specific test class
pytest core/tests/test_models_comprehensive.py::TestGaugeModel

# Run specific test method
pytest core/tests/test_models_comprehensive.py::TestGaugeModel::test_gauge_creation
```

### Advanced Options
```bash
# Verbose output
pytest -v

# Stop on first failure
pytest -x

# Run only marked tests
pytest -m "slow"

# Run in parallel
pytest -n 4

# Generate coverage report
pytest --cov=. --cov-report=html --cov-report=term
```

### Test Categories
```bash
# Unit tests only
pytest -k "not integration"

# Integration tests only
pytest core/tests/test_integration_*

# Performance tests
pytest core/tests/test_integration_performance.py

# Security tests
pytest core/tests/test_integration_security.py
```

## Writing Tests

### Basic Test Structure
```python
from django.test import TestCase
from core.models import Gauge
from core.tests.factories import GaugeFactory

class TestGaugeModel(TestCase):
    """Test Gauge model functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.gauge = GaugeFactory()
    
    def test_gauge_creation(self):
        """Test gauge can be created."""
        self.assertEqual(self.gauge.country_code, 'PK')
        self.assertTrue(self.gauge.is_active)
    
    def tearDown(self):
        """Clean up after tests."""
        # Optional cleanup
        pass
```

### Using Factories
```python
# Creating test data with factories
gauge = GaugeFactory()
reading = ReadingFactory(gauge=gauge, water_level=5.0)
user = UserFactory(is_staff=True)

# Creating multiple instances
gauges = GaugeFactory.create_batch(10)

# Customizing factory data
gauge = GaugeFactory(
    gauge_id='CUSTOM001',
    name='Custom Gauge',
    latitude=31.5204
)
```

### Mocking External APIs
```python
from unittest.mock import patch, Mock
from core.tests.fixtures.api_responses import SAMPLE_GAUGE_RESPONSE

@patch('core.services.requests.get')
def test_api_call(self, mock_get):
    """Test API integration."""
    # Mock the response
    mock_get.return_value = Mock(
        status_code=200,
        json=Mock(return_value=SAMPLE_GAUGE_RESPONSE)
    )
    
    # Call the service
    service = GoogleFloodHubService()
    data = service.fetch_gauges()
    
    # Verify
    self.assertEqual(len(data), 1)
    mock_get.assert_called_once()
```

### Testing Views
```python
from django.test import TestCase, Client
from django.urls import reverse

class TestDashboardView(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
    
    def test_dashboard_requires_login(self):
        """Test dashboard requires authentication."""
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 302)
    
    def test_dashboard_with_login(self):
        """Test dashboard with authenticated user."""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)
```

## Test Categories

### 1. Unit Tests
- Model validation
- Service methods
- Utility functions
- Serializers

### 2. Integration Tests
- Data flow testing
- API integration
- Database transactions
- Multi-component workflows

### 3. Performance Tests
- Load testing
- Query optimization
- Memory usage
- Concurrent access

### 4. Security Tests
- Authentication flows
- Authorization checks
- Input validation
- XSS/CSRF protection

### 5. Error Handling Tests
- Network failures
- Invalid data
- Database errors
- API timeouts

## Best Practices

### 1. Test Isolation
```python
# Use TransactionTestCase for tests that need clean database
from django.test import TransactionTestCase

class TestDataIntegrity(TransactionTestCase):
    def test_transaction_rollback(self):
        # Test transaction behavior
        pass
```

### 2. Descriptive Names
```python
# Good
def test_gauge_creation_with_valid_coordinates(self):
def test_api_returns_404_for_nonexistent_gauge(self):

# Bad
def test_1(self):
def test_gauge(self):
```

### 3. Arrange-Act-Assert Pattern
```python
def test_reading_creation(self):
    # Arrange
    gauge = GaugeFactory()
    
    # Act
    reading = ReadingFactory(gauge=gauge, water_level=5.0)
    
    # Assert
    self.assertEqual(reading.gauge, gauge)
    self.assertEqual(reading.water_level, 5.0)
```

### 4. Use Fixtures Appropriately
```python
@pytest.fixture
def authenticated_client(client, user):
    """Provide authenticated client."""
    client.force_login(user)
    return client

def test_with_auth(authenticated_client):
    response = authenticated_client.get('/dashboard/')
    assert response.status_code == 200
```

### 5. Mock External Dependencies
```python
# Always mock external services
@patch('core.services.requests.get')
def test_external_api(self, mock_get):
    mock_get.return_value = Mock(status_code=200)
    # Test without making real API calls
```

## CI/CD Integration

### GitHub Actions Workflow
The project uses GitHub Actions for continuous integration:

```yaml
# .github/workflows/tests.yml
- Runs on every push and pull request
- Tests against Python 3.11
- Uses PostgreSQL for database tests
- Generates coverage reports
- Runs security checks
```

### Pre-commit Hooks
Install pre-commit hooks for local testing:

```bash
# Install pre-commit
pip install pre-commit

# Install the git hook scripts
pre-commit install

# Run against all files
pre-commit run --all-files
```

### Coverage Requirements
- Minimum overall coverage: 80%
- Critical paths coverage: 95%
- New code coverage: 90%

## Troubleshooting

### Common Issues

#### 1. Database Connection Errors
```bash
# Error: psycopg2.OperationalError: FATAL: database "test_flood" does not exist

# Solution: Create test database
createdb test_flood
```

#### 2. Import Errors
```bash
# Error: ImportError: cannot import name 'GaugeFactory'

# Solution: Ensure you're in the src directory
cd src && pytest
```

#### 3. Slow Tests
```python
# Mark slow tests
@pytest.mark.slow
def test_large_dataset():
    pass

# Skip slow tests
pytest -m "not slow"
```

#### 4. Flaky Tests
```python
# Use retry for flaky tests
@pytest.mark.flaky(reruns=3)
def test_concurrent_access():
    pass
```

### Debugging Tests
```bash
# Run with debugging
pytest --pdb

# Show print statements
pytest -s

# Verbose output
pytest -vv

# Show local variables on failure
pytest -l
```

### Performance Optimization
1. Use `setUpTestData` for class-level fixtures
2. Use bulk_create for multiple objects
3. Use in-memory SQLite for unit tests
4. Parallelize test execution

## Test Maintenance

### Regular Tasks
1. **Weekly**: Review and update failing tests
2. **Monthly**: Check coverage reports
3. **Quarterly**: Performance benchmark review
4. **Annually**: Test framework upgrade

### Adding New Tests
1. Write test first (TDD)
2. Ensure test fails initially
3. Implement feature
4. Verify test passes
5. Check coverage
6. Add to appropriate test suite

### Deprecating Tests
1. Mark as deprecated with reason
2. Set removal date
3. Update related tests
4. Remove after grace period

## Resources

### Documentation
- [Django Testing](https://docs.djangoproject.com/en/stable/topics/testing/)
- [Pytest Documentation](https://docs.pytest.org/)
- [Factory Boy](https://factoryboy.readthedocs.io/)

### Tools
- Coverage.py - Code coverage
- pytest-benchmark - Performance testing
- pytest-xdist - Parallel execution
- safety - Security vulnerability scanning

---

*Last Updated: [Current Date]*
*Version: 1.0*