# MUN Connect Testing Framework

This directory contains the testing framework for the MUN Connect backend. The tests are organized by functionality and are run using pytest.

## Setup

1. Install the required dependencies:

```bash
pip install -r requirements-test.txt
```

2. Configure your environment variables by copying `.env.test` to `.env`:

```bash
cp .env.test .env
```

3. Modify the environment variables in `.env` as needed for your local setup.

## Running Tests

You can run tests using the `run_tests.py` script:

```bash
# Run all tests
python run_tests.py --all

# Run unit tests only
python run_tests.py --unit

# Run API tests only
python run_tests.py --api

# Run AWS integration tests
python run_tests.py --aws

# Run authentication tests
python run_tests.py --auth

# Generate HTML report
python run_tests.py --report

# Generate coverage report
python run_tests.py --coverage

# Run specific test file
python run_tests.py --file test_basic.py
```

Alternatively, you can run pytest directly:

```bash
# Run specific test file
python -m pytest test_basic.py

# Run with verbose output
python -m pytest test_basic.py -v

# Run tests with a specific marker
python -m pytest -m unit

# Generate HTML report
python -m pytest --html=report/report.html

# Generate coverage report
python -m pytest --cov=backend --cov-report=html:coverage
```

## Test Organization

- `test_basic.py`: Basic tests to verify that the testing setup works
- `test_mind_map_api.py`: Tests for the mind map API
- `test_delegate_profile_api.py`: Tests for the delegate profile API
- `test_aws_integration.py`: Tests for AWS integration (S3, SageMaker)
- `test_aws_mcp.py`: Tests for AWS MCP integration
- `test_auth.py`: Tests for authentication

## Fixtures

The testing framework includes several fixtures that you can use in your tests:

- `aws_credentials`: Mock AWS credentials
- `s3_client`: Mock S3 client
- `supabase_mock`: Mock Supabase client
- `sagemaker_mock`: Mock SageMaker client
- `test_app`: A Flask test app
- `test_client`: A Flask test client
- `sample_pdf_file`: A sample PDF file for testing

## Adding New Tests

When adding new tests, follow these guidelines:

1. Create a new file with the prefix `test_`.
2. Use appropriate markers to categorize your tests (e.g., `@pytest.mark.unit`, `@pytest.mark.api`).
3. Use the provided fixtures when possible.
4. Keep tests focused and independent of each other.
5. Clean up after your tests to avoid affecting other tests.

## CI/CD Integration

These tests can be integrated into a CI/CD pipeline. The `run_tests.py` script returns the appropriate exit code that can be used to determine if the tests passed or failed. 