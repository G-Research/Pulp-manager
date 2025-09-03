# GitHub Actions Workflows

This directory contains GitHub Actions workflows for continuous integration and testing.

## Workflows

### ci.yml - Comprehensive CI
- **Trigger**: Push to main branch, Pull requests, Manual dispatch
- **Jobs**:
  - **Lint**: Runs pylint on the codebase
  - **Test**: Runs pytest with coverage reporting
  - **Test-Make**: Runs tests using `make t` command
  - **Test Summary**: Provides a summary of all CI checks
- **Features**:
  - Coverage reporting with Codecov integration
  - JUnit XML test results
  - Test artifacts upload
  - Uses official devcontainers/ci GitHub Action for consistency

## Running Tests Locally

To replicate the CI environment locally:

```bash
# Using devcontainer
cd .devcontainer
docker compose up -d
docker compose exec devcontainer bash
cd /workspace
./venv/bin/pytest -v

# Using make
make t  # Run tests
make l  # Run lint
make c  # Run coverage
```

## Workflow Configuration

All workflows use the devcontainer environment to ensure consistency between local development and CI. The devcontainer includes:
- Python 3.10
- MariaDB 11.1.2
- Redis (latest)
- All required Python dependencies
- LDAP libraries for authentication

## Troubleshooting

If workflows fail:
1. Check that the devcontainer builds successfully locally
2. Ensure all services (MariaDB, Redis) are accessible
3. Verify that all dependencies in requirements.txt are installable
4. Check test database migrations are working correctly

## Adding New Workflows

When adding new workflows:
1. Use the devcontainer for consistency
2. Wait for services to be ready before running tests
3. Clean up resources in the `always()` block
4. Upload relevant artifacts for debugging
