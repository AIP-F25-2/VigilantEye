# VIGILANTEye Test Suite Documentation

## Overview

This directory contains comprehensive test cases and testing tools for the VIGILANTEye surveillance management system.

## Test Files

### 1. `test_api.py`
**Purpose**: Core API endpoint tests including authentication and user management.

**Test Coverage**:
- Health check endpoints
- User signup/registration
- User login/authentication
- Validation error handling
- Edge cases and error scenarios

**Run Tests**:
```bash
pytest tests/test_api.py -v
```

### 2. `test_telegram.py`
**Purpose**: Telegram notification integration tests.

**Test Coverage**:
- Message ingestion (text and image)
- Webhook callback handling
- Message status transitions
- Error handling and validation
- Telegram client functions

**Run Tests**:
```bash
pytest tests/test_telegram.py -v
```

### 3. `test_project_endpoints.py`
**Purpose**: Comprehensive tests for all project endpoints.

**Test Coverage**:
- Project CRUD operations
- Video management endpoints
- Recording management endpoints
- User management endpoints
- Integration tests
- Error handling

**Run Tests**:
```bash
pytest tests/test_project_endpoints.py -v
```

## Test Pages (HTML)

### 1. `test_page.html`
**Purpose**: Interactive web interface for testing all API endpoints.

**Features**:
- Tabbed interface for different API sections
- Sample data templates
- Real-time API testing
- Response visualization
- Auth token management
- Configuration options

**Usage**:
1. Open `tests/test_page.html` in a web browser
2. Configure the base URL (default: http://localhost:5000)
3. Select the appropriate tab (Authentication, Users, Projects, etc.)
4. Fill in the request data or use sample data
5. Click "Test" to send the request
6. View the response in the response area

### 2. `login_test_page.html`
**Purpose**: Dedicated interface for testing login functionality.

**Features**:
- Login form with sample credentials
- Multiple user scenarios
- API testing capabilities
- Response validation

### 3. `telegram_test_page.html`
**Purpose**: Dedicated interface for testing Telegram notifications.

**Features**:
- Text and image message sending
- Webhook callback testing
- Sample alert templates
- Real-time response display

## Running All Tests

### Run All Tests
```bash
pytest tests/ -v
```

### Run with Coverage
```bash
pytest tests/ --cov=app --cov-report=html
```

### Run Specific Test File
```bash
pytest tests/test_api.py -v
pytest tests/test_telegram.py -v
pytest tests/test_project_endpoints.py -v
```

### Run Specific Test Function
```bash
pytest tests/test_api.py::test_user_login_success -v
```

## Test Data

### Sample Users
- **Username**: `testuser`
- **Email**: `test@example.com`
- **Password**: `password123`

### Sample Projects
- **Name**: `Test Surveillance Project`
- **Category**: `security`
- **Description**: `A test project for surveillance`

### Sample Telegram Messages
- **Channel ID**: `-1001234567890`
- **Text Message**: Alert notifications
- **Image Message**: Surveillance image URLs

## Test Configuration

### Environment Variables
```bash
export DATABASE_URL=sqlite:///:memory:  # For in-memory testing
export TELEGRAM_BOT_TOKEN=test-token
export TELEGRAM_WEBHOOK_SECRET=test-secret
export SECRET_KEY=test-secret-key
```

### Test Database
Tests use an in-memory SQLite database by default for fast execution. For integration tests with MySQL, update the database URL in the test fixtures.

## Test Categories

### Unit Tests
- Individual function testing
- Model validation
- Schema validation
- Utility functions

### Integration Tests
- API endpoint testing
- Database operations
- External service integration (Telegram)
- Authentication flow

### End-to-End Tests
- Complete user workflows
- Multi-step operations
- Error recovery scenarios

## Writing New Tests

### Test Structure
```python
def test_feature_name(client):
    """Test description"""
    # Arrange
    test_data = {...}
    
    # Act
    response = client.post('/api/endpoint', json=test_data)
    
    # Assert
    assert response.status_code == 200
    data = response.get_json()
    assert data['status'] == 'success'
```

### Best Practices
1. Use descriptive test names
2. Follow Arrange-Act-Assert pattern
3. Test both success and failure cases
4. Use fixtures for common setup
5. Mock external services
6. Clean up test data

## Continuous Integration

Tests are designed to run in CI/CD pipelines:
- Fast execution (< 30 seconds)
- No external dependencies (mocked)
- Deterministic results
- Clear error messages

## Troubleshooting

### Common Issues

1. **Database Connection Errors**
   - Ensure test database is configured
   - Check DATABASE_URL environment variable
   - Use in-memory SQLite for unit tests

2. **Import Errors**
   - Ensure app is in Python path
   - Check __init__.py files exist
   - Verify all dependencies are installed

3. **Test Failures**
   - Check test output for specific errors
   - Verify sample data is valid
   - Ensure mocked services are configured

## Test Coverage Goals

- **Unit Tests**: > 80% coverage
- **Integration Tests**: All major endpoints
- **E2E Tests**: Critical user workflows

## Additional Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [Flask Testing Guide](https://flask.palletsprojects.com/en/2.3.x/testing/)
- [API Documentation](../README.md)

## Contributing

When adding new features:
1. Write tests first (TDD approach)
2. Ensure all tests pass
3. Maintain or improve test coverage
4. Update this documentation

---

**Last Updated**: 2024-01-15
**Test Suite Version**: 1.0.0
