# Contributing to Birth Time Rectifier

Thank you for your interest in contributing to the Birth Time Rectifier project! This document provides guidelines and instructions for contributing.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Workflow](#development-workflow)
- [Pull Request Process](#pull-request-process)
- [Coding Standards](#coding-standards)
- [Testing Guidelines](#testing-guidelines)
- [Documentation](#documentation)
- [Issue Reporting](#issue-reporting)
- [Feature Requests](#feature-requests)
- [Community](#community)

## Code of Conduct

This project adheres to a Code of Conduct that all contributors are expected to follow. By participating, you are expected to uphold this code. Please report unacceptable behavior to the project maintainers.

We are committed to providing a welcoming and inclusive environment for all contributors regardless of gender, sexual orientation, ability, ethnicity, socioeconomic status, and religion.

## Getting Started

### Prerequisites

Before you begin, ensure you have the following installed:
- Python 3.10 or higher
- Node.js 18 or higher
- PostgreSQL 14 or higher
- Redis 6 or higher
- Git

### Setting Up Your Development Environment

1. Fork the repository on GitHub
2. Clone your fork locally:
   ```bash
   git clone https://github.com/YOUR-USERNAME/birth-time-rectifier.git
   cd birth-time-rectifier
   ```
3. Add the original repository as an upstream remote:
   ```bash
   git remote add upstream https://github.com/original-owner/birth-time-rectifier.git
   ```
4. Create a virtual environment and install dependencies:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   pip install -r requirements-dev.txt  # Development dependencies
   ```
5. Install frontend dependencies:
   ```bash
   cd src
   npm install
   ```

## Development Workflow

1. Create a new branch for your feature or bugfix:
   ```bash
   git checkout -b feature/your-feature-name
   # or
   git checkout -b fix/issue-you-are-fixing
   ```

2. Make your changes, following our [coding standards](#coding-standards)

3. Run tests to ensure your changes don't break existing functionality:
   ```bash
   # Backend tests
   pytest tests/

   # Frontend tests
   cd src
   npm test
   ```

4. Commit your changes with a descriptive commit message:
   ```bash
   git commit -m "Add feature: your feature description"
   ```

5. Push your branch to your fork:
   ```bash
   git push origin feature/your-feature-name
   ```

6. Create a Pull Request from your fork to the original repository

## Pull Request Process

1. Ensure your PR includes a clear description of the changes and the purpose
2. Update documentation if necessary
3. Include tests for new functionality
4. Ensure all tests pass
5. Link any relevant issues in the PR description
6. Request a review from at least one maintainer
7. Address any feedback from reviewers
8. Once approved, a maintainer will merge your PR

## Coding Standards

### Python Code

- Follow [PEP 8](https://www.python.org/dev/peps/pep-0008/) style guide
- Use type hints for function parameters and return values
- Document functions, classes, and modules using docstrings
- Maximum line length of 100 characters
- Use meaningful variable and function names

### TypeScript/JavaScript Code

- Follow the project's ESLint configuration
- Use TypeScript for type safety
- Follow the [Airbnb JavaScript Style Guide](https://github.com/airbnb/javascript)
- Use functional components with hooks for React components
- Use async/await instead of promises where appropriate

### General Guidelines

- Keep functions and methods small and focused on a single responsibility
- Write self-documenting code with clear variable and function names
- Add comments only when necessary to explain complex logic
- Avoid duplicate code by creating reusable functions
- Follow the project's existing patterns and conventions

## Testing Guidelines

### Backend Testing

- Write unit tests for all new functionality
- Use pytest for testing
- Aim for at least 80% code coverage
- Mock external dependencies
- Test both success and failure cases
- Use fixtures for test data

### Frontend Testing

- Write unit tests for React components using Jest and React Testing Library
- Test component rendering and user interactions
- Mock API calls and external dependencies
- Test both success and error states
- Write integration tests for critical user flows

## Documentation

Good documentation is crucial for the project's success. Please follow these guidelines:

- Update the README.md if you change project setup or requirements
- Document new API endpoints in the API documentation
- Add JSDoc comments to TypeScript/JavaScript functions
- Update user documentation for user-facing changes
- Include code examples where appropriate
- Document configuration options and environment variables

## Issue Reporting

When reporting issues, please include:

1. A clear and descriptive title
2. Steps to reproduce the issue
3. Expected behavior
4. Actual behavior
5. Screenshots if applicable
6. Your environment (OS, browser, versions)
7. Any relevant logs or error messages

Use the issue templates provided in the repository.

## Feature Requests

We welcome feature requests! When suggesting a feature:

1. Check if the feature has already been suggested or implemented
2. Provide a clear description of the feature
3. Explain the use case and benefits
4. Consider implementation details if possible
5. Be open to feedback and alternatives

## Community

Join our community channels to get help and discuss the project:

- [Discord Server](https://discord.gg/birthrectifier)
- [Community Forum](https://community.birthrectifier.example.com)
- [Twitter](https://twitter.com/BirthRectifier)

## Recognition

Contributors will be recognized in the following ways:

- Addition to the CONTRIBUTORS.md file
- Mention in release notes for significant contributions
- Opportunity to become a project maintainer for consistent contributors

Thank you for contributing to Birth Time Rectifier!
