# VigilantEYE

**AI-Powered Video Intelligence System**

A complete full-stack application for video analysis with AI capabilities, featuring React frontend, Python backend, and AI services integration.

## Architecture Overview

This system follows a **layered architecture** with clear separation of concerns:

```
┌─────────────────────────────────────┐
│     API/Controllers Layer           │  ← HTTP/REST endpoints
├─────────────────────────────────────┤
│     Service Layer                   │  ← Business logic
├─────────────────────────────────────┤
│     Repository Layer                │  ← Data access abstraction
├─────────────────────────────────────┤
│     Database Layer                  │  ← Multiple database tables
└─────────────────────────────────────┘
```

## Project Structure

```
├── src/
│   ├── api/              # API controllers and routes
│   ├── services/         # Business logic services
│   ├── repositories/     # Data access layer
│   ├── models/           # Domain models and entities
│   ├── dto/              # Data Transfer Objects
│   ├── database/         # Database configuration and migrations
│   ├── middleware/       # Custom middleware
│   ├── utils/            # Utility functions and helpers
│   ├── config/           # Configuration management
│   └── main.py           # Application entry point
├── tests/                # Test suite
│   ├── unit/            # Unit tests
│   ├── integration/     # Integration tests
│   └── fixtures/        # Test fixtures and mocks
├── docs/                 # Documentation
├── scripts/              # Utility scripts
└── requirements/         # Python dependencies
```

## Design Principles

- **SOLID Principles**: Single Responsibility, Open/Closed, Liskov Substitution, Interface Segregation, Dependency Inversion
- **DRY (Don't Repeat Yourself)**: Code reusability
- **Separation of Concerns**: Each layer has a specific responsibility
- **Dependency Injection**: Loose coupling between components
- **Repository Pattern**: Abstract data access logic
- **Service Pattern**: Encapsulate business logic
- **DTO Pattern**: Data transfer between layers

## Getting Started

### Prerequisites
- Python 3.9+
- PostgreSQL/MySQL (or your preferred database)
- Virtual environment

### Installation

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements/development.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your configuration

# Run database migrations
python scripts/migrate.py create

# Start the application
python src/main.py
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src tests/

# Run specific test suite
pytest tests/unit/
```

## Development Workflow

1. Create feature branch
2. Implement changes following the architecture
3. Write unit and integration tests
4. Run tests and ensure coverage
5. Create pull request
6. Code review
7. Merge to main

## Configuration

Configuration is managed through environment variables and configuration files:
- `config/development.yml` - Development environment
- `config/staging.yml` - Staging environment
- `config/production.yml` - Production environment

## Contributing

See [CONTRIBUTING.md](docs/CONTRIBUTING.md) for guidelines.

## License

[Your License Here]
