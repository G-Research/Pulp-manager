# Contributing to Pulp Manager

We're excited to have you contribute to our project! This document outlines the process you should follow to contribute effectively.

## How to Contribute

Basic instructions about where to send patches, check out source code, and get development support:

- **Patches**: Please send patches via pull requests on GitHub at https://github.com/G-Research/Pulp-manager.
- **Source Code**: You can check out the source code at https://github.com/G-Research/Pulp-manager.
- **Support**: For development support, please open an issue at https://github.com/G-Research/Pulp-manager/issues.

## Getting Started

Before you start contributing, please follow these steps:

- **Installation Steps**: See the [Development Info](#development-info) section in README.md for complete setup instructions
- **Pre-requisites**: 
  - Docker and Docker Compose
  - Python 3.10+ (for local development without containers)  
  - Git
  - 8GB RAM minimum (for running all services)
  - Visual Studio Code with Dev Containers extension (for DevContainer development)
- **Working with Source Code**: Use DevContainers (recommended) or manual setup as described in README.md

## Team

Understand our team structure and guidelines:

- For details on our team and roles, please see the [MAINTAINERS.md](MAINTAINERS.md) file.

## Building Dependencies

Don't forget to install all necessary dependencies:

- **Installation Steps**: 
  - DevContainer: Dependencies are automatically installed when opening in VS Code
  - Manual: Run `make venv` to create virtual environment and install dependencies
  - System dependencies: LDAP development libraries (`libldap2-dev libsasl2-dev libssl-dev` on Ubuntu/Debian)

## Building the Project

Ensure you can build the project successfully:

- **Build Scripts/Instructions**: 
  - Run tests: `make test` or `make t`
  - Run with coverage: `make cover` or `make c`
  - Run linting: `make lint` or `make l`

## Workflow and Branching

Our preferred workflow and branching structure:

- We use GitHub Flow with feature branches. Create a feature branch from main, make your changes, and submit a pull request back to main.

## Testing Conventions

Our approach to testing:

- **Test Location**: Tests are located in `pulp_manager/tests/` with unit tests in `pulp_manager/tests/unit/`
- **Running Tests**: 
  - All tests: `make test` or `./venv/bin/pytest`
  - Specific test file: `./venv/bin/pytest pulp_manager/tests/unit/services/test_pulp_manager.py -v`
  - With coverage: `make cover` or `coverage run --source=pulp_manager/app -m pytest`
- **Test Strategy/Goals**: 90% test coverage requirement. Use pytest with mocking for external dependencies, fakeredis for Redis mocking, and freezegun for time-based testing.

## Coding Style and Linters

Our coding standards and tools:

- **Coding Standards**: Follow existing code patterns in the codebase. Use repository pattern for data access, service layer for business logic, and dependency injection.
- **Linters**: We use pylint for Python code quality checks. Run with `make lint`.

## Writing Issues

Guidelines for filing issues:

- **Where to File Issues**: Please file issues at https://github.com/G-Research/Pulp-manager/issues.
- **Issue Conventions**: Follow our conventions outlined in [ISSUE_TEMPLATE.md](ISSUE_TEMPLATE.md).

## Writing Pull Requests

Guidelines for pull requests:

- **Where to File Pull Requests**: Submit your pull requests at https://github.com/G-Research/Pulp-manager/pulls.
- **PR Conventions**: Follow our conventions outlined in [PULL_REQUEST_TEMPLATE.md](PULL_REQUEST_TEMPLATE.md).

## Reviewing Pull Requests

How we review pull requests:

- **Review Process**: All pull requests require review and approval before merging. Ensure tests pass and coverage meets 90% threshold.
- **Reviewers**: Our reviews are conducted by project maintainers listed in [MAINTAINERS.md](MAINTAINERS.md).

## Shipping Releases

Our release process:

- **Cadence**: We ship releases as needed based on feature completion and bug fixes.
- **Responsible Parties**: Releases are managed by project maintainers.

## Documentation Updates

How we handle documentation:

- **Documentation Location**: Our documentation is hosted in the repository README.md, CLAUDE.md, and docs/ folder.
- **Update Process**: Documentation is updated as part of pull requests when changes affect user-facing functionality or development processes.
