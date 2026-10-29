# Review Insights API

A Django REST Framework backend for product reviews with JWT authentication,
a pandas-based CSV cleaning pipeline, and an LLM-powered review summarizer.

## Features
- Products and reviews CRUD (REST, pagination, filtering by product)
- JWT authentication (read is public, writes require login)
- `POST /api/products/{id}/summary/` returns an LLM-generated sentiment,
  summary, pros and cons (Google Gemini), with a rating-based fallback if the
  LLM call fails
- `import_reviews` management command that cleans a messy CSV with pandas
  (trims whitespace, normalises casing, parses ratings, drops invalid rows
  and duplicates) and loads it idempotently

## Tech stack
Python 3.12, Django, Django REST Framework, SimpleJWT, pandas, Google Gemini API.
Uses SQLite by default; the models are database-agnostic.

## Setup
```bash
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
cp .env.example .env         # then add your GEMINI_API_KEY
python manage.py migrate
python manage.py createsuperuser
python manage.py import_reviews data/sample_reviews.csv
python manage.py runserver
```

## Endpoints
| Method | Path | Auth |
|---|---|---|
| POST | /api/token/ | none (returns access and refresh tokens) |
| GET/POST | /api/products/ | write needs JWT |
| GET/PUT/DELETE | /api/products/{id}/ | write needs JWT |
| GET/POST | /api/reviews/?product={id} | write needs JWT |
| POST | /api/products/{id}/summary/ | JWT required |

## Example
```bash
curl -X POST http://127.0.0.1:8000/api/products/1/summary/ -H "Authorization: Bearer <token>"
```

## Possible improvements
Docker Compose with PostgreSQL, automated tests, rate limiting on the LLM
endpoint, caching summaries.