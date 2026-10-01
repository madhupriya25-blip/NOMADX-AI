# NomadX AI Backend Architecture

## Existing Project Scan

The existing app is a single Flask application in `app.py` with legacy SQLite helpers and active frontend routes for:

- `/`, `/login`, `/register`, `/logout`, `/dashboard`
- `/hotels`, `/restaurants`, `/rentals`, `/map`, `/emergency`, `/chatbot`
- `/tripplanner`, `/weather`, `/scanner`, `/booking`, `/bookings`
- Existing frontend API calls under `/api/*`, `/chat`, `/nearby_places`, `/route_navigation`, `/live_location`

Frontend files were intentionally not modified:

- `templates/*.html`
- `static/css/style.css`
- `static/style.css`
- `static/script.js`
- `static/js/app.js`
- `static/js/rentals.js`

## Recommended Structure

```text
NomadX AI/
  app.py                         # Existing Flask app and legacy routes
  config.py                      # Env-driven production configuration
  nomadx_backend/
    extensions.py                # SQLAlchemy, Migrate, JWT, SocketIO, Limiter, Celery
    models.py                    # Normalized database models
    api/routes.py                # Production REST API under /api/v1
    websockets.py                # SocketIO events
    tasks.py                     # Celery background tasks
    services/                    # Integrations and domain logic
    utils/                       # Validation, response, upload security helpers
  migrations/                    # Flask-Migrate/Alembic bootstrap
  Dockerfile
  docker-compose.yml
  gunicorn.conf.py
  celery_worker.py
```

## Production APIs

New APIs are mounted under `/api/v1` to avoid breaking the existing frontend.

- Auth: `/api/v1/auth/register`, `/login`, `/refresh`, `/logout`, `/password-reset`, `/password-reset/confirm`, `/verify-email/<token>`
- Profile: `/api/v1/profile`
- Maps: `/api/v1/maps/search`, `/reverse`, `/route`, `/distance`, `/nearby`
- Hotels: `/api/v1/hotels`, `/api/v1/hotels/<id>`
- Restaurants: `/api/v1/restaurants`, `/api/v1/restaurants/<id>`
- Rentals: `/api/v1/rentals`, `/api/v1/rentals/<id>`
- Trips: `/api/v1/trips`
- Chat: `/api/v1/chat`, `/api/v1/chat/history`, `/api/v1/chat/stream`
- Weather: `/api/v1/weather/current`, `/api/v1/weather/forecast`
- Scanner: `/api/v1/scanner/scan`
- Emergency: `/api/v1/emergency/sos`, `/api/v1/emergency/services`
- Notifications: `/api/v1/notifications`, `/api/v1/notifications/<id>/read`
- Reviews: `/api/v1/reviews`
- Favorites: `/api/v1/favorites`
- Bookmarks: `/api/v1/bookmarks`
- Google Place details: `/api/v1/providers/google-places/<place_id>`

## External Providers

- OpenAI: set `OPENAI_API_KEY` and optional `OPENAI_MODEL` for trip planning and chatbot replies.
- OpenWeather: set `OPENWEATHER_API_KEY` for current weather; Open-Meteo fallback is used when absent.
- Google Places: set `GOOGLE_PLACES_API_KEY` and call hotel/restaurant list endpoints with `?realtime=true`.
- Nominatim, Overpass, OSRM, Open-Meteo: used for keyless maps, nearby search, routes, and fallback weather.
- SMTP: set `MAIL_SERVER`, `MAIL_PORT`, `MAIL_USERNAME`, `MAIL_PASSWORD`, `MAIL_FROM` for email verification, password reset, and notifications.
- Twilio-ready SMS architecture: configure `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_FROM_NUMBER` when you wire SMS delivery.

## Database

Normalized SQLAlchemy models cover:

- Users
- Trips
- Locations
- Hotels
- Restaurants
- CarRentals
- ChatHistory
- EmergencyRequests
- Notifications
- Reviews
- Favorites
- Bookmarks

Additional operational tables:

- Password reset tokens
- Email verification tokens
- JWT token blocklist
- Scanner uploads

## Local Development

```powershell
copy .env.example .env
.\venv\Scripts\pip.exe install -r requirements.txt
flask --app app db migrate -m "initial production backend"
flask --app app db upgrade
python app.py
```

The existing frontend remains available at `http://localhost:5000`. Production APIs are available at `http://localhost:5000/api/v1`.

## Docker Deployment

```powershell
copy .env.example .env
docker compose up --build
docker compose exec web flask --app app db upgrade
```

Services:

- `web`: Gunicorn + eventlet Flask app
- `worker`: Celery worker
- `postgres`: PostgreSQL 16
- `redis`: Redis 7

## Security Controls

- Password hashing through Werkzeug.
- JWT access and refresh tokens through Flask-JWT-Extended.
- Token revocation via `token_blocklist`.
- Input validation through `nomadx_backend/utils/validation.py`.
- SQL injection prevention through SQLAlchemy query composition.
- Upload hardening through extension allowlists and secure filenames.
- Rate limiting through Flask-Limiter and Redis.
- CSRF support through Flask-WTF; enable with `ENABLE_CSRF=true` once templates include CSRF tokens.
- XSS risk reduction for backend-sourced text through sanitization and existing frontend escaping.

## Compatibility Notes

The existing `/api/*` routes remain in `app.py` so the current UI continues to work. The production backend is additive and mounted under `/api/v1`. If the new production dependencies are not installed, `app.py` logs a warning and continues running the legacy app.
