# Neo Market — B2B Service

B2B service of the Neo Market platform built with Django, DRF, PostgreSQL, Docker and uv.

## Tech Stack

- Python 3.14
- Django 5
- Django REST Framework
- PostgreSQL 16
- Docker / Docker Compose
- uv
- Ruff
- Pytest

---

# Project Structure

```text
B2B/
├── config/               # Django project configuration
│   └── settings.py
│
├── B2B/                  # Business modules
│
├── tests/                # Tests
│
├── manage.py
├── Dockerfile
├── Makefile
├── pyproject.toml
├── uv.lock
└── .env
```

---

# Requirements

Before starting make sure you have installed:

- Docker
- Docker Compose
- Python 3.14+
- uv

Install uv:

```bash
brew install uv
```

or

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

---

# Local Development

## Install dependencies

```bash
cd app
make install
```

---

## Run development server

```bash
make run
```

Application will be available at:

```text
http://localhost:8000
```

---

# Docker

## Start infrastructure

From repository root:

```bash
docker compose up --build
```

B2B service will be available at:

```text
http://localhost:8001
```

---

# Database

## Create migrations

```bash
cd app
make migrations
```

---

## Apply migrations

```bash
cd app
make migrate
```

---

## Create superuser

```bash
cd app
make superuser
```

---

# Testing

Run tests:

```bash
cd app
make test
```

---

# Linting

Run linter:

```bash
cd app
make lint
```

Format code:

```bash
cd app
make format
```

---

# Useful Commands

| Command | Description |
|---|---|
| `make install` | Install dependencies |
| `make run` | Run Django server |
| `make migrations` | Create migrations |
| `make migrate` | Apply migrations |
| `make superuser` | Create admin user |
| `make shell` | Open Django shell |
| `make test` | Run tests |
| `make lint` | Run Ruff lint |
| `make format` | Format code |

---

# Environment 

GitHub -> Settings -> Environments -> B2B 

That's where all the secrets are.