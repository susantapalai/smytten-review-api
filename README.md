# Review Insights API

A Django REST Framework backend for product reviews, with JWT authentication, a pandas-based CSV cleaning pipeline, and an LLM-powered review summarizer (Google Gemini).

## Features

- **Products and reviews REST API** with pagination and filtering reviews by product
- **JWT authentication** (SimpleJWT): reads are public, writes require a token
- **LLM review summarizer**: `POST /api/products/{id}/summary/` returns sentiment, a short summary, pros and cons. If the LLM call fails or no API key is set, it returns a rating-based summary labelled `"source": "fallback"` instead of an error
- **CSV cleaning and import** (`import_reviews` management command) built with pandas: trims whitespace, normalises casing, parses ratings like `"4 stars"`, drops invalid rows and duplicates, and loads the data idempotently
- **Docker Compose** setup with PostgreSQL; falls back to SQLite when run without Docker

## Tech stack

- Python 3.12
- Django, Django REST Framework, SimpleJWT
- pandas
- Google Gemini API (`google-genai`)
- PostgreSQL 16 (Docker) or SQLite (local)
- Docker and Docker Compose

## Project structure

```
smytten-review-api/
├── config/                     # Django project settings and root URLs
├── reviews/
│   ├── models.py               # Product, Review
│   ├── serializers.py
│   ├── views.py                # ViewSets and the summary action
│   ├── services.py             # LLM call and fallback logic
│   ├── urls.py
│   └── management/commands/
│       └── import_reviews.py   # pandas CSV cleaning and import
├── data/sample_reviews.csv     # deliberately messy sample data
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── .env.example
```

## Setup (local, SQLite)

```bash
git clone https://github.com/susantapalai/smytten-review-api.git
cd smytten-review-api

python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS / Linux

pip install -r requirements.txt
```

Create your environment file and add a Gemini API key (free key from https://aistudio.google.com):

```bash
copy .env.example .env         # Windows
# cp .env.example .env         # macOS / Linux
```

Then run:

```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py import_reviews data/sample_reviews.csv
python manage.py runserver
```

The API is now at http://127.0.0.1:8000/api/ and the admin at http://127.0.0.1:8000/admin/.

## Setup (Docker, PostgreSQL)

Make sure Docker Desktop is running and that a `.env` file exists (see above), because Compose reads the API key from it.

```bash
docker compose up --build
```

In a second terminal:

```bash
docker compose exec web python manage.py createsuperuser
docker compose exec web python manage.py import_reviews data/sample_reviews.csv
```

The app is served at http://127.0.0.1:8000/. The database is a separate PostgreSQL container with a persistent volume. To confirm which database is in use:

```bash
docker compose exec web python manage.py shell -c "from django.db import connection; print(connection.vendor)"
```

## Environment variables

| Variable | Purpose | Default |
|---|---|---|
| `GEMINI_API_KEY` | API key for the summary endpoint | none (fallback summary is used) |
| `GEMINI_MODEL` | Gemini model name | `gemini-2.5-flash` |
| `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST`, `POSTGRES_PORT` | If `POSTGRES_DB` is set, Django uses PostgreSQL; otherwise SQLite. Set automatically by `docker-compose.yml` | unset |

Never commit `.env`. It is listed in `.gitignore`.

## API endpoints

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/api/token/` | none | Get `access` and `refresh` tokens |
| POST | `/api/token/refresh/` | none | Refresh an access token |
| GET | `/api/products/` | none | List products (paginated, 10 per page) |
| POST | `/api/products/` | JWT | Create a product |
| GET / PUT / PATCH / DELETE | `/api/products/{id}/` | write needs JWT | Retrieve, update or delete a product |
| POST | `/api/products/{id}/summary/` | JWT | LLM summary of the product's reviews |
| GET | `/api/reviews/?product={id}` | none | List reviews, optionally filtered by product |
| POST | `/api/reviews/` | JWT | Create a review (the user is taken from the token) |
| GET / PUT / PATCH / DELETE | `/api/reviews/{id}/` | write needs JWT | Retrieve, update or delete a review |

Ratings must be between 1 and 5.

## Example usage

Get a token (PowerShell):

```powershell
$body = @{ username = "admin"; password = "YOUR_PASSWORD" } | ConvertTo-Json
$t = Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/token/ -ContentType "application/json" -Body $body
```

Request a summary:

```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/products/1/summary/ -Headers @{Authorization="Bearer $($t.access)"}
```

The same with curl (macOS / Linux):

```bash
TOKEN=$(curl -s -X POST http://127.0.0.1:8000/api/token/ \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"YOUR_PASSWORD"}' | python -c "import sys,json; print(json.load(sys.stdin)['access'])")

curl -X POST http://127.0.0.1:8000/api/products/1/summary/ -H "Authorization: Bearer $TOKEN"
```

Example response:

```json
{
  "sentiment": "mixed",
  "summary": "Customers praise the shades and smooth application, but some find it drying and say the colour fades after a few hours.",
  "pros": ["Beautiful shades", "Smooth application", "Nice value for money"],
  "cons": ["Fades after a few hours", "Too drying on lips"],
  "average_rating": 3.75,
  "source": "llm"
}
```

## How the CSV import works

`python manage.py import_reviews <path-to-csv>` expects the columns `Product, Brand, Username, Rating, Review` and applies these steps:

1. Trim whitespace and treat blank values as missing
2. Drop rows with no product or no review text
3. Normalise casing (product and brand in title case, usernames in lower case) and collapse repeated spaces
4. Parse ratings such as `"4 stars"` into `4` and keep only values from 1 to 5
5. Remove duplicate reviews (same product, user and text)
6. Load into the database using `get_or_create`, so re-running the command does not create duplicates

On the included sample file, it reads 12 rows, keeps 8, and imports 8 reviews.

## How the summary endpoint works

1. Collects up to 50 reviews for the product
2. Sends them to Gemini with a prompt that asks for JSON (sentiment, summary, pros, cons)
3. Parses the response and adds the average rating
4. On any failure (missing key, quota, network, invalid JSON), logs the error and returns a rating-based summary with `"source": "fallback"` so the client always gets a usable response

## Known limitations and possible improvements

- The Docker image runs Django's development server; a production setup would use gunicorn behind a reverse proxy
- No automated tests yet (pytest and API tests are the next step)
- `DEBUG`, `SECRET_KEY` and `ALLOWED_HOSTS` in `settings.py` are development defaults and need hardening for deployment
- Summaries are generated on every request; caching them and rate limiting the endpoint would reduce cost and latency
- Swagger/OpenAPI documentation and a recommendation endpoint are not implemented yet