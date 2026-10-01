import requests
import json
import math
import os
import sqlite3
import uuid
import base64
from datetime import datetime, timedelta
from functools import wraps
from pathlib import Path

import requests
try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

from flask import (
    Flask,
    Blueprint,
    flash,
    has_request_context,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    session,
    url_for,
)
try:
    from flask_session import Session
except ImportError:
    Session = None
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

from nomadx_backend.services.emergency_numbers import (
    country_options,
    emergency_contacts_for_category,
    emergency_profile,
    infer_region_from_coordinates,
    lookup_emergency_number as resolve_emergency_number,
)


BASE_DIR = Path(__file__).resolve().parent
if load_dotenv:
    load_dotenv(BASE_DIR / ".env")
DATABASE_DIR = BASE_DIR / "database"
DATABASE_DIR.mkdir(exist_ok=True)
DB_PATH = DATABASE_DIR / "nomadx.db"
UPLOAD_DIR = BASE_DIR / "static" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

app = Flask(__name__)
app.secret_key = os.environ.get("NOMADX_SECRET_KEY", "nomadx-ai-dev-secret")
app.config["NOMADX_DB_PATH"] = str(DB_PATH)
app.config["UPLOAD_FOLDER"] = str(UPLOAD_DIR)
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(hours=8)
try:
    from config import load_config
    app.config.from_object(load_config())
except ImportError:
    pass
if Session:
    Path(app.config.get("SESSION_FILE_DIR", BASE_DIR / ".flask_session")).mkdir(parents=True, exist_ok=True)
    Session(app)

api_bp = Blueprint("api", __name__, url_prefix="/api")
try:
    from routes.chatbot import register_chatbot_routes
    register_chatbot_routes(api_bp)
except ImportError:
    pass


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def rows_to_dicts(rows):
    return [dict(row) for row in rows]


def current_user_id():
    if not has_request_context():
        return None
    return session.get("user_id")


SUPPORTED_LANGUAGES = [
    {"code": "en", "name": "English", "native": "English", "dir": "ltr"},
    {"code": "hi", "name": "Hindi", "native": "Hindi", "dir": "ltr"},
    {"code": "kn", "name": "Kannada", "native": "Kannada", "dir": "ltr"},
    {"code": "te", "name": "Telugu", "native": "Telugu", "dir": "ltr"},
    {"code": "ta", "name": "Tamil", "native": "Tamil", "dir": "ltr"},
    {"code": "ml", "name": "Malayalam", "native": "Malayalam", "dir": "ltr"},
    {"code": "mr", "name": "Marathi", "native": "Marathi", "dir": "ltr"},
    {"code": "bn", "name": "Bengali", "native": "Bengali", "dir": "ltr"},
    {"code": "gu", "name": "Gujarati", "native": "Gujarati", "dir": "ltr"},
    {"code": "pa", "name": "Punjabi", "native": "Punjabi", "dir": "ltr"},
    {"code": "ur", "name": "Urdu", "native": "Urdu", "dir": "rtl"},
    {"code": "ar", "name": "Arabic", "native": "Arabic", "dir": "rtl"},
    {"code": "zh-CN", "name": "Chinese (Simplified)", "native": "Chinese Simplified", "dir": "ltr"},
    {"code": "zh-TW", "name": "Chinese (Traditional)", "native": "Chinese Traditional", "dir": "ltr"},
    {"code": "ja", "name": "Japanese", "native": "Japanese", "dir": "ltr"},
    {"code": "ko", "name": "Korean", "native": "Korean", "dir": "ltr"},
    {"code": "th", "name": "Thai", "native": "Thai", "dir": "ltr"},
    {"code": "vi", "name": "Vietnamese", "native": "Vietnamese", "dir": "ltr"},
    {"code": "id", "name": "Indonesian", "native": "Indonesian", "dir": "ltr"},
    {"code": "ms", "name": "Malay", "native": "Malay", "dir": "ltr"},
    {"code": "fil", "name": "Filipino", "native": "Filipino", "dir": "ltr"},
    {"code": "tr", "name": "Turkish", "native": "Turkish", "dir": "ltr"},
    {"code": "fa", "name": "Persian", "native": "Persian", "dir": "rtl"},
    {"code": "ru", "name": "Russian", "native": "Russian", "dir": "ltr"},
    {"code": "uk", "name": "Ukrainian", "native": "Ukrainian", "dir": "ltr"},
    {"code": "de", "name": "German", "native": "German", "dir": "ltr"},
    {"code": "fr", "name": "French", "native": "French", "dir": "ltr"},
    {"code": "es", "name": "Spanish", "native": "Spanish", "dir": "ltr"},
    {"code": "pt", "name": "Portuguese", "native": "Portuguese", "dir": "ltr"},
    {"code": "it", "name": "Italian", "native": "Italian", "dir": "ltr"},
    {"code": "nl", "name": "Dutch", "native": "Dutch", "dir": "ltr"},
    {"code": "sv", "name": "Swedish", "native": "Swedish", "dir": "ltr"},
    {"code": "no", "name": "Norwegian", "native": "Norwegian", "dir": "ltr"},
    {"code": "da", "name": "Danish", "native": "Danish", "dir": "ltr"},
    {"code": "fi", "name": "Finnish", "native": "Finnish", "dir": "ltr"},
    {"code": "pl", "name": "Polish", "native": "Polish", "dir": "ltr"},
    {"code": "cs", "name": "Czech", "native": "Czech", "dir": "ltr"},
    {"code": "el", "name": "Greek", "native": "Greek", "dir": "ltr"},
    {"code": "ro", "name": "Romanian", "native": "Romanian", "dir": "ltr"},
    {"code": "hu", "name": "Hungarian", "native": "Hungarian", "dir": "ltr"},
    {"code": "he", "name": "Hebrew", "native": "Hebrew", "dir": "rtl"},
    {"code": "sw", "name": "Swahili", "native": "Swahili", "dir": "ltr"},
    {"code": "af", "name": "Afrikaans", "native": "Afrikaans", "dir": "ltr"},
    {"code": "zu", "name": "Zulu", "native": "Zulu", "dir": "ltr"},
    {"code": "am", "name": "Amharic", "native": "Amharic", "dir": "ltr"},
    {"code": "ne", "name": "Nepali", "native": "Nepali", "dir": "ltr"},
    {"code": "si", "name": "Sinhala", "native": "Sinhala", "dir": "ltr"},
    {"code": "my", "name": "Burmese", "native": "Burmese", "dir": "ltr"},
    {"code": "km", "name": "Khmer", "native": "Khmer", "dir": "ltr"},
    {"code": "lo", "name": "Lao", "native": "Lao", "dir": "ltr"},
    {"code": "mn", "name": "Mongolian", "native": "Mongolian", "dir": "ltr"},
    {"code": "ka", "name": "Georgian", "native": "Georgian", "dir": "ltr"},
    {"code": "hy", "name": "Armenian", "native": "Armenian", "dir": "ltr"},
]
SUPPORTED_LANGUAGE_CODES = {language["code"] for language in SUPPORTED_LANGUAGES}


def ensure_user_profile_columns(conn):
    existing = {row["name"] for row in conn.execute("PRAGMA table_info(users)").fetchall()}
    profile_columns = {
        "profile_image": "TEXT",
        "phone_number": "TEXT",
        "google_name": "TEXT",
        "google_email": "TEXT",
        "google_picture": "TEXT",
        "google_sub": "TEXT",
        "google_connected_at": "TEXT",
        "theme": "TEXT DEFAULT 'dark'",
        "language": "TEXT DEFAULT 'en'",
        "notifications": "INTEGER DEFAULT 1",
        "email_prefs": "INTEGER DEFAULT 1",
        "currency": "TEXT DEFAULT 'USD'",
    }
    for column, definition in profile_columns.items():
        if column not in existing:
            conn.execute(f"ALTER TABLE users ADD COLUMN {column} {definition}")


def get_user_profile(user_id=None):
    user_id = user_id or current_user_id()
    if not user_id:
        return {
            "username": "",
            "email": "",
            "phone_number": "",
            "profile_image": "",
            "google_name": "",
            "google_email": "",
            "google_picture": "",
            "google_sub": "",
            "google_connected_at": "",
            "photo_url": "",
            "initial": "N",
            "theme": "dark",
            "language": "en",
            "notifications": True,
            "email_prefs": True,
            "currency": "USD",
        }

    with get_db() as conn:
        user = conn.execute(
            """
            SELECT id, username, email, phone_number, profile_image, google_name, google_email,
                   google_picture, google_sub, google_connected_at, theme, language,
                   notifications, email_prefs, currency
            FROM users
            WHERE id=?
            """,
            (user_id,),
        ).fetchone()

    if not user:
        return {
            "username": "",
            "email": "",
            "phone_number": "",
            "profile_image": "",
            "google_name": "",
            "google_email": "",
            "google_picture": "",
            "google_sub": "",
            "google_connected_at": "",
            "photo_url": "",
            "initial": "N",
            "theme": "dark",
            "language": "en",
            "notifications": True,
            "email_prefs": True,
            "currency": "USD",
        }

    profile = dict(user)
    profile["phone_number"] = profile.get("phone_number") or ""
    profile["profile_image"] = profile.get("profile_image") or ""
    profile["google_name"] = profile.get("google_name") or ""
    profile["google_email"] = profile.get("google_email") or ""
    profile["google_picture"] = profile.get("google_picture") or ""
    profile["google_sub"] = profile.get("google_sub") or ""
    profile["google_connected_at"] = profile.get("google_connected_at") or ""
    profile["theme"] = profile.get("theme") if profile.get("theme") in {"dark", "light", "auto"} else "dark"
    profile["language"] = profile.get("language") if profile.get("language") in SUPPORTED_LANGUAGE_CODES else "en"
    profile["notifications"] = bool(profile.get("notifications", 1))
    profile["email_prefs"] = bool(profile.get("email_prefs", 1))
    profile["currency"] = profile.get("currency") or "USD"
    profile["photo_url"] = profile["profile_image"] or profile["google_picture"]
    display_name = profile.get("username") or profile.get("google_name") or profile.get("email") or "NomadX"
    profile["initial"] = display_name.strip()[:1].upper() or "N"
    return profile


def get_dashboard_template_user(user_id=None):
    profile = get_user_profile(user_id)
    display_name = profile.get("username") or profile.get("google_name") or "NomadX Traveler"
    email = profile.get("email") or profile.get("google_email") or "traveler@nomadx.ai"
    return {
        "name": display_name,
        "email": email,
        "phone": profile.get("phone_number") or "",
        "phone_number": profile.get("phone_number") or "",
        "photo": "",
        "google_linked": bool(profile.get("google_email") or profile.get("google_name") or profile.get("google_picture")),
        "google_name": profile.get("google_name") or "",
        "google_email": profile.get("google_email") or "",
        "google_photo": profile.get("google_picture") or profile.get("profile_image") or "",
        "photo_url": profile.get("photo_url") or "",
        "theme": profile.get("theme") or "dark",
        "language": profile.get("language") or "en",
        "notifications": bool(profile.get("notifications", True)),
        "email_prefs": bool(profile.get("email_prefs", True)),
        "currency": profile.get("currency") or "USD",
    }


def decode_google_credential(credential):
    if not credential or credential.count(".") < 2:
        return {}
    try:
        payload = credential.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        return json.loads(base64.urlsafe_b64decode(payload.encode("utf-8")))
    except (ValueError, TypeError, json.JSONDecodeError, UnicodeDecodeError):
        return {}


@app.context_processor
def inject_profile_context():
    if not has_request_context():
        return {
            "current_profile": get_user_profile(None),
            "google_client_id": os.environ.get("GOOGLE_CLIENT_ID", ""),
            "supported_languages": SUPPORTED_LANGUAGES,
        }
    if "user_id" not in session:
        return {
            "current_profile": get_user_profile(None),
            "google_client_id": os.environ.get("GOOGLE_CLIENT_ID", ""),
            "supported_languages": SUPPORTED_LANGUAGES,
        }
    return {
        "current_profile": get_user_profile(session.get("user_id")),
        "google_client_id": os.environ.get("GOOGLE_CLIENT_ID", ""),
        "supported_languages": SUPPORTED_LANGUAGES,
    }


def create_password_reset(user_id):
    token = uuid.uuid4().hex
    expires_at = (datetime.utcnow() + timedelta(hours=1)).isoformat()
    with get_db() as conn:
        conn.execute(
            "INSERT INTO password_resets(user_id, token, expires_at) VALUES(?,?,?)",
            (user_id, token, expires_at),
        )
    return token


def get_password_reset(token):
    with get_db() as conn:
        return conn.execute(
            "SELECT * FROM password_resets WHERE token=?",
            (token,),
        ).fetchone()


def consume_password_reset(token):
    reset = get_password_reset(token)
    if not reset:
        return None

    expires_at = datetime.fromisoformat(reset["expires_at"])
    if datetime.utcnow() > expires_at:
        with get_db() as conn:
            conn.execute("DELETE FROM password_resets WHERE token=?", (token,))
        return None

    with get_db() as conn:
        conn.execute("DELETE FROM password_resets WHERE token=?", (token,))
    return reset["user_id"]


def ensure_default_session():
    if "user_id" in session:
        return

    email = "traveler@nomadx.ai"
    with get_db() as conn:
        user = conn.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        if not user:
            conn.execute(
                "INSERT INTO users(username,email,password) VALUES(?,?,?)",
                ("NomadX Traveler", email, generate_password_hash("nomadx-demo")),
            )
            user = conn.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()

    session["user_id"] = user["id"]
    session["user"] = user["username"]
    session["email"] = user["email"]


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("landing_seen"):
            return redirect(url_for("index"))
        if "user_id" not in session:
            flash("Please login to continue.", "warning")
            return redirect(url_for("login"))
        return view(*args, **kwargs)

    return wrapped


def json_login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            return jsonify({"success": False, "error": "Login required"}), 401
        return view(*args, **kwargs)

    return wrapped


def init_db():
    with get_db() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                phone_number TEXT,
                password TEXT NOT NULL,
                profile_image TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS password_resets(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                token TEXT UNIQUE NOT NULL,
                expires_at TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS hotels(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                city TEXT NOT NULL,
                country TEXT NOT NULL,
                address TEXT NOT NULL,
                owner_name TEXT NOT NULL,
                owner_phone TEXT NOT NULL,
                price REAL NOT NULL,
                rating REAL NOT NULL,
                available_rooms INTEGER NOT NULL,
                description TEXT NOT NULL,
                image TEXT NOT NULL,
                amenities TEXT NOT NULL,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS restaurants(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                cuisine TEXT NOT NULL,
                city TEXT NOT NULL,
                country TEXT NOT NULL,
                location TEXT NOT NULL,
                contact_phone TEXT NOT NULL,
                price_range TEXT NOT NULL,
                rating REAL NOT NULL,
                available_tables INTEGER NOT NULL,
                description TEXT NOT NULL,
                image TEXT NOT NULL,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS rentals(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                vehicle TEXT NOT NULL,
                vehicle_type TEXT NOT NULL,
                city TEXT NOT NULL,
                location TEXT NOT NULL,
                owner_phone TEXT NOT NULL,
                rental_agency TEXT NOT NULL,
                availability TEXT NOT NULL,
                pickup_address TEXT NOT NULL,
                fuel_type TEXT NOT NULL,
                transmission TEXT NOT NULL,
                price REAL NOT NULL,
                rating REAL NOT NULL,
                description TEXT NOT NULL,
                image TEXT NOT NULL,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS bookings(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                booking_type TEXT NOT NULL,
                item_id INTEGER,
                item_name TEXT NOT NULL,
                location TEXT NOT NULL,
                price TEXT NOT NULL,
                booking_date TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'Confirmed',
                details TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS chatbot_history(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                message TEXT NOT NULL,
                reply TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS emergency_requests(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                category TEXT NOT NULL,
                latitude REAL,
                longitude REAL,
                location_text TEXT,
                status TEXT NOT NULL DEFAULT 'Logged',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS trip_plans(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                destination TEXT NOT NULL,
                travel_date TEXT NOT NULL,
                budget TEXT NOT NULL,
                plan_json TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS live_locations(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                latitude REAL NOT NULL,
                longitude REAL NOT NULL,
                accuracy REAL,
                heading REAL,
                speed REAL,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS chats(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                message TEXT NOT NULL,
                reply TEXT NOT NULL,
                provider TEXT DEFAULT 'local',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS emergency_logs(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                category TEXT NOT NULL,
                latitude REAL,
                longitude REAL,
                location_text TEXT,
                status TEXT NOT NULL DEFAULT 'Logged',
                contacts_json TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS weather_cache(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cache_key TEXT UNIQUE NOT NULL,
                payload_json TEXT NOT NULL,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
        ensure_user_profile_columns(conn)
        seed_data(conn)


def seed_data(conn):
    if conn.execute("SELECT COUNT(*) FROM hotels").fetchone()[0] == 0:
        conn.executemany(
            """
            INSERT INTO hotels(name, city, country, address, owner_name, owner_phone, price, rating,
            available_rooms, description, image, amenities)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            [
                ("Luxury Palace Hotel", "Dubai", "UAE", "Marina Walk, Dubai Marina", "Aisha Khan", "+971-55-120-4433", 320, 4.9, 18, "Infinity Pool - Spa - Smart Rooms", "https://images.unsplash.com/photo-1566073771259-6a8506099945", "Pool,Spa,Airport pickup,AI concierge"),
                ("Ocean View Resort", "Male", "Maldives", "North Atoll Beach Road", "Ravi Menon", "+960-778-4491", 450, 4.8, 9, "Beach Access - Luxury Dining - Water villas", "https://images.unsplash.com/photo-1522798514-97ceb8c4f1c8", "Beach,Dining,Snorkeling,Transfers"),
                ("Smart Budget Inn", "Bangalore", "India", "Indiranagar 100 Feet Road", "Meera Rao", "+91-98450-22331", 70, 4.5, 42, "Comfortable stay for budget travelers", "https://images.unsplash.com/photo-1505693416388-ac5ce068fe85", "WiFi,Breakfast,Metro access"),
                ("Kyoto Zen Stay", "Kyoto", "Japan", "Gion District, Hanamikoji Street", "Hiro Tanaka", "+81-75-441-2201", 185, 4.7, 15, "Minimal ryokan-style smart stay near temples", "https://images.unsplash.com/photo-1542314831-068cd1dbfeeb", "Tea room,Guided walks,Smart locks"),
                ("Paris Lumiere Suites", "Paris", "France", "Rue Cler, 7th Arrondissement", "Camille Moreau", "+33-1-88-42-1940", 260, 4.6, 21, "Boutique suites near the Eiffel Tower", "https://images.unsplash.com/photo-1551882547-ff40c63fe5fa", "City views,Cafe,Concierge"),
            ],
        )

    if conn.execute("SELECT COUNT(*) FROM restaurants").fetchone()[0] == 0:
        conn.executemany(
            """
            INSERT INTO restaurants(name, cuisine, city, country, location, contact_phone, price_range,
            rating, available_tables, description, image)
            VALUES(?,?,?,?,?,?,?,?,?,?,?)
            """,
            [
                ("Skyline Lounge", "Italian", "Dubai", "UAE", "Dubai Marina", "+971-55-404-8877", "Luxury", 4.9, 6, "Premium rooftop dining with skyline views.", "https://images.unsplash.com/photo-1517248135467-4c7edcad34c4"),
                ("Ocean Breeze Cafe", "Seafood", "Male", "Maldives", "Beachfront Promenade", "+960-990-1182", "Mid-Range", 4.6, 12, "Fresh seafood and ocean ambience.", "https://images.unsplash.com/photo-1552566626-52f8b828add9"),
                ("Spice Garden", "Indian", "Bangalore", "India", "Koramangala 5th Block", "+91-99800-44221", "Cheap", 4.8, 18, "Traditional Indian flavors and premium hospitality.", "https://images.unsplash.com/photo-1541544741938-0af808871cc0"),
                ("Sakura Table", "Japanese", "Kyoto", "Japan", "Gion Corner", "+81-75-200-8811", "Luxury", 4.7, 5, "Seasonal kaiseki dining and tea pairings.", "https://images.unsplash.com/photo-1553621042-f6e147245754"),
            ],
        )

    if conn.execute("SELECT COUNT(*) FROM rentals").fetchone()[0] == 0:
        conn.executemany(
            """
            INSERT INTO rentals(vehicle, vehicle_type, city, location, owner_phone, rental_agency,
            availability, pickup_address, fuel_type, transmission, price, rating, description, image)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            [
                ("BMW M4 Coupe", "Luxury Sports Car", "Dubai", "Dubai Marina", "+971-55-701-9900", "NomadX Elite Motors", "Available", "Marina Gate Pickup Zone", "Petrol", "Automatic", 18500, 4.9, "Premium luxury sports vehicle with smart navigation.", "https://images.unsplash.com/photo-1492144534655-ae79c964c9d7"),
                ("Tesla Model X", "Electric SUV", "Bangalore", "Indiranagar", "+91-99002-17721", "VoltRide Rentals", "Available", "Indiranagar Metro Gate B", "Electric", "Automatic", 14200, 4.8, "AI-powered electric SUV for eco-friendly travel.", "https://images.unsplash.com/photo-1503376780353-7e6692767b70"),
                ("Range Rover Sport", "Luxury SUV", "Mumbai", "Bandra", "+91-98201-55442", "Urban Trail Cars", "Limited", "Bandra Kurla Complex", "Diesel", "Automatic", 16800, 4.7, "Premium SUV for long road trips and adventure.", "https://images.unsplash.com/photo-1552519507-da3b142c6e3d"),
                ("Kawasaki Ninja", "Bike Rental", "Goa", "Calangute", "+91-77988-44219", "Coastal Bike Hub", "Available", "Calangute Beach Parking", "Petrol", "Manual", 4500, 4.9, "Sports bike for coastal rides and mountain routes.", "https://images.unsplash.com/photo-1511919884226-fd3cad34687c"),
            ],
        )


init_db()


def query_catalog(table, filters):
    allowed = {"hotels", "restaurants", "rentals"}
    if table not in allowed:
        return []

    sql = f"SELECT * FROM {table} WHERE 1=1"
    params = []

    for column, value in filters.items():
        if not value:
            continue
        if column == "max_price":
            sql += " AND price <= ?"
            params.append(float(value))
        elif column == "min_rating":
            sql += " AND rating >= ?"
            params.append(float(value))
        else:
            sql += f" AND LOWER({column}) LIKE ?"
            params.append(f"%{value.lower()}%")

    if table in {"hotels", "rentals"}:
        sql += " ORDER BY rating DESC, price ASC"
    else:
        sql += " ORDER BY rating DESC, available_tables DESC"
    with get_db() as conn:
        return rows_to_dicts(conn.execute(sql, params).fetchall())


def booking_payload(row):
    data = dict(row)
    data["ticket_code"] = f"NX-{data['id']:05d}"
    data["date"] = data.get("booking_date")
    return data


def create_booking(user_id, booking_type, item_id, item_name, location, price, booking_date, details=None):
    with get_db() as conn:
        cur = conn.execute(
            """
            INSERT INTO bookings(user_id, booking_type, item_id, item_name, location, price,
            booking_date, status, details)
            VALUES(?,?,?,?,?,?,?,?,?)
            """,
            (
                user_id,
                booking_type,
                item_id,
                item_name,
                location,
                str(price),
                booking_date or datetime.now().date().isoformat(),
                "Confirmed",
                json.dumps(details or {}),
            ),
        )
        return cur.lastrowid


def parse_float_arg(name, default=None):
    value = request.args.get(name)
    if value in (None, ""):
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def osm_search(query, limit=8):
    response = requests.get(
        "https://nominatim.openstreetmap.org/search",
        params={
            "format": "json",
            "q": query,
            "limit": limit,
            "addressdetails": 1,
            "extratags": 1,
        },
        headers={"User-Agent": "NomadXAI/1.0 (smart-map)"},
        timeout=8,
    )
    response.raise_for_status()
    return response.json()


def overpass_nearby(lat, lon, kind, radius=3000, limit=12):
    tag_sets = {
        "hotels": ['["tourism"="hotel"]', '["tourism"="guest_house"]', '["tourism"="hostel"]'],
        "restaurants": ['["amenity"="restaurant"]', '["amenity"="cafe"]', '["amenity"="fast_food"]'],
        "hospitals": ['["amenity"="hospital"]', '["amenity"="clinic"]', '["healthcare"="hospital"]'],
        "police": ['["amenity"="police"]'],
        "fuel": ['["amenity"="fuel"]', '["amenity"="charging_station"]'],
        "airports": ['["aeroway"="aerodrome"]', '["aeroway"="terminal"]'],
        "rentals": ['["amenity"="car_rental"]', '["amenity"="bicycle_rental"]'],
        "attractions": ['["tourism"="attraction"]', '["tourism"="museum"]', '["historic"]'],
        "places": ['["tourism"="attraction"]', '["amenity"="restaurant"]', '["tourism"="hotel"]'],
    }
    selectors = tag_sets.get(kind, tag_sets["places"])
    queries = []
    for selector in selectors:
        queries.append(f'node(around:{radius},{lat},{lon}){selector};')
        queries.append(f'way(around:{radius},{lat},{lon}){selector};')
    overpass_query = "[out:json][timeout:8];(" + "".join(queries) + ");out center tags " + str(limit) + ";"
    response = requests.post(
        "https://overpass-api.de/api/interpreter",
        data={"data": overpass_query},
        headers={"User-Agent": "NomadXAI/1.0 (nearby-finder)"},
        timeout=10,
    )
    response.raise_for_status()
    return response.json().get("elements", [])


def catalog_nearby(lat, lon, kind, limit=5):
    table = "rentals" if kind in {"rentals", "rental"} else kind
    if table not in {"hotels", "restaurants", "rentals"}:
        return []

    with get_db() as conn:
        rows = rows_to_dicts(conn.execute(f"SELECT * FROM {table} ORDER BY rating DESC LIMIT ?", (limit,)).fetchall())

    offsets = [(0.004, 0.005), (-0.005, 0.004), (0.006, -0.003), (-0.004, -0.006), (0.002, 0.007)]
    places = []
    for index, row in enumerate(rows):
        place_lat = lat + offsets[index % len(offsets)][0]
        place_lon = lon + offsets[index % len(offsets)][1]
        if table == "hotels":
            name = row["name"]
            details = {
                "owner_name": row["owner_name"],
                "phone": row["owner_phone"],
                "address": row["address"],
                "availability": f'{row["available_rooms"]} rooms available',
                "price": f'Rs {row["price"]}/night',
                "rating": row["rating"],
            }
        elif table == "restaurants":
            name = row["name"]
            details = {
                "phone": row["contact_phone"],
                "address": row["location"],
                "availability": f'{row["available_tables"]} tables available',
                "price": row["price_range"],
                "rating": row["rating"],
                "cuisine": row["cuisine"],
            }
        else:
            name = row["vehicle"]
            details = {
                "owner_name": row["rental_agency"],
                "phone": row["owner_phone"],
                "pickup_address": row["pickup_address"],
                "availability": row["availability"],
                "price_per_day": f'Rs {row["price"]}/day',
                "vehicle_type": row["vehicle_type"],
                "rating": row["rating"],
            }
        places.append(
            {
                "name": name,
                "lat": place_lat,
                "lon": place_lon,
                "type": table,
                "source": "NomadX SQLite",
                "distance_km": round(haversine_km(lat, lon, place_lat, place_lon), 2),
                "eta_min": max(3, round(haversine_km(lat, lon, place_lat, place_lon) / 25 * 60)),
                "details": details,
            }
        )
    return places


def fallback_nearby(lat, lon, kind):
    offsets = [(0.006, 0.004), (-0.004, 0.006), (0.003, -0.005), (-0.007, -0.003)]
    names = {
        "hospitals": ["CityCare Hospital", "Metro Emergency Clinic", "NomadX Medical Point"],
        "police": ["Central Police Station", "Tourist Police Desk", "Safety Patrol Unit"],
        "fire": ["Main Fire Station", "Rapid Fire Response", "Urban Rescue Station"],
        "fuel": ["Express Fuel Station", "GreenCharge EV Hub", "Highway Fuel Point"],
        "airports": ["International Airport Terminal", "Domestic Departure Gate", "Airport Transfer Hub"],
        "attractions": ["City Museum", "Central Park", "Culture Walk"],
        "places": ["City Museum", "Central Park", "Culture Walk"],
    }
    return [
        {
            "name": name,
            "lat": lat + offsets[i][0],
            "lon": lon + offsets[i][1],
            "type": kind,
            "source": "NomadX fallback",
            "distance_km": round(haversine_km(lat, lon, lat + offsets[i][0], lon + offsets[i][1]), 2),
            "eta_min": 5 + i * 4,
            "details": {},
        }
        for i, name in enumerate(names.get(kind, names["places"]))
    ]


def normalize_osm_place(element, origin_lat, origin_lon, kind):
    tags = element.get("tags", {})
    place_lat = element.get("lat") or element.get("center", {}).get("lat")
    place_lon = element.get("lon") or element.get("center", {}).get("lon")
    if place_lat is None or place_lon is None:
        return None
    place_lat = float(place_lat)
    place_lon = float(place_lon)
    distance = haversine_km(origin_lat, origin_lon, place_lat, place_lon)
    return {
        "name": tags.get("name") or tags.get("brand") or kind.title(),
        "lat": place_lat,
        "lon": place_lon,
        "type": kind,
        "source": "OpenStreetMap",
        "distance_km": round(distance, 2),
        "eta_min": max(3, round(distance / 25 * 60)),
        "details": {
            "address": ", ".join(filter(None, [tags.get("addr:street"), tags.get("addr:city")])),
            "phone": tags.get("phone") or tags.get("contact:phone"),
            "website": tags.get("website") or tags.get("contact:website"),
            "availability": "Live OSM result",
            "price": tags.get("fee") or tags.get("charge"),
        },
    }


def reverse_geocode(lat, lon):
    try:
        response = requests.get(
            "https://nominatim.openstreetmap.org/reverse",
            params={"format": "json", "lat": lat, "lon": lon, "addressdetails": 1},
            headers={"User-Agent": "NomadXAI/1.0 (reverse-geocoder)"},
            timeout=8,
        )
        response.raise_for_status()
        data = response.json()
        address = data.get("address", {})
        return {
            "display_name": data.get("display_name") or f"{lat}, {lon}",
            "street": address.get("road") or address.get("neighbourhood") or "",
            "district": address.get("county") or address.get("state_district") or "",
            "city": address.get("city") or address.get("town") or address.get("village") or "",
            "state": address.get("state") or "",
            "country": address.get("country") or "",
            "country_code": (address.get("country_code") or "").upper(),
        }
    except requests.RequestException:
        return {
            "display_name": f"{lat}, {lon}",
            "street": "",
            "district": "",
            "city": "Current Location",
            "state": "",
            "country": "Live estimate",
            "country_code": "",
        }


def infer_location_from_query(query):
    text = (query or "").lower()
    for marker in [" near ", " in ", " at "]:
        if marker in text:
            return query.lower().split(marker, 1)[1].strip()
    return query


def meaningful_tokens(text):
    stopwords = {
        "near",
        "me",
        "in",
        "at",
        "the",
        "a",
        "an",
        "hotel",
        "hotels",
        "restaurant",
        "restaurants",
        "rental",
        "rentals",
        "cars",
        "car",
        "bike",
        "bikes",
    }
    return [word for word in "".join(ch if ch.isalnum() else " " for ch in text.lower()).split() if word not in stopwords]


def row_matches_query(row, query, fields):
    tokens = meaningful_tokens(query)
    haystack = " ".join(str(row[field]).lower() for field in fields if field in row.keys())
    return not tokens or any(token in haystack for token in tokens)


def enrich_hotel(row):
    hotel = dict(row)
    amenities = [item.strip() for item in hotel.get("amenities", "").split(",") if item.strip()]
    hotel.update(
        {
            "exact_location": f"{hotel['address']}, {hotel['city']}, {hotel['country']}",
            "timings": "24-hour front desk",
            "room_price": f"Rs {hotel['price']}/night",
            "booking_availability": hotel["available_rooms"] > 0,
            "photos": [hotel["image"]],
            "contact_number": hotel["owner_phone"],
            "map_location": {"query": f"{hotel['name']} {hotel['city']}"},
            "reviews": [
                {"author": "NomadX traveler", "rating": hotel["rating"], "text": "Clean, well located, and easy to book."}
            ],
            "amenities_list": amenities,
            "nearby_places": ["Restaurants", "Transit", "Tourist attractions"],
        }
    )
    return hotel


def enrich_restaurant(row):
    restaurant = dict(row)
    restaurant.update(
        {
            "exact_location": f"{restaurant['location']}, {restaurant['city']}, {restaurant['country']}",
            "timings": "11:00 AM - 11:00 PM",
            "contact_number": restaurant["contact_phone"],
            "table_booking": restaurant["available_tables"] > 0,
            "menu_preview": [restaurant["cuisine"], restaurant["price_range"], "Chef specials"],
            "map_location": {"query": f"{restaurant['name']} {restaurant['city']}"},
            "reviews": [
                {"author": "NomadX diner", "rating": restaurant["rating"], "text": "Reliable food stop for travelers."}
            ],
        }
    )
    return restaurant


def enrich_rental(row):
    rental = dict(row)
    rental.update(
        {
            "owner_contact_number": rental["owner_phone"],
            "owner_address": rental["pickup_address"],
            "availability_status": rental["availability"],
            "map_location": {"query": f"{rental['vehicle']} {rental['city']}"},
            "booking_available": rental["availability"].lower() != "unavailable",
        }
    )
    return rental


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/enter")
def enter_app():
    allowed_next = {
        "dashboard",
        "hotels",
        "restaurants",
        "rentals",
        "map_page",
        "emergency",
        "chatbot",
        "tripplanner",
        "weather",
        "scanner",
        "booking",
        "login",
        "register",
    }
    next_endpoint = request.args.get("next", "dashboard")
    if next_endpoint not in allowed_next:
        next_endpoint = "dashboard"

    session["landing_seen"] = True
    if next_endpoint in {"login", "register"}:
        return redirect(url_for(next_endpoint))

    if "user_id" not in session:
        session["post_login_next"] = next_endpoint
        return redirect(url_for("login"))

    return redirect(url_for(next_endpoint))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET" and "user_id" in session:
        return redirect(url_for("dashboard"))

    error = None
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        with get_db() as conn:
            user = conn.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()

        if user and check_password_hash(user["password"], password):
            landing_seen = session.get("landing_seen")
            post_login_next = session.get("post_login_next", "dashboard")
            session.clear()
            session.permanent = True
            if landing_seen:
                session["landing_seen"] = True
            session["user_id"] = user["id"]
            session["user"] = user["username"]
            session["email"] = user["email"]
            flash("Welcome back to NomadX AI.", "success")
            return redirect(url_for(post_login_next if landing_seen else "index"))

        error = "Invalid email or password. Please try again."
        flash(error, "danger")

    return render_template("login.html", error=error)


@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    reset_url = None
    error = None
    message = None
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        if not email:
            error = "Please enter your email address."
            return render_template("forgot_password.html", reset_url=reset_url, error=error, message=message)

        with get_db() as conn:
            user = conn.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()

        if user:
            token = create_password_reset(user["id"])
            reset_url = url_for("reset_password", token=token, _external=True)

        message = "If an account with that email exists, a password reset link has been generated."
        return render_template("forgot_password.html", reset_url=reset_url, error=error, message=message)

    return render_template("forgot_password.html", reset_url=reset_url, error=error, message=message)


@app.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    reset = get_password_reset(token)
    if not reset:
        flash("The password reset link is invalid or has expired.", "danger")
        return redirect(url_for("forgot_password"))

    expires_at = datetime.fromisoformat(reset["expires_at"])
    if datetime.utcnow() > expires_at:
        consume_password_reset(token)
        flash("The password reset link has expired.", "danger")
        return redirect(url_for("forgot_password"))

    error = None
    if request.method == "POST":
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not password or not confirm_password:
            error = "Please enter and confirm your new password."
        elif len(password) < 6:
            error = "Password must be at least 6 characters."
        elif password != confirm_password:
            error = "Passwords do not match."
        else:
            user_id = consume_password_reset(token)
            if not user_id:
                flash("The password reset link is invalid or has expired.", "danger")
                return redirect(url_for("forgot_password"))

            with get_db() as conn:
                conn.execute(
                    "UPDATE users SET password=? WHERE id=?",
                    (generate_password_hash(password), user_id),
                )
            flash("Your password has been reset. Please login with your new password.", "success")
            return redirect(url_for("login"))

        flash(error, "danger")

    return render_template("reset_password.html", error=error, token=token)


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET" and "user_id" in session:
        return redirect(url_for("dashboard"))

    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not username or not email or not password:
            error = "All fields are required."
        elif len(password) < 6:
            error = "Password must be at least 6 characters."
        elif confirm_password and password != confirm_password:
            error = "Passwords do not match."
        else:
            try:
                with get_db() as conn:
                    conn.execute(
                        "INSERT INTO users(username,email,password) VALUES(?,?,?)",
                        (username, email, generate_password_hash(password)),
                    )
                flash("Account created. Please login.", "success")
                return redirect(url_for("login"))
            except sqlite3.IntegrityError:
                error = "This email is already registered. Please login."

        flash(error, "danger")

    return render_template("register.html", error=error)


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("index"))


@app.route("/dashboard")
@login_required
def dashboard():
    analytics = dashboard_analytics()
    return render_template(
        "dashboard.html",
        username=session.get("user"),
        user=get_dashboard_template_user(),
        analytics=analytics,
        current_profile=get_user_profile(),
        google_client_id=os.environ.get("GOOGLE_CLIENT_ID", ""),
    )


@app.route("/profile/save", methods=["POST"])
@login_required
def save_profile():
    username = request.form.get("username", "").strip()
    email = request.form.get("email", "").strip().lower()
    phone_number = request.form.get("phone_number", request.form.get("phone", "")).strip()
    if username:
        if len(username) > 80:
            flash("Profile name is too long.", "danger")
            return redirect(url_for("dashboard"))
        if email and "@" not in email:
            flash("Please enter a valid email address.", "danger")
            return redirect(url_for("dashboard"))
        if len(phone_number) > 30:
            flash("Phone number is too long.", "danger")
            return redirect(url_for("dashboard"))
        with get_db() as conn:
            if email:
                existing = conn.execute(
                    "SELECT id FROM users WHERE lower(email)=lower(?) AND id<>?",
                    (email, current_user_id()),
                ).fetchone()
                if existing:
                    flash("That email is already used by another account.", "danger")
                    return redirect(url_for("dashboard"))
            conn.execute(
                """
                UPDATE users
                SET username=?,
                    email=COALESCE(NULLIF(?, ''), email),
                    phone_number=?
                WHERE id=?
                """,
                (username, email, phone_number, current_user_id()),
            )
        session["user"] = username
        if email:
            session["email"] = email

    file = request.files.get("profile_photo")
    if file and file.filename:
        ext = Path(secure_filename(file.filename)).suffix.lower()
        if ext not in {".jpg", ".jpeg", ".png"}:
            flash("Only JPG and PNG profile photos are supported.", "danger")
            return redirect(url_for("dashboard"))
        stored_name = f"profile-{current_user_id()}-{uuid.uuid4().hex}{ext}"
        file.save(UPLOAD_DIR / stored_name)
        url = url_for("static", filename=f"uploads/{stored_name}")
        with get_db() as conn:
            conn.execute("UPDATE users SET profile_image=? WHERE id=?", (url, current_user_id()))

    flash("Profile saved.", "success")
    return redirect(url_for("dashboard"))


@app.route("/profile/google/save", methods=["POST"])
@login_required
def save_google_profile():
    google_name = request.form.get("google_name", "").strip()
    google_email = request.form.get("google_email", "").strip().lower()
    google_picture = request.form.get("google_picture", "").strip()

    if google_email and "@" not in google_email:
        flash("Please enter a valid Google email.", "danger")
        return redirect(url_for("dashboard"))

    with get_db() as conn:
        conn.execute(
            """
            UPDATE users
            SET username=COALESCE(?, username),
                profile_image=COALESCE(?, profile_image),
                google_name=?, google_email=?, google_picture=?, google_connected_at=?
            WHERE id=?
            """,
            (
                google_name or None,
                google_picture or None,
                google_name or None,
                google_email or None,
                google_picture or None,
                datetime.utcnow().isoformat(),
                current_user_id(),
            ),
        )
    if google_name:
        session["user"] = google_name

    flash("Google profile details saved.", "success")
    return redirect(url_for("dashboard"))


@app.route("/hotels")
@login_required
def hotels():
    query = request.args.get("query", "").strip()
    location = request.args.get("location", "").strip()
    country = request.args.get("country", "").strip()
    max_price = request.args.get("budget", "").strip()
    min_rating = request.args.get("rating", "").strip()

    filters = {"country": country, "max_price": max_price, "min_rating": min_rating}
    hotels_data = query_catalog("hotels", filters)
    if query:
        q = query.lower()
        hotels_data = [h for h in hotels_data if q in h["name"].lower() or q in h["description"].lower()]
    if location:
        loc = location.lower()
        hotels_data = [h for h in hotels_data if loc in h["city"].lower() or loc in h["address"].lower()]

    for hotel in hotels_data:
        hotel["location"] = f"{hotel['city']}, {hotel['country']}"
        hotel["price"] = f"${hotel['price']:.0f}/night"

    return render_template("hotels.html", hotels=hotels_data, location=location, query=query)


@app.route("/book-hotel", methods=["POST"])
@login_required
def book_hotel():
    hotel_id = request.form.get("hotel_id")
    hotel_name = request.form.get("hotel_name")
    hotel_location = request.form.get("hotel_location")
    hotel_price = request.form.get("hotel_price")
    booking_date = request.form.get("booking_date") or datetime.now().date().isoformat()

    if hotel_id:
        with get_db() as conn:
            hotel = conn.execute("SELECT * FROM hotels WHERE id=?", (hotel_id,)).fetchone()
        if hotel:
            hotel_name = hotel["name"]
            hotel_location = f"{hotel['city']}, {hotel['country']}"
            hotel_price = f"${hotel['price']:.0f}/night"
            details = {"owner": hotel["owner_name"], "address": hotel["address"]}
        else:
            details = {}
    else:
        details = {}

    create_booking(current_user_id(), "hotel", hotel_id, hotel_name, hotel_location, hotel_price, booking_date, details)
    flash("Hotel booking confirmed.", "success")
    return redirect(url_for("booking"))


@app.route("/booking")
@app.route("/bookings")
@login_required
def booking():
    query = request.args.get("q", "") or ""
    with get_db() as conn:
        sql = "SELECT * FROM bookings WHERE user_id=?"
        params = [current_user_id()]
        if query.strip():
            search = f"%{query.strip().lower()}%"
            sql += " AND (LOWER(item_name) LIKE ? OR LOWER(location) LIKE ? OR LOWER(booking_type) LIKE ? OR LOWER(status) LIKE ?)"
            params.extend([search, search, search, search])
        sql += " ORDER BY created_at DESC"
        rows = conn.execute(sql, params).fetchall()

    bookings_data = []
    for row in rows:
        item = booking_payload(row)
        item["hotel_name"] = item["item_name"]
        bookings_data.append(item)

    return render_template("booking.html", bookings=bookings_data, q=query)


@app.route("/restaurants")
@login_required
def restaurants():
    restaurants_data = query_catalog("restaurants", {})
    return render_template("restaurants.html", restaurants=restaurants_data)


@app.route("/rentals")
@login_required
def rentals():
    rentals_data = query_catalog("rentals", {})
    return render_template("rentals.html", rentals=rentals_data)


@app.route("/map")
@app.route("/maps")
@login_required
def map_page():
    return render_template("map.html")


@app.route("/emergency")
@login_required
def emergency():
    return render_template("emergency.html")


@app.route("/chatbot")
@login_required
def chatbot():
    return render_template("chatbot.html")


@app.route("/chat", methods=["POST"])
def legacy_chat_api():
    chat_view = app.view_functions.get("api.chat")
    if chat_view:
        return chat_view()
    return jsonify({"success": True, "reply": "NomadX AI is ready. Please try your message again.", "response": "NomadX AI is ready. Please try your message again."})


@app.route("/tripplanner")
@login_required
def tripplanner():
    return render_template("trip planner.html")


@app.route("/weather")
@login_required
def weather():
    return render_template("weather.html")





@api_bp.route("/hotels")
@api_bp.route("/hotels/search")
@json_login_required
def api_hotels():
    filters = {
        "city": request.args.get("city") or request.args.get("location"),
        "country": request.args.get("country"),
        "max_price": request.args.get("budget"),
        "min_rating": request.args.get("rating"),
    }
    hotels_data = query_catalog("hotels", filters)
    query = (request.args.get("q") or request.args.get("query") or "").strip().lower()
    if query:
        location_hint = infer_location_from_query(query)
        hotels_data = [
            hotel
            for hotel in hotels_data
            if query in hotel["name"].lower()
            or query in hotel["description"].lower()
            or query in hotel["address"].lower()
            or location_hint in hotel["city"].lower()
            or row_matches_query(hotel, query, ["name", "description", "address", "city", "country"])
        ]
    return jsonify({"success": True, "hotels": [enrich_hotel(hotel) for hotel in hotels_data], "count": len(hotels_data)})


@api_bp.route("/hotels/details")
@json_login_required
def api_hotel_details():
    hotel_id = request.args.get("hotel_id") or request.args.get("id")
    name = (request.args.get("name") or request.args.get("q") or "").strip().lower()
    with get_db() as conn:
        if hotel_id:
            hotel = conn.execute("SELECT * FROM hotels WHERE id=?", (hotel_id,)).fetchone()
        elif name:
            hotel = conn.execute(
                "SELECT * FROM hotels WHERE LOWER(name) LIKE ? OR LOWER(city) LIKE ? ORDER BY rating DESC LIMIT 1",
                (f"%{name}%", f"%{name}%"),
            ).fetchone()
        else:
            hotel = None
    if not hotel:
        return jsonify({"success": False, "error": "Hotel not found"}), 404
    return jsonify({"success": True, "hotel": enrich_hotel(hotel)})


@api_bp.route("/hotels/book", methods=["POST"])
@json_login_required
def api_hotel_book():
    data = request.get_json(silent=True) or request.form.to_dict()
    hotel_id = data.get("hotel_id") or data.get("item_id") or data.get("id")
    with get_db() as conn:
        hotel = conn.execute("SELECT * FROM hotels WHERE id=?", (hotel_id,)).fetchone() if hotel_id else None
    if not hotel:
        return jsonify({"success": False, "error": "Hotel not found"}), 404
    booking_id = create_booking(
        current_user_id(),
        "hotel",
        hotel["id"],
        hotel["name"],
        f"{hotel['address']}, {hotel['city']}",
        f"Rs {hotel['price']}/night",
        data.get("booking_date") or datetime.now().date().isoformat(),
        {"owner": hotel["owner_name"], "phone": hotel["owner_phone"], "rooms": hotel["available_rooms"]},
    )
    return jsonify({"success": True, "booking_id": booking_id, "message": "Hotel booking confirmed"})


@api_bp.route("/restaurants")
@api_bp.route("/restaurants/search")
@json_login_required
def api_restaurants():
    filters = {
        "cuisine": request.args.get("cuisine"),
        "city": request.args.get("city") or request.args.get("location"),
        "min_rating": request.args.get("rating"),
    }
    restaurants_data = query_catalog("restaurants", filters)
    price = (request.args.get("price") or "").lower()
    if price:
        restaurants_data = [r for r in restaurants_data if price in r["price_range"].lower()]
    query = (request.args.get("q") or request.args.get("query") or "").strip().lower()
    if query:
        location_hint = infer_location_from_query(query)
        restaurants_data = [
            restaurant
            for restaurant in restaurants_data
            if query in restaurant["name"].lower()
            or query in restaurant["cuisine"].lower()
            or location_hint in restaurant["city"].lower()
            or location_hint in restaurant["location"].lower()
            or row_matches_query(restaurant, query, ["name", "cuisine", "city", "location", "description"])
        ]
    return jsonify({"success": True, "restaurants": [enrich_restaurant(r) for r in restaurants_data], "count": len(restaurants_data)})


@api_bp.route("/restaurants/details")
@json_login_required
def api_restaurant_details():
    restaurant_id = request.args.get("restaurant_id") or request.args.get("id")
    name = (request.args.get("name") or request.args.get("q") or "").strip().lower()
    with get_db() as conn:
        if restaurant_id:
            restaurant = conn.execute("SELECT * FROM restaurants WHERE id=?", (restaurant_id,)).fetchone()
        elif name:
            restaurant = conn.execute(
                "SELECT * FROM restaurants WHERE LOWER(name) LIKE ? OR LOWER(city) LIKE ? OR LOWER(cuisine) LIKE ? ORDER BY rating DESC LIMIT 1",
                (f"%{name}%", f"%{name}%", f"%{name}%"),
            ).fetchone()
        else:
            restaurant = None
    if not restaurant:
        return jsonify({"success": False, "error": "Restaurant not found"}), 404
    return jsonify({"success": True, "restaurant": enrich_restaurant(restaurant)})


@api_bp.route("/restaurants/book", methods=["POST"])
@json_login_required
def api_restaurant_book():
    data = request.get_json(silent=True) or request.form.to_dict()
    restaurant_id = data.get("restaurant_id") or data.get("item_id") or data.get("id")
    with get_db() as conn:
        restaurant = conn.execute("SELECT * FROM restaurants WHERE id=?", (restaurant_id,)).fetchone() if restaurant_id else None
    if not restaurant:
        return jsonify({"success": False, "error": "Restaurant not found"}), 404
    booking_id = create_booking(
        current_user_id(),
        "restaurant",
        restaurant["id"],
        restaurant["name"],
        f"{restaurant['location']}, {restaurant['city']}",
        restaurant["price_range"],
        data.get("booking_date") or datetime.now().date().isoformat(),
        {"phone": restaurant["contact_phone"], "tables": restaurant["available_tables"], "cuisine": restaurant["cuisine"]},
    )
    return jsonify({"success": True, "booking_id": booking_id, "message": "Restaurant table reserved"})


@api_bp.route("/rentals")
@api_bp.route("/rentals/search")
@json_login_required
def api_rentals():
    filters = {
        "city": request.args.get("city") or request.args.get("location"),
        "vehicle_type": request.args.get("type"),
    }
    rentals_data = query_catalog("rentals", filters)
    budget = parse_float_arg("budget")
    if budget is None:
        budget = parse_float_arg("max_price")
    if budget is not None:
        rentals_data = [rental for rental in rentals_data if float(rental["price"]) <= budget]
    query = (request.args.get("q") or request.args.get("query") or "").strip().lower()
    if query:
        location_hint = infer_location_from_query(query)
        rentals_data = [
            rental
            for rental in rentals_data
            if query in rental["vehicle"].lower()
            or query in rental["vehicle_type"].lower()
            or location_hint in rental["city"].lower()
            or location_hint in rental["location"].lower()
            or row_matches_query(rental, query, ["vehicle", "vehicle_type", "city", "location", "description", "pickup_address"])
        ]
    return jsonify({"success": True, "rentals": [enrich_rental(r) for r in rentals_data], "count": len(rentals_data)})


@api_bp.route("/rentals/details")
@json_login_required
def api_rental_details():
    rental_id = request.args.get("rental_id") or request.args.get("id")
    name = (request.args.get("name") or request.args.get("q") or "").strip().lower()
    with get_db() as conn:
        if rental_id:
            rental = conn.execute("SELECT * FROM rentals WHERE id=?", (rental_id,)).fetchone()
        elif name:
            rental = conn.execute(
                "SELECT * FROM rentals WHERE LOWER(vehicle) LIKE ? OR LOWER(city) LIKE ? OR LOWER(vehicle_type) LIKE ? ORDER BY rating DESC LIMIT 1",
                (f"%{name}%", f"%{name}%", f"%{name}%"),
            ).fetchone()
        else:
            rental = None
    if not rental:
        return jsonify({"success": False, "error": "Rental not found"}), 404
    return jsonify({"success": True, "rental": enrich_rental(rental)})


@api_bp.route("/rentals/book", methods=["POST"])
@json_login_required
def api_rental_book():
    data = request.get_json(silent=True) or request.form.to_dict()
    rental_id = data.get("rental_id") or data.get("item_id") or data.get("id")
    with get_db() as conn:
        rental = conn.execute("SELECT * FROM rentals WHERE id=?", (rental_id,)).fetchone() if rental_id else None
    if not rental:
        return jsonify({"success": False, "error": "Rental not found"}), 404
    booking_id = create_booking(
        current_user_id(),
        "rental",
        rental["id"],
        rental["vehicle"],
        rental["pickup_address"],
        f"Rs {rental['price']}/day",
        data.get("booking_date") or datetime.now().date().isoformat(),
        {"owner": rental["rental_agency"], "phone": rental["owner_phone"], "availability": rental["availability"]},
    )
    return jsonify({"success": True, "booking_id": booking_id, "message": "Rental booking confirmed"})


@api_bp.route("/bookings", methods=["GET", "POST"])
@json_login_required
def api_bookings():
    if request.method == "GET":
        with get_db() as conn:
            rows = conn.execute(
                "SELECT * FROM bookings WHERE user_id=? ORDER BY created_at DESC",
                (current_user_id(),),
            ).fetchall()
        return jsonify({"success": True, "bookings": [booking_payload(row) for row in rows]})

    data = request.get_json(silent=True) or request.form.to_dict()
    booking_type = data.get("booking_type", "custom")
    item_id = data.get("item_id")
    item_name = data.get("item_name") or data.get("name") or "NomadX Booking"
    location = data.get("location") or data.get("city") or "To be confirmed"
    price = data.get("price") or "Dynamic"
    booking_date = data.get("booking_date") or data.get("date") or datetime.now().date().isoformat()
    booking_id = create_booking(current_user_id(), booking_type, item_id, item_name, location, price, booking_date, data)
    return jsonify({"success": True, "booking_id": booking_id, "message": "Booking confirmed"})


@api_bp.route("/bookings/<int:booking_id>/cancel", methods=["POST"])
@json_login_required
def api_cancel_booking(booking_id):
    with get_db() as conn:
        cur = conn.execute(
            "UPDATE bookings SET status='Cancelled' WHERE id=? AND user_id=?",
            (booking_id, current_user_id()),
        )
    if cur.rowcount == 0:
        return jsonify({"success": False, "error": "Booking not found"}), 404
    return jsonify({"success": True, "message": "Booking cancelled"})


@api_bp.route("/bookings/<int:booking_id>/ticket")
@login_required
def download_ticket(booking_id):
    with get_db() as conn:
        booking_row = conn.execute(
            "SELECT * FROM bookings WHERE id=? AND user_id=?",
            (booking_id, current_user_id()),
        ).fetchone()
    if not booking_row:
        return jsonify({"success": False, "error": "Booking not found"}), 404

    ticket_path = UPLOAD_DIR / f"ticket-{booking_id}.txt"
    booking_data = booking_payload(booking_row)
    ticket_path.write_text(
        "\n".join(
            [
                "NomadX AI Booking Ticket",
                f"Ticket: {booking_data['ticket_code']}",
                f"Type: {booking_data['booking_type']}",
                f"Name: {booking_data['item_name']}",
                f"Location: {booking_data['location']}",
                f"Date: {booking_data['booking_date']}",
                f"Price: {booking_data['price']}",
                f"Status: {booking_data['status']}",
            ]
        ),
        encoding="utf-8",
    )
    return send_file(ticket_path, as_attachment=True, download_name=f"{booking_data['ticket_code']}.txt")


@api_bp.route("/chat/history")
@json_login_required
def api_chat_history():
    with get_db() as conn:
        rows = conn.execute(
            "SELECT message, reply, created_at FROM chatbot_history WHERE user_id=? ORDER BY created_at DESC LIMIT 25",
            (current_user_id(),),
        ).fetchall()
    return jsonify({"success": True, "history": rows_to_dicts(rows)})


@api_bp.route("/tripplanner", methods=["POST"])
@api_bp.route("/tripplanner/create", methods=["POST"])
@api_bp.route("/trip-plan", methods=["POST"])
@json_login_required
def api_trip_plan():
    data = request.get_json(silent=True) or request.form.to_dict()
    destination = data.get("destination", "").strip()
    travel_date = data.get("travel_date") or data.get("date") or ""
    budget = data.get("budget", "").strip()
    days = data.get("days") or data.get("duration") or "3"
    interests = data.get("interests") or data.get("interest") or "culture, food, sightseeing"
    if not destination or not travel_date or not budget:
        return jsonify({"success": False, "error": "Destination, date, and budget are required"}), 400

    plan = build_trip_plan(destination, travel_date, budget, days=days, interests=interests)
    with get_db() as conn:
        cur = conn.execute(
            "INSERT INTO trip_plans(user_id, destination, travel_date, budget, plan_json) VALUES(?,?,?,?,?)",
            (current_user_id(), destination, travel_date, budget, json.dumps(plan)),
        )
    return jsonify({"success": True, "plan_id": cur.lastrowid, "plan": plan})


@api_bp.route("/tripplanner/suggestions")
@json_login_required
def api_tripplanner_suggestions():
    destination = (request.args.get("destination") or request.args.get("city") or "Bangalore").strip()
    budget = request.args.get("budget", "Medium Budget")
    days = request.args.get("days", "3")
    interests = request.args.get("interests", "culture, food, sightseeing")
    plan = build_trip_plan(destination, datetime.now().date().isoformat(), budget, days=days, interests=interests)
    return jsonify(
        {
            "success": True,
            "suggestions": {
                "hotels": plan["hotels"],
                "restaurants": plan["restaurants"],
                "attractions": plan["attractions"],
                "routes": plan["routes"],
                "weather": plan["weather"],
                "daily_budget": plan["daily_budget"],
            },
        }
    )


@api_bp.route("/weather")
@json_login_required
def api_weather():
    city = request.args.get("city", "Bangalore").strip()
    country = request.args.get("country", "").strip()
    lat = request.args.get("lat")
    lon = request.args.get("lon")
    try:
        weather_data = fetch_openweather_bundle(city=city, country=country, lat=lat, lon=lon)
    except WeatherServiceError as error:
        return jsonify({"success": False, "error": str(error)}), 400
    except requests.RequestException:
        return jsonify({"success": False, "error": "OpenWeather service is temporarily unavailable."}), 503
    return jsonify({"success": True, **weather_data})


@api_bp.route("/forecast")
@json_login_required
def api_forecast():
    city = request.args.get("city", "Bangalore").strip()
    country = request.args.get("country", "").strip()
    lat = request.args.get("lat")
    lon = request.args.get("lon")
    try:
        weather_data = fetch_openweather_bundle(city=city, country=country, lat=lat, lon=lon)
    except WeatherServiceError as error:
        return jsonify({"success": False, "error": str(error)}), 400
    except requests.RequestException:
        return jsonify({"success": False, "error": "OpenWeather forecast service is temporarily unavailable."}), 503
    return jsonify(
        {
            "success": True,
            "location": weather_data["current"]["location"],
            "country": weather_data["current"]["country"],
            "daily": weather_data["daily"],
            "hourly": weather_data["hourly"],
            "alerts": weather_data["alerts"],
        }
    )


@api_bp.route("/location-weather")
@json_login_required
def api_location_weather():
    lat = request.args.get("lat")
    lon = request.args.get("lon")
    if not lat or not lon:
        return jsonify({"success": False, "error": "Latitude and longitude are required."}), 400
    try:
        weather_data = fetch_openweather_bundle(lat=lat, lon=lon)
    except WeatherServiceError as error:
        return jsonify({"success": False, "error": str(error)}), 400
    except requests.RequestException:
        return jsonify({"success": False, "error": "OpenWeather location weather service is temporarily unavailable."}), 503
    return jsonify({"success": True, **weather_data})


@app.route("/search_location")
@api_bp.route("/maps/search")
@json_login_required
def api_map_search():
    query = request.args.get("q", "").strip()
    if not query:
        return jsonify({"success": False, "error": "Search query required"}), 400

    try:
        places = osm_search(query)
    except requests.RequestException:
        places = [{"display_name": query, "lat": "12.9716", "lon": "77.5946", "type": "fallback"}]

    normalized = [
        {
            "name": place.get("display_name", query).split(",")[0],
            "display_name": place.get("display_name", query),
            "lat": float(place.get("lat", 12.9716)),
            "lon": float(place.get("lon", 77.5946)),
            "type": place.get("type", "location"),
            "importance": place.get("importance", 0),
        }
        for place in places[:5]
    ]
    return jsonify({"success": True, "places": normalized})


@api_bp.route("/maps/location", methods=["GET", "POST"])
@json_login_required
def api_maps_location():
    data = request.get_json(silent=True) or {}
    lat = data.get("latitude") or data.get("lat") or request.args.get("lat")
    lon = data.get("longitude") or data.get("lon") or request.args.get("lon")
    try:
        lat = float(lat)
        lon = float(lon)
    except (TypeError, ValueError):
        return jsonify({"success": False, "error": "Valid latitude and longitude are required"}), 400

    if request.method == "POST":
        with get_db() as conn:
            conn.execute(
                """
                INSERT INTO live_locations(user_id, latitude, longitude, accuracy, heading, speed, updated_at)
                VALUES(?,?,?,?,?,?,?)
                """,
                (
                    current_user_id(),
                    lat,
                    lon,
                    data.get("accuracy"),
                    data.get("heading"),
                    data.get("speed"),
                    datetime.utcnow().isoformat(timespec="seconds"),
                ),
            )

    location = reverse_geocode(lat, lon)
    return jsonify({"success": True, "location": {"latitude": lat, "longitude": lon, **location}})


@app.route("/nearby_places")
@api_bp.route("/nearby")
@api_bp.route("/maps/nearby")
@json_login_required
def api_nearby():
    lat = parse_float_arg("lat", 12.9716)
    lon = parse_float_arg("lon", 77.5946)
    kind = request.args.get("type", "places").lower()
    aliases = {"hotel": "hotels", "restaurant": "restaurants", "hospital": "hospitals", "rental": "rentals", "attraction": "attractions"}
    kind = aliases.get(kind, kind)

    places = catalog_nearby(lat, lon, kind)
    try:
        osm_places = [
            place
            for place in (normalize_osm_place(item, lat, lon, kind) for item in overpass_nearby(lat, lon, kind))
            if place
        ]
        places = (osm_places + places)[:12]
    except requests.RequestException:
        if not places:
            places = fallback_nearby(lat, lon, kind)

    places = sorted(places, key=lambda item: item.get("distance_km", 999))[:12]
    return jsonify({"success": True, "places": places, "center": {"lat": lat, "lon": lon}, "category": kind})


@api_bp.route("/nearby-services")
@json_login_required
def api_nearby_services():
    lat = parse_float_arg("lat", 12.9716)
    lon = parse_float_arg("lon", 77.5946)
    requested_country = (request.args.get("country") or "").strip()
    requested_state = (request.args.get("state") or "").strip()
    location = reverse_geocode(lat, lon)
    inferred = infer_region_from_coordinates(lat, lon)
    location_country = location.get("country")
    if location_country == "Live estimate":
        location_country = ""
    country = requested_country or location_country or location.get("country_code") or inferred.get("country")
    state = requested_state or location.get("state") or location.get("district") or inferred.get("state")
    profile = emergency_profile(country=country, state=state, category=request.args.get("category"))
    categories = ["hospitals", "police", "fire", "ambulance"]
    services = {}
    for category in categories:
        lookup = "hospitals" if category == "ambulance" else category
        if lookup == "fire":
            services[category] = fallback_nearby(lat, lon, "fire")
        else:
            try:
                services[category] = [
                    place
                    for place in (normalize_osm_place(item, lat, lon, lookup) for item in overpass_nearby(lat, lon, lookup, radius=5000, limit=6))
                    if place
                ][:6] or fallback_nearby(lat, lon, lookup)
            except requests.RequestException:
                services[category] = fallback_nearby(lat, lon, lookup)
    return jsonify(
        {
            "success": True,
            "center": {"lat": lat, "lon": lon},
            "location": location,
            "services": services,
            "helplines": profile["helplines"],
            "profile": profile,
            "safe_route": "Prefer main roads, lit areas, and share live location until help arrives.",
        }
    )


@api_bp.route("/emergency-number")
@json_login_required
def api_emergency_number():
    # Accept 'country', 'state' or a generic 'q' query parameter
    country = (request.args.get("country") or request.args.get("q") or "").strip()
    state = (request.args.get("state") or request.args.get("region") or "").strip()
    category = (request.args.get("category") or "").strip()
    profile = emergency_profile(country=country, state=state, category=category)
    return jsonify({"success": True, **profile})


@api_bp.route("/route")
@json_login_required
def api_route():
    # Provide simple routing between two points using OSRM public API
    try:
        start_lat = float(request.args.get("start_lat"))
        start_lon = float(request.args.get("start_lon"))
        end_lat = float(request.args.get("end_lat"))
        end_lon = float(request.args.get("end_lon"))
    except (TypeError, ValueError):
        return jsonify({"success": False, "error": "start_lat,start_lon,end_lat,end_lon are required and must be numeric"}), 400

    mode = (request.args.get("mode") or "walking").lower()
    profile = "walking" if mode == "walking" else "driving"
    coords = f"{start_lon},{start_lat};{end_lon},{end_lat}"
    osrm_url = f"https://router.project-osrm.org/route/v1/{profile}/{coords}?overview=false&steps=true&alternatives=true"
    try:
        resp = requests.get(osrm_url, timeout=8)
        resp.raise_for_status()
        data = resp.json()
        routes = data.get("routes", [])
        if not routes:
            return jsonify({"success": False, "error": "No route found"}), 404
        route = routes[0]
        legs = route.get("legs", [])
        steps = []
        for leg in legs:
            for step in leg.get("steps", []):
                steps.append({
                    "distance": step.get("distance"),
                    "duration": step.get("duration"),
                    "name": step.get("name"),
                    "maneuver": step.get("maneuver", {}).get("instruction") if isinstance(step.get("maneuver"), dict) else step.get("maneuver"),
                })

        return jsonify(
            {
                "success": True,
                "profile": profile,
                "distance": route.get("distance"),
                "duration": route.get("duration"),
                "steps": steps,
            }
        )
    except requests.RequestException:
        return jsonify({"success": False, "error": "Routing service unavailable"}), 503


@api_bp.route("/emergency/location")
@json_login_required
def api_emergency_location():
    lat = parse_float_arg("lat")
    lon = parse_float_arg("lon")
    if lat is None or lon is None:
        with get_db() as conn:
            row = conn.execute(
                """
                SELECT latitude, longitude FROM live_locations
                WHERE user_id=? ORDER BY id DESC LIMIT 1
                """,
                (current_user_id(),),
            ).fetchone()
        if row:
            lat = row["latitude"]
            lon = row["longitude"]
        else:
            lat, lon = 12.9716, 77.5946
    location = reverse_geocode(lat, lon)
    return jsonify({"success": True, "location": {"latitude": lat, "longitude": lon, **location}})


@api_bp.route("/emergency/services")
@json_login_required
def api_emergency_services():
    return api_nearby_services()


@api_bp.route("/emergency/helplines")
@json_login_required
def api_emergency_helplines():
    country = (request.args.get("country") or request.args.get("q") or "India").strip()
    state = (request.args.get("state") or "").strip()
    category = (request.args.get("category") or "").strip()
    profile = emergency_profile(country=country, state=state, category=category)
    return jsonify({"success": True, "countries": country_options(), **profile})


@app.route("/route_navigation")
@api_bp.route("/maps/route")
@api_bp.route("/maps/directions")
@json_login_required
def api_map_route():
    try:
        start_lat = float(request.args.get("start_lat"))
        start_lon = float(request.args.get("start_lon"))
        end_lat = float(request.args.get("end_lat"))
        end_lon = float(request.args.get("end_lon"))
    except (TypeError, ValueError):
        return jsonify({"success": False, "error": "Valid start and end coordinates are required"}), 400
    points = [[start_lat, start_lon], [end_lat, end_lon]]
    distance = haversine_km(start_lat, start_lon, end_lat, end_lon)
    eta = max(3, round((distance / (32 if distance < 20 else 55)) * 60))
    mode = "Smart taxi + walking transfer" if distance < 15 else "Car route with highway segments"
    try:
        response = requests.get(
            f"https://router.project-osrm.org/route/v1/driving/{start_lon},{start_lat};{end_lon},{end_lat}",
            params={"overview": "full", "geometries": "geojson", "steps": "false"},
            headers={"User-Agent": "NomadXAI/1.0 (route-navigation)"},
            timeout=8,
        )
        response.raise_for_status()
        routes = response.json().get("routes", [])
        if routes:
            osrm_route = routes[0]
            distance = osrm_route.get("distance", distance * 1000) / 1000
            eta = max(1, round(osrm_route.get("duration", eta * 60) / 60))
            points = [[lat, lon] for lon, lat in osrm_route["geometry"]["coordinates"]]
            mode = "Live OSRM driving route"
    except requests.RequestException:
        pass

    route = {
        "distance_km": round(distance, 2),
        "eta_min": eta,
        "mode": mode,
        "suggestion": "Use the fastest well-lit route and keep offline maps enabled.",
        "points": points,
    }
    return jsonify({"success": True, "route": route})


@app.route("/live_location", methods=["GET", "POST"])
@json_login_required
def live_location():
    if request.method == "POST":
        data = request.get_json(silent=True) or {}
        try:
            lat = float(data.get("latitude"))
            lon = float(data.get("longitude"))
        except (TypeError, ValueError):
            return jsonify({"success": False, "error": "Valid latitude and longitude are required"}), 400

        with get_db() as conn:
            conn.execute(
                """
                INSERT INTO live_locations(user_id, latitude, longitude, accuracy, heading, speed, updated_at)
                VALUES(?,?,?,?,?,?,?)
                """,
                (
                    current_user_id(),
                    lat,
                    lon,
                    data.get("accuracy"),
                    data.get("heading"),
                    data.get("speed"),
                    datetime.utcnow().isoformat(timespec="seconds"),
                ),
            )
        return jsonify({"success": True, "location": {"latitude": lat, "longitude": lon}})

    with get_db() as conn:
        row = conn.execute(
            """
            SELECT latitude, longitude, accuracy, heading, speed, updated_at
            FROM live_locations
            WHERE user_id=?
            ORDER BY id DESC
            LIMIT 1
            """,
            (current_user_id(),),
        ).fetchone()
    return jsonify({"success": True, "location": dict(row) if row else None})


@api_bp.route("/emergency", methods=["POST"])
@json_login_required
def api_emergency():
    data = request.get_json(silent=True) or request.form.to_dict()
    category = data.get("category", "Emergency")
    lat = data.get("latitude")
    lon = data.get("longitude")
    location_text = data.get("location_text", "GPS location pending")
    country = data.get("country")
    state = data.get("state")
    if (not country or not state) and lat and lon:
        try:
            detected = reverse_geocode(float(lat), float(lon))
            country = country or detected.get("country") or detected.get("country_code")
            state = state or detected.get("state") or detected.get("district")
            if location_text == "GPS location pending" and detected.get("display_name"):
                location_text = detected["display_name"]
        except (TypeError, ValueError):
            pass
    contacts = emergency_contacts(category, country=country, state=state)
    profile = emergency_profile(country=country, state=state, category=category)
    with get_db() as conn:
        cur = conn.execute(
            """
            INSERT INTO emergency_requests(user_id, category, latitude, longitude, location_text, status)
            VALUES(?,?,?,?,?,?)
            """,
            (current_user_id(), category, lat, lon, location_text, "Dispatched"),
        )
        conn.execute(
            """
            INSERT INTO emergency_logs(user_id, category, latitude, longitude, location_text, status, contacts_json)
            VALUES(?,?,?,?,?,?,?)
            """,
            (current_user_id(), category, lat, lon, location_text, "Dispatched", json.dumps(contacts)),
        )
    return jsonify(
        {
            "success": True,
            "request_id": cur.lastrowid,
            "status": "Dispatched",
            "contacts": contacts,
            "profile": profile,
            "safe_route": "Move toward well-lit public areas and share your live location.",
        }
    )


@api_bp.route("/dashboard")
@json_login_required
def api_dashboard():
    return jsonify({"success": True, "analytics": dashboard_analytics()})


@api_bp.route("/profile", methods=["GET", "PATCH", "POST"])
@api_bp.route("/profile/update", methods=["PATCH", "POST"])
@json_login_required
def api_profile():
    if request.method == "GET":
        return jsonify({"success": True, "profile": get_user_profile(), "languages": SUPPORTED_LANGUAGES})

    data = request.get_json(silent=True) or {}
    username = (data.get("username") or data.get("name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    phone_number = (data.get("phone_number") or data.get("phone") or "").strip()
    if not username:
        return jsonify({"success": False, "error": "Please enter a profile name"}), 400
    if len(username) > 80:
        return jsonify({"success": False, "error": "Profile name is too long"}), 400
    if email and "@" not in email:
        return jsonify({"success": False, "error": "Please enter a valid email address"}), 400
    if len(phone_number) > 30:
        return jsonify({"success": False, "error": "Phone number is too long"}), 400

    with get_db() as conn:
        if email:
            existing = conn.execute(
                "SELECT id FROM users WHERE lower(email)=lower(?) AND id<>?",
                (email, current_user_id()),
            ).fetchone()
            if existing:
                return jsonify({"success": False, "error": "That email is already used by another account"}), 409
        conn.execute(
            """
            UPDATE users
            SET username=?,
                email=COALESCE(NULLIF(?, ''), email),
                phone_number=?
            WHERE id=?
            """,
            (username, email, phone_number, current_user_id()),
        )
    session["user"] = username
    if email:
        session["email"] = email
    return jsonify({"success": True, "profile": get_user_profile(), "languages": SUPPORTED_LANGUAGES})


@api_bp.route("/settings", methods=["GET", "PATCH", "POST"])
@api_bp.route("/settings/update", methods=["PATCH", "POST"])
@json_login_required
def api_settings():
    if request.method == "GET":
        profile = get_user_profile()
        return jsonify(
            {
                "success": True,
                "settings": {
                    "theme": profile["theme"],
                    "language": profile["language"],
                    "notifications": profile["notifications"],
                    "email_prefs": profile["email_prefs"],
                    "currency": profile["currency"],
                },
                "languages": SUPPORTED_LANGUAGES,
            }
        )

    data = request.get_json(silent=True) or {}
    theme = (data.get("theme") or "dark").strip()
    language = (data.get("language") or "en").strip()
    currency = (data.get("currency") or "USD").strip().upper()
    allowed_themes = {"dark", "light", "auto"}
    allowed_currencies = {"USD", "EUR", "GBP", "INR", "JPY", "AUD"}

    if theme not in allowed_themes:
        return jsonify({"success": False, "error": "Invalid theme selected"}), 400
    if language not in SUPPORTED_LANGUAGE_CODES:
        return jsonify({"success": False, "error": "Invalid language selected"}), 400
    if currency not in allowed_currencies:
        return jsonify({"success": False, "error": "Invalid currency selected"}), 400

    notifications = 1 if bool(data.get("notifications")) else 0
    email_prefs = 1 if bool(data.get("email_prefs")) else 0

    with get_db() as conn:
        conn.execute(
            """
            UPDATE users
            SET theme=?, language=?, notifications=?, email_prefs=?, currency=?
            WHERE id=?
            """,
            (theme, language, notifications, email_prefs, currency, current_user_id()),
        )

    return jsonify({"success": True, "profile": get_user_profile(), "languages": SUPPORTED_LANGUAGES})


@api_bp.route("/profile/google", methods=["POST"])
@api_bp.route("/google/connect", methods=["POST"])
@json_login_required
def api_profile_google():
    data = request.get_json(silent=True) or {}
    google_payload = decode_google_credential(data.get("credential"))
    google_name = (google_payload.get("name") or data.get("google_name") or data.get("name") or "").strip()
    google_email = (google_payload.get("email") or data.get("google_email") or data.get("email") or "").strip().lower()
    google_picture = (google_payload.get("picture") or data.get("google_picture") or data.get("picture") or "").strip()
    google_sub = (google_payload.get("sub") or data.get("google_sub") or "").strip()

    if google_email and "@" not in google_email:
        return jsonify({"success": False, "error": "Please enter a valid Google email"}), 400
    if not any([google_name, google_email, google_picture, google_sub]):
        return jsonify({"success": False, "error": "No Google profile details received"}), 400

    with get_db() as conn:
        conn.execute(
            """
            UPDATE users
            SET username=COALESCE(?, username),
                profile_image=COALESCE(?, profile_image),
                google_name=?, google_email=?, google_picture=?, google_sub=?, google_connected_at=?
            WHERE id=?
            """,
            (
                google_name or None,
                google_picture or None,
                google_name or None,
                google_email or None,
                google_picture or None,
                google_sub or None,
                datetime.utcnow().isoformat(),
                current_user_id(),
            ),
        )
    if google_name:
        session["user"] = google_name

    return jsonify({"success": True, "profile": get_user_profile()})


@api_bp.route("/profile/google", methods=["DELETE"])
@api_bp.route("/google/disconnect", methods=["POST", "DELETE"])
@json_login_required
def api_profile_google_disconnect():
    with get_db() as conn:
        conn.execute(
            """
            UPDATE users
            SET google_name=NULL,
                google_email=NULL,
                google_picture=NULL,
                google_sub=NULL,
                google_connected_at=NULL
            WHERE id=?
            """,
            (current_user_id(),),
        )
    return jsonify({"success": True, "profile": get_user_profile()})


@api_bp.route("/profile/photo", methods=["POST", "DELETE"])
@json_login_required
def api_profile_photo():
    if request.method == "DELETE":
        with get_db() as conn:
            conn.execute("UPDATE users SET profile_image=NULL WHERE id=?", (current_user_id(),))
        return jsonify({"success": True, "message": "Profile photo removed", "profile": get_user_profile()})

    file = request.files.get("file")
    if not file or not file.filename:
        return jsonify({"success": False, "error": "No file uploaded"}), 400
    ext = Path(secure_filename(file.filename)).suffix.lower()
    if ext not in {".jpg", ".jpeg", ".png"}:
        return jsonify({"success": False, "error": "Only image uploads are supported"}), 400
    stored_name = f"profile-{current_user_id()}-{uuid.uuid4().hex}{ext}"
    file.save(UPLOAD_DIR / stored_name)
    url = url_for("static", filename=f"uploads/{stored_name}")
    with get_db() as conn:
        conn.execute("UPDATE users SET profile_image=? WHERE id=?", (url, current_user_id()))
    return jsonify({"success": True, "url": url, "profile": get_user_profile()})


def extract_city(text):
    known = ["dubai", "bangalore", "bengaluru", "mumbai", "goa", "paris", "kyoto", "male", "maldives", "tokyo"]
    for city in known:
        if city in text:
            return "Bangalore" if city == "bengaluru" else city.title()
    markers = [" in ", " near ", " at ", " for "]
    for marker in markers:
        if marker in text:
            candidate = text.split(marker, 1)[1].split("?")[0].split(",")[0].strip()
            words = [word for word in candidate.split() if word.isalpha()]
            if words:
                return " ".join(words[:2]).title()
    return ""


def haversine_km(lat1, lon1, lat2, lon2):
    radius = 6371
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return radius * (2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)))


def format_catalog(items, label_field, extra_field=None, price_field=None, limit=3):
    parts = []
    for item in items[:limit]:
        extra = f", {item[extra_field]}" if extra_field and item.get(extra_field) else ""
        price = f", {item[price_field]}" if price_field and item.get(price_field) else ""
        parts.append(f"{item[label_field]}{extra}{price}")
    return "; ".join(parts)


def ai_chat_reply(message, history=None):
    system_prompt = (
        "You are NomadX AI, a professional realtime travel assistant inside a Flask travel platform. "
        "Answer naturally like ChatGPT while being practical and safety-aware. "
        "Help with hotels, restaurants, rentals, weather, maps, routes, emergencies, tourism, bookings, trip plans, documents, and general questions. "
        "When useful, give concrete options with prices, ratings, locations, route or safety steps. "
        "Use the conversation history to maintain context, avoid repeating yourself, and ask a short follow-up only when needed. "
        "For emergencies such as lost passport, injury, police, hospital, theft, or unsafe travel, give calm step-by-step guidance and recommend local authorities/embassy support."
    )
    recent = history or []
    openai_key = os.environ.get("OPENAI_API_KEY")
    gemini_key = os.environ.get("GEMINI_API_KEY")

    if openai_key and OpenAI:
        try:
            client = OpenAI(api_key=openai_key)
            messages = [{"role": "system", "content": system_prompt}]
            for item in recent[-6:]:
                messages.append({"role": "user", "content": item["message"]})
                messages.append({"role": "assistant", "content": item["reply"]})
            messages.append({"role": "user", "content": message})
            response = client.chat.completions.create(
                model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
                messages=messages,
                temperature=0.5,
                max_tokens=350,
            )
            return response.choices[0].message.content.strip(), "openai"
        except Exception:
            pass

    # If OPENAI key exists but SDK not installed, call OpenAI REST API directly
    if openai_key and not OpenAI:
        try:
            headers = {"Authorization": f"Bearer {openai_key}", "Content-Type": "application/json"}
            model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
            payload = {
                "model": model,
                "messages": (
                    [{"role": "system", "content": system_prompt}]
                    + [
                        entry
                        for item in recent[-6:]
                        for entry in (
                            {"role": "user", "content": item["message"]},
                            {"role": "assistant", "content": item["reply"]},
                        )
                    ]
                    + [{"role": "user", "content": message}]
                ),
                "temperature": 0.5,
                "max_tokens": 350,
            }
            resp = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload, timeout=12)
            resp.raise_for_status()
            data = resp.json()
            text = data["choices"][0]["message"]["content"].strip()
            return text, "openai-rest"
        except Exception:
            pass

    if gemini_key:
        try:
            prompt = "\n".join(
                [system_prompt]
                + [f"User: {item['message']}\nAssistant: {item['reply']}" for item in recent[-6:]]
                + [f"User: {message}\nAssistant:"]
            )
            response = requests.post(
                "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent",
                params={"key": gemini_key},
                json={"contents": [{"parts": [{"text": prompt}]}]},
                timeout=12,
            )
            response.raise_for_status()
            text = response.json()["candidates"][0]["content"]["parts"][0]["text"]
            return text.strip(), "gemini"
        except Exception:
            pass

    return smart_chat_reply(message, history), "local"


def smart_chat_reply(message, history=None):
    text = (message or "").lower()
    history = history or []
    city = extract_city(text)
    if not text:
        return "Ask me about hotels, restaurants, rentals, routes, weather, emergency help, or trip planning."

    if "emergency" in text or "hospital" in text or "police" in text:
        return "Emergency mode is ready. Call 112 for immediate help. I can also help locate nearby hospitals, police stations, fire support, and safer routes if you share or detect your GPS location on Smart Maps."
    if "hotel" in text or "stay" in text:
        hotels_data = query_catalog("hotels", {"city": city}) if city else query_catalog("hotels", {})
        names = ", ".join(f"{h['name']} in {h['city']} from ${h['price']:.0f}/night, rating {h['rating']}, {h['available_rooms']} rooms" for h in hotels_data[:3])
        where = f" near {city}" if city else ""
        return f"Here are live hotel picks{where}: {names}. I would compare rating, room availability, owner contact, address, and nightly price before booking."
    if "restaurant" in text or "food" in text or "cuisine" in text:
        restaurants_data = query_catalog("restaurants", {"city": city}) if city else query_catalog("restaurants", {})
        names = ", ".join(f"{r['name']} ({r['cuisine']}, {r['city']}), rating {r['rating']}, {r['available_tables']} tables" for r in restaurants_data[:3])
        return f"Best restaurant suggestions: {names}. You can reserve a table from the Restaurants page and the booking will be saved."
    if "rental" in text or "car" in text or "bike" in text:
        rentals_data = query_catalog("rentals", {"city": city}) if city else query_catalog("rentals", {})
        names = ", ".join(f"{r['vehicle']} via {r['rental_agency']} at Rs {r['price']:.0f}/day, {r['availability']}" for r in rentals_data[:3])
        return f"Rental options I found: {names}. I can help you choose by city, vehicle type, fuel type, pickup address, and budget."
    if "weather" in text:
        try:
            weather_data = fetch_weather(city=city or "Bangalore")
            return f"Current travel weather for {weather_data['location']}: {weather_data['temperature']}C, {weather_data['condition']}, humidity {weather_data['humidity']}%, wind {weather_data['wind']} km/h. Travel tip: {weather_data['recommendation']}"
        except Exception as error:
            return f"Realtime weather is unavailable right now: {error}. Add a valid OPENWEATHER_API_KEY in .env, then restart the Flask server."
    if "trip" in text or "plan" in text or "itinerary" in text or "budget" in text:
        destination = city or "your destination"
        if city:
            plan = build_trip_plan(city, (datetime.now() + timedelta(days=14)).date().isoformat(), "Medium Budget")
            return f"For {destination}, I suggest {', '.join(plan['attractions'])}. Estimated daily budget is about ${plan['daily_budget']}. Hotels: {format_catalog(plan['hotels'], 'name', 'city')}. Restaurants: {format_catalog(plan['restaurants'], 'name', 'cuisine')}. Weather note: {plan['weather']['recommendation']}"
        return "Tell me your destination, travel date, and budget level. I will generate hotels, restaurants, attractions, smart routes, weather notes, and an estimated daily spend."
    if "map" in text or "route" in text or "nearby" in text:
        return "Smart Maps can detect your GPS location, search any location, drop markers, show nearby hotels, restaurants, hospitals, police stations, tourist attractions, rentals, and fuel stations, plus estimate route distance and ETA."
    if "flight" in text or "airline" in text or "airport" in text:
        return "For flights, compare morning departures for fewer delays, check baggage rules, and keep 2-3 hours for international airport arrival. I can pair flight planning with hotel check-in time and airport-to-hotel route suggestions."
    if "attraction" in text or "tourist" in text or "places" in text:
        destination = city or "your selected city"
        return f"Top tourist ideas for {destination}: heritage walk, local market, viewpoint route, food district, and an evening cultural stop. Open Smart Maps to search the city and fetch nearby attraction markers."
    if history:
        last = history[-1]["message"]
        return f"Building on your last request about '{last}', I can refine this by budget, city, dates, rating, distance, weather, or safety. Ask for hotels, restaurants, rentals, routes, attractions, flights, or emergency support."
    return "I can help you compare stays, reserve restaurants, book rentals, plan routes, estimate budgets, check weather, find attractions, suggest flights, and handle travel emergencies."


def lookup_emergency_number(country=None, state=None):
    return resolve_emergency_number(country=country, state=state)


class WeatherServiceError(Exception):
    pass


def openweather_key():
    key = os.environ.get("OPENWEATHER_API_KEY", "").strip()
    if not key:
        raise WeatherServiceError("OPENWEATHER_API_KEY is missing. Add it to your .env file.")
    return key


def openweather_get(url, params):
    params = {**params, "appid": openweather_key()}
    response = requests.get(url, params=params, timeout=10)
    if response.status_code == 401:
        raise WeatherServiceError("OpenWeather API key is invalid or inactive.")
    if response.status_code == 404:
        raise WeatherServiceError("Weather location was not found.")
    response.raise_for_status()
    return response.json()


def resolve_weather_location(city=None, country=None, lat=None, lon=None):
    if lat not in (None, "") and lon not in (None, ""):
        return {"lat": float(lat), "lon": float(lon), "name": "Current Location", "country": country or ""}

    query = ", ".join(part for part in [city, country] if part).strip()
    if not query:
        raise WeatherServiceError("City, country, or GPS coordinates are required.")

    places = openweather_get(
        "https://api.openweathermap.org/geo/1.0/direct",
        {"q": query, "limit": 1},
    )
    if not places:
        raise WeatherServiceError("Weather location was not found.")
    place = places[0]
    return {
        "lat": float(place["lat"]),
        "lon": float(place["lon"]),
        "name": place.get("name") or city,
        "country": place.get("country") or country or "",
        "state": place.get("state", ""),
    }


def aqi_label(value):
    return {
        1: "Good",
        2: "Fair",
        3: "Moderate",
        4: "Poor",
        5: "Very Poor",
    }.get(value, "Unavailable")


def weather_recommendations(current, air_quality=None, alerts=None):
    temp = current.get("temperature")
    feels_like = current.get("feels_like")
    wind = current.get("wind")
    rain = current.get("rain_probability", 0)
    condition = (current.get("condition") or "").lower()
    aqi = (air_quality or {}).get("aqi")
    suggestions = []

    if rain >= 50 or "rain" in condition or "storm" in condition:
        suggestions.append("Carry an umbrella or rain jacket and allow extra route time.")
    if temp is not None and temp >= 34:
        suggestions.append("Avoid peak afternoon travel, hydrate often, and use shaded routes.")
    if feels_like is not None and feels_like <= 12:
        suggestions.append("Pack warm layers before heading out.")
    if wind is not None and wind >= 35:
        suggestions.append("High wind may affect biking, beach plans, and airport transfers.")
    if aqi and aqi >= 4:
        suggestions.append("Air quality is poor; limit outdoor activity and use a mask if needed.")
    if alerts:
        suggestions.append("Weather alerts are active. Check local advisories before traveling.")
    if not suggestions:
        suggestions.append("Weather looks suitable for sightseeing and local travel.")

    return {
        "summary": " ".join(suggestions),
        "tips": suggestions,
        "best_time_to_travel": "Morning or early evening" if temp and temp >= 31 else "Late morning to evening",
        "traffic_note": "Expect slower traffic during rain or severe alerts." if rain >= 50 or alerts else "No major weather traffic risk detected.",
    }


def normalize_current_weather(data, location, air_quality=None, onecall=None):
    weather = (data.get("weather") or [{}])[0]
    main = data.get("main", {})
    wind = data.get("wind", {})
    sys = data.get("sys", {})
    visibility_m = data.get("visibility")
    rain_probability = 0
    if data.get("rain", {}).get("1h"):
        rain_probability = min(100, round(float(data["rain"]["1h"]) * 20))
    elif onecall and onecall.get("hourly"):
        rain_probability = round((onecall["hourly"][0].get("pop") or 0) * 100)

    current = {
        "location": data.get("name") or location.get("name"),
        "country": sys.get("country") or location.get("country", ""),
        "lat": location["lat"],
        "lon": location["lon"],
        "temperature": round(main.get("temp")) if main.get("temp") is not None else None,
        "feels_like": round(main.get("feels_like")) if main.get("feels_like") is not None else None,
        "condition": weather.get("description", "Unavailable").title(),
        "icon": weather.get("icon"),
        "icon_url": f"https://openweathermap.org/img/wn/{weather.get('icon')}@2x.png" if weather.get("icon") else None,
        "humidity": main.get("humidity"),
        "pressure": main.get("pressure"),
        "wind": round((wind.get("speed") or 0) * 3.6, 1),
        "wind_mps": wind.get("speed"),
        "visibility": round(visibility_m / 1000, 1) if visibility_m is not None else None,
        "sunrise": datetime.fromtimestamp(sys["sunrise"]).strftime("%I:%M %p") if sys.get("sunrise") else None,
        "sunset": datetime.fromtimestamp(sys["sunset"]).strftime("%I:%M %p") if sys.get("sunset") else None,
        "rain_probability": rain_probability,
        "uv_index": onecall.get("current", {}).get("uvi") if onecall else None,
        "air_quality": air_quality,
        "updated_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
    }
    alerts = normalize_weather_alerts(onecall)
    current["alerts"] = alerts
    current["recommendation"] = weather_recommendations(current, air_quality=air_quality, alerts=alerts)["summary"]
    current["recommendations"] = weather_recommendations(current, air_quality=air_quality, alerts=alerts)
    return current


def normalize_air_quality(data):
    item = (data.get("list") or [{}])[0]
    main = item.get("main", {})
    components = item.get("components", {})
    aqi = main.get("aqi")
    return {
        "aqi": aqi,
        "label": aqi_label(aqi),
        "components": components,
    }


def normalize_weather_alerts(onecall):
    alerts = []
    if not onecall:
        return alerts
    for alert in onecall.get("alerts", [])[:5]:
        alerts.append(
            {
                "event": alert.get("event"),
                "description": alert.get("description"),
                "start": datetime.fromtimestamp(alert["start"]).isoformat() if alert.get("start") else None,
                "end": datetime.fromtimestamp(alert["end"]).isoformat() if alert.get("end") else None,
                "sender": alert.get("sender_name"),
            }
        )
    return alerts


def normalize_forecast(data, onecall=None):
    hourly = []
    for item in (data.get("list") or [])[:16]:
        weather = (item.get("weather") or [{}])[0]
        hourly.append(
            {
                "time": item.get("dt_txt"),
                "hour": datetime.fromtimestamp(item["dt"]).strftime("%I %p") if item.get("dt") else item.get("dt_txt"),
                "temperature": round(item.get("main", {}).get("temp")) if item.get("main", {}).get("temp") is not None else None,
                "condition": weather.get("description", "").title(),
                "icon": weather.get("icon"),
                "rain_probability": round((item.get("pop") or 0) * 100),
                "wind": round((item.get("wind", {}).get("speed") or 0) * 3.6, 1),
            }
        )

    daily_map = {}
    for item in data.get("list", []):
        dt = datetime.fromtimestamp(item["dt"])
        key = dt.date().isoformat()
        weather = (item.get("weather") or [{}])[0]
        day = daily_map.setdefault(
            key,
            {
                "date": key,
                "day": dt.strftime("%A"),
                "min_temp": item["main"]["temp"],
                "max_temp": item["main"]["temp"],
                "condition": weather.get("description", "").title(),
                "icon": weather.get("icon"),
                "rain_probability": 0,
            },
        )
        day["min_temp"] = min(day["min_temp"], item["main"]["temp"])
        day["max_temp"] = max(day["max_temp"], item["main"]["temp"])
        day["rain_probability"] = max(day["rain_probability"], round((item.get("pop") or 0) * 100))

    daily = list(daily_map.values())
    for day in daily:
        day["min_temp"] = round(day["min_temp"])
        day["max_temp"] = round(day["max_temp"])
        day["temp"] = day["max_temp"]

    if onecall and onecall.get("daily"):
        daily = [
            {
                "date": datetime.fromtimestamp(item["dt"]).date().isoformat(),
                "day": datetime.fromtimestamp(item["dt"]).strftime("%A"),
                "min_temp": round(item.get("temp", {}).get("min")),
                "max_temp": round(item.get("temp", {}).get("max")),
                "temp": round(item.get("temp", {}).get("day")),
                "condition": (item.get("weather") or [{}])[0].get("description", "").title(),
                "icon": (item.get("weather") or [{}])[0].get("icon"),
                "rain_probability": round((item.get("pop") or 0) * 100),
            }
            for item in onecall["daily"][:7]
        ]

    return {"hourly": hourly, "daily": daily[:7]}


OPEN_METEO_CODES = {
    0: "Clear Sky",
    1: "Mainly Clear",
    2: "Partly Cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing Rime Fog",
    51: "Light Drizzle",
    53: "Moderate Drizzle",
    55: "Dense Drizzle",
    61: "Slight Rain",
    63: "Moderate Rain",
    65: "Heavy Rain",
    71: "Slight Snow",
    73: "Moderate Snow",
    75: "Heavy Snow",
    80: "Rain Showers",
    81: "Moderate Rain Showers",
    82: "Violent Rain Showers",
    95: "Thunderstorm",
    96: "Thunderstorm With Hail",
    99: "Severe Thunderstorm With Hail",
}


def open_meteo_code_label(code):
    return OPEN_METEO_CODES.get(int(code or 0), "Weather Data")


def open_meteo_icon(code, is_day=1):
    code = int(code or 0)
    day = bool(is_day)
    if code in {0, 1}:
        return "01d" if day else "01n"
    if code in {2, 3, 45, 48}:
        return "03d" if day else "03n"
    if code in {51, 53, 55, 61, 63, 65, 80, 81, 82}:
        return "10d" if day else "10n"
    if code in {71, 73, 75}:
        return "13d" if day else "13n"
    if code in {95, 96, 99}:
        return "11d" if day else "11n"
    return "02d" if day else "02n"


def resolve_open_meteo_location(city=None, country=None, lat=None, lon=None):
    if lat not in (None, "") and lon not in (None, ""):
        return {"lat": float(lat), "lon": float(lon), "name": "Current Location", "country": country or ""}

    query = ", ".join(part for part in [city, country] if part).strip()
    if not query:
        raise WeatherServiceError("Please enter a city or allow GPS location.")
    response = requests.get(
        "https://geocoding-api.open-meteo.com/v1/search",
        params={"name": query, "count": 1, "language": "en", "format": "json"},
        timeout=10,
    )
    response.raise_for_status()
    results = response.json().get("results") or []
    if not results:
        raise WeatherServiceError(f"No realtime weather location found for '{query}'. Try city + country, for example 'Bangalore, India'.")
    place = results[0]
    return {
        "lat": float(place["latitude"]),
        "lon": float(place["longitude"]),
        "name": place.get("name") or city,
        "country": place.get("country_code") or place.get("country") or country or "",
        "state": place.get("admin1", ""),
    }


def fetch_open_meteo_bundle(city="Bangalore", country=None, lat=None, lon=None):
    location = resolve_open_meteo_location(city=city, country=country, lat=lat, lon=lon)
    cache_key = f"weather:openmeteo:v1:{location['lat']:.4f},{location['lon']:.4f}"
    try:
        with get_db() as conn:
            row = conn.execute("SELECT payload_json, updated_at FROM weather_cache WHERE cache_key=?", (cache_key,)).fetchone()
        if row and datetime.utcnow() - datetime.fromisoformat(row["updated_at"]) < timedelta(minutes=8):
            return json.loads(row["payload_json"])
    except Exception:
        pass

    forecast_response = requests.get(
        "https://api.open-meteo.com/v1/forecast",
        params={
            "latitude": location["lat"],
            "longitude": location["lon"],
            "timezone": "auto",
            "current": "temperature_2m,relative_humidity_2m,apparent_temperature,is_day,precipitation,weather_code,pressure_msl,wind_speed_10m",
            "hourly": "temperature_2m,relative_humidity_2m,apparent_temperature,precipitation_probability,weather_code,wind_speed_10m,pressure_msl,visibility,uv_index",
            "daily": "weather_code,temperature_2m_max,temperature_2m_min,sunrise,sunset,precipitation_probability_max,uv_index_max",
            "forecast_days": 7,
        },
        timeout=10,
    )
    forecast_response.raise_for_status()
    data = forecast_response.json()

    aq_label = "Unavailable"
    aq_value = None
    aq_components = {}
    try:
        aq_response = requests.get(
            "https://air-quality-api.open-meteo.com/v1/air-quality",
            params={"latitude": location["lat"], "longitude": location["lon"], "hourly": "us_aqi,pm2_5,pm10", "timezone": "auto"},
            timeout=10,
        )
        aq_response.raise_for_status()
        aq = aq_response.json().get("hourly", {})
        aq_value = (aq.get("us_aqi") or [None])[0]
        aq_components = {"pm2_5": (aq.get("pm2_5") or [None])[0], "pm10": (aq.get("pm10") or [None])[0]}
        if aq_value is not None:
            aq_label = "Good" if aq_value <= 50 else "Moderate" if aq_value <= 100 else "Poor" if aq_value <= 150 else "Very Poor"
    except Exception:
        pass

    current_raw = data.get("current", {})
    hourly_raw = data.get("hourly", {})
    daily_raw = data.get("daily", {})
    current_code = current_raw.get("weather_code")
    icon = open_meteo_icon(current_code, current_raw.get("is_day", 1))
    visibility_values = hourly_raw.get("visibility") or []
    rain_values = hourly_raw.get("precipitation_probability") or []
    uv_values = hourly_raw.get("uv_index") or []
    alerts = []

    current = {
        "location": location["name"],
        "country": location.get("country", ""),
        "lat": location["lat"],
        "lon": location["lon"],
        "temperature": round(current_raw.get("temperature_2m")) if current_raw.get("temperature_2m") is not None else None,
        "feels_like": round(current_raw.get("apparent_temperature")) if current_raw.get("apparent_temperature") is not None else None,
        "condition": open_meteo_code_label(current_code),
        "icon": icon,
        "icon_url": f"https://openweathermap.org/img/wn/{icon}@2x.png",
        "humidity": current_raw.get("relative_humidity_2m"),
        "pressure": round(current_raw.get("pressure_msl")) if current_raw.get("pressure_msl") is not None else None,
        "wind": current_raw.get("wind_speed_10m"),
        "wind_mps": round((current_raw.get("wind_speed_10m") or 0) / 3.6, 2),
        "visibility": round((visibility_values[0] or 0) / 1000, 1) if visibility_values else None,
        "sunrise": (daily_raw.get("sunrise") or [None])[0],
        "sunset": (daily_raw.get("sunset") or [None])[0],
        "rain_probability": rain_values[0] if rain_values else 0,
        "uv_index": round(uv_values[0], 1) if uv_values and uv_values[0] is not None else None,
        "air_quality": {"aqi": aq_value, "label": aq_label, "components": aq_components},
        "alerts": alerts,
        "updated_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
    }
    current["recommendations"] = weather_recommendations(current, air_quality=current["air_quality"], alerts=alerts)
    current["recommendation"] = current["recommendations"]["summary"]

    hourly = []
    for index, time_value in enumerate((hourly_raw.get("time") or [])[:24]):
        code = (hourly_raw.get("weather_code") or [None])[index]
        hourly.append(
            {
                "time": time_value,
                "hour": time_value.split("T")[-1],
                "temperature": round((hourly_raw.get("temperature_2m") or [None])[index]),
                "condition": open_meteo_code_label(code),
                "icon": open_meteo_icon(code),
                "rain_probability": (hourly_raw.get("precipitation_probability") or [0])[index],
                "wind": (hourly_raw.get("wind_speed_10m") or [None])[index],
            }
        )

    daily = []
    for index, date_value in enumerate((daily_raw.get("time") or [])[:7]):
        code = (daily_raw.get("weather_code") or [None])[index]
        max_temp = round((daily_raw.get("temperature_2m_max") or [None])[index])
        min_temp = round((daily_raw.get("temperature_2m_min") or [None])[index])
        daily.append(
            {
                "date": date_value,
                "day": datetime.fromisoformat(date_value).strftime("%A"),
                "min_temp": min_temp,
                "max_temp": max_temp,
                "temp": max_temp,
                "condition": open_meteo_code_label(code),
                "icon": open_meteo_icon(code),
                "rain_probability": (daily_raw.get("precipitation_probability_max") or [0])[index],
            }
        )

    payload = {
        "current": current,
        "weather": current,
        "forecast": daily,
        "daily": daily,
        "hourly": hourly,
        "air_quality": current["air_quality"],
        "alerts": alerts,
        "recommendations": current["recommendations"],
        "source": "Open-Meteo realtime fallback",
        "one_call_available": False,
    }

    try:
        with get_db() as conn:
            conn.execute(
                """
                INSERT INTO weather_cache(cache_key, payload_json, updated_at)
                VALUES(?,?,?)
                ON CONFLICT(cache_key) DO UPDATE SET payload_json=excluded.payload_json, updated_at=excluded.updated_at
                """,
                (cache_key, json.dumps(payload), datetime.utcnow().isoformat(timespec="seconds")),
            )
    except Exception:
        pass
    return payload

def fetch_openweather_bundle(city="Bangalore", country=None, lat=None, lon=None):
    if not os.environ.get("OPENWEATHER_API_KEY", "").strip():
        return fetch_open_meteo_bundle(city=city, country=country, lat=lat, lon=lon)

    location = resolve_weather_location(city=city, country=country, lat=lat, lon=lon)
    cache_key = f"weather:openweather:v3:{location['lat']:.4f},{location['lon']:.4f}"
    try:
        with get_db() as conn:
            row = conn.execute("SELECT payload_json, updated_at FROM weather_cache WHERE cache_key=?", (cache_key,)).fetchone()
        if row and datetime.utcnow() - datetime.fromisoformat(row["updated_at"]) < timedelta(minutes=8):
            return json.loads(row["payload_json"])
    except Exception:
        pass

    try:
        current_data = openweather_get(
            "https://api.openweathermap.org/data/2.5/weather",
            {"lat": location["lat"], "lon": location["lon"], "units": "metric"},
        )
        forecast_data = openweather_get(
            "https://api.openweathermap.org/data/2.5/forecast",
            {"lat": location["lat"], "lon": location["lon"], "units": "metric"},
        )
        air_quality = normalize_air_quality(
            openweather_get(
                "https://api.openweathermap.org/data/2.5/air_pollution",
                {"lat": location["lat"], "lon": location["lon"]},
            )
        )
    except WeatherServiceError:
        return fetch_open_meteo_bundle(city=city, country=country, lat=lat, lon=lon)

    onecall = None
    try:
        onecall = openweather_get(
            "https://api.openweathermap.org/data/3.0/onecall",
            {"lat": location["lat"], "lon": location["lon"], "units": "metric", "exclude": "minutely"},
        )
    except Exception:
        onecall = None

    current = normalize_current_weather(current_data, location, air_quality=air_quality, onecall=onecall)
    forecast = normalize_forecast(forecast_data, onecall=onecall)
    payload = {
        "current": current,
        "weather": current,
        "forecast": forecast["daily"],
        "daily": forecast["daily"],
        "hourly": forecast["hourly"],
        "air_quality": air_quality,
        "alerts": current["alerts"],
        "recommendations": current["recommendations"],
        "source": "OpenWeatherMap",
        "one_call_available": bool(onecall),
    }

    try:
        with get_db() as conn:
            conn.execute(
                """
                INSERT INTO weather_cache(cache_key, payload_json, updated_at)
                VALUES(?,?,?)
                ON CONFLICT(cache_key) DO UPDATE SET payload_json=excluded.payload_json, updated_at=excluded.updated_at
                """,
                (cache_key, json.dumps(payload), datetime.utcnow().isoformat(timespec="seconds")),
            )
    except Exception:
        pass
    return payload


def build_trip_plan(destination, travel_date, budget, days=3, interests="culture, food, sightseeing"):
    city = destination.split(",")[0].strip()
    hotels_data = query_catalog("hotels", {"city": city}) or query_catalog("hotels", {})
    restaurants_data = query_catalog("restaurants", {"city": city}) or query_catalog("restaurants", {})
    try:
        weather_data = fetch_weather(city=city)
    except Exception as error:
        weather_data = {
            "location": city,
            "country": "",
            "temperature": None,
            "condition": "Realtime weather unavailable",
            "humidity": None,
            "wind": None,
            "forecast": [],
            "recommendation": f"Configure OPENWEATHER_API_KEY for live weather. Current issue: {error}",
        }
    budget_multiplier = {"Low Budget": 0.75, "Medium Budget": 1.0, "Luxury": 1.8}.get(budget, 1.0)
    daily_estimate = round((hotels_data[0]["price"] if hotels_data else 120) * budget_multiplier + 65, 2)
    try:
        day_count = max(1, min(14, int(days)))
    except (TypeError, ValueError):
        day_count = 3
    interest_list = [item.strip() for item in str(interests).split(",") if item.strip()] or ["culture", "food", "sightseeing"]
    attractions = [
        f"{city} heritage walk",
        f"{city} viewpoint and skyline route",
        f"Local market and food district in {city}",
    ]
    itinerary = [
        {
            "day": day,
            "morning": f"{city} {interest_list[(day - 1) % len(interest_list)]} trail",
            "afternoon": attractions[(day - 1) % len(attractions)],
            "evening": restaurants_data[(day - 1) % len(restaurants_data)]["name"] if restaurants_data else f"{city} local dinner zone",
        }
        for day in range(1, day_count + 1)
    ]
    return {
        "destination": destination,
        "travel_date": travel_date,
        "budget": budget,
        "days": day_count,
        "interests": interest_list,
        "hotels": hotels_data[:3],
        "restaurants": restaurants_data[:3],
        "attractions": attractions,
        "itinerary": itinerary,
        "routes": ["Airport/rail arrival to hotel", "Hotel to attractions loop", "Evening dining route"],
        "daily_budget": daily_estimate,
        "weather": weather_data,
        "recommendations": [
            "Book hotels early for better realtime pricing.",
            weather_data["recommendation"],
            "Keep emergency contacts and offline maps ready before departure.",
        ],
    }


def fetch_weather(city="Bangalore", lat=None, lon=None):
    return fetch_openweather_bundle(city=city, lat=lat, lon=lon)["current"]


def emergency_contacts(category, country=None, state=None):
    return emergency_contacts_for_category(category=category, country=country, state=state)


def dashboard_analytics():
    with get_db() as conn:
        total_bookings = conn.execute("SELECT COUNT(*) FROM bookings WHERE user_id=?", (current_user_id(),)).fetchone()[0]
        upcoming = conn.execute(
            "SELECT COUNT(*) FROM bookings WHERE user_id=? AND status='Confirmed'",
            (current_user_id(),),
        ).fetchone()[0]
        trip_plans = conn.execute("SELECT COUNT(*) FROM trip_plans WHERE user_id=?", (current_user_id(),)).fetchone()[0]
        saved = total_bookings + trip_plans
    return {
        "total_bookings": total_bookings,
        "upcoming_trips": upcoming,
        "saved_destinations": saved,
        "trip_plans": trip_plans,
    }


@app.errorhandler(404)
def page_not_found(error):
    return "<h1>404 - Page not found</h1><p>NomadX AI could not find this route.</p>", 404


@app.errorhandler(500)
def internal_server_error(error):
    return "<h1>500 - Server error</h1><p>NomadX AI hit an unexpected backend issue.</p>", 500

# Register blueprints after all routes are declared to avoid Flask setup errors
app.register_blueprint(api_bp)
try:
    from nomadx_backend import init_backend

    NOMADX_PRODUCTION_BACKEND_ENABLED = init_backend(app)
except Exception as exc:
    NOMADX_PRODUCTION_BACKEND_ENABLED = False
    app.logger.warning("NomadX production backend was not initialized: %s", exc)

@app.route("/api/weather/current")
def api_weather_current():
    city = request.args.get("city")
    lat = request.args.get("lat")
    lon = request.args.get("lon")

    try:
        data = fetch_openweather_bundle(
            city=city,
            lat=lat,
            lon=lon
        )
        return jsonify(data)

    except Exception as e:
        return jsonify({"error": str(e)}), 500



if __name__ == "__main__":
    if NOMADX_PRODUCTION_BACKEND_ENABLED:
        from nomadx_backend.extensions import socketio

        socketio.run(app, debug=app.debug, host="0.0.0.0", port=int(os.environ.get("PORT", "5000")))
    else:
        app.run(debug=True, use_reloader=False)
# Add this to your Flask routes file

from flask import jsonify, request
import re
# Add this to your Flask routes file (app.py or routes.py)

from flask import jsonify, request, render_template

# ================= EMERGENCY DATABASE =================
EMERGENCY_DATABASE = [
    # INDIA
    {"id": 1, "country": "India", "state": "Karnataka", "city": "Bengaluru", 
     "police": "100", "ambulance": "102", "fire": "101", "women": "1091", 
     "child": "1098", "tourist": "1363", "disaster": "1070", "medical": "108"},
    
    {"id": 2, "country": "India", "state": "Karnataka", "city": "Mysuru",
     "police": "100", "ambulance": "102", "fire": "101", "women": "1091",
     "child": "1098", "tourist": "1363", "disaster": "1070", "medical": "108"},
    
    {"id": 3, "country": "India", "state": "Maharashtra", "city": "Mumbai",
     "police": "100", "ambulance": "102", "fire": "101", "women": "1091",
     "child": "1098", "tourist": "1363", "disaster": "1070", "medical": "108"},
    
    {"id": 4, "country": "India", "state": "Delhi", "city": "New Delhi",
     "police": "100", "ambulance": "102", "fire": "101", "women": "1091",
     "child": "1098", "tourist": "1363", "disaster": "1070", "medical": "108"},
    
    {"id": 5, "country": "India", "state": "Tamil Nadu", "city": "Chennai",
     "police": "100", "ambulance": "102", "fire": "101", "women": "1091",
     "child": "1098", "tourist": "1363", "disaster": "1070", "medical": "108"},
    
    {"id": 6, "country": "India", "state": "Kerala", "city": "Kochi",
     "police": "100", "ambulance": "102", "fire": "101", "women": "1091",
     "child": "1098", "tourist": "1363", "disaster": "1070", "medical": "108"},
    
    {"id": 7, "country": "India", "state": "Rajasthan", "city": "Jaipur",
     "police": "100", "ambulance": "102", "fire": "101", "women": "1091",
     "child": "1098", "tourist": "1363", "disaster": "1070", "medical": "108"},
    
    {"id": 8, "country": "India", "state": "Goa", "city": "Panaji",
     "police": "100", "ambulance": "102", "fire": "101", "women": "1091",
     "child": "1098", "tourist": "1363", "disaster": "1070", "medical": "108"},

    # USA
    {"id": 9, "country": "USA", "state": "California", "city": "Los Angeles",
     "police": "911", "ambulance": "911", "fire": "911", "women": "1-800-799-7233",
     "child": "1-800-422-4453", "tourist": "1-888-407-4747", "disaster": "1-800-621-FEMA",
     "medical": "911"},
    
    {"id": 10, "country": "USA", "state": "California", "city": "San Francisco",
     "police": "911", "ambulance": "911", "fire": "911", "women": "1-800-799-7233",
     "child": "1-800-422-4453", "tourist": "1-888-407-4747", "disaster": "1-800-621-FEMA",
     "medical": "911"},
    
    {"id": 11, "country": "USA", "state": "New York", "city": "New York City",
     "police": "911", "ambulance": "911", "fire": "911", "women": "1-800-799-7233",
     "child": "1-800-422-4453", "tourist": "1-888-407-4747", "disaster": "1-800-621-FEMA",
     "medical": "911"},

    # UK
    {"id": 12, "country": "UK", "state": "England", "city": "London",
     "police": "999", "ambulance": "999", "fire": "999", "women": "0808 2000 247",
     "child": "0800 1111", "tourist": "+44 20 7008 1500", "disaster": "0800 111 222",
     "medical": "999"},

    # JAPAN
    {"id": 13, "country": "Japan", "state": "Tokyo", "city": "Tokyo",
     "police": "110", "ambulance": "119", "fire": "119", "women": "0120-279-338",
     "child": "0120-99-7777", "tourist": "+81 3 3434 5678", "disaster": "0120-345-678",
     "medical": "119"},

    # FRANCE
    {"id": 14, "country": "France", "state": "Île-de-France", "city": "Paris",
     "police": "17", "ambulance": "15", "fire": "18", "women": "3919",
     "child": "119", "tourist": "+33 1 4567 8901", "disaster": "112",
     "medical": "15"},

    # GERMANY
    {"id": 15, "country": "Germany", "state": "Berlin", "city": "Berlin",
     "police": "110", "ambulance": "112", "fire": "112", "women": "0800 116 016",
     "child": "0800 111 0 333", "tourist": "+49 30 4567 8901", "disaster": "112",
     "medical": "112"},

    # UAE
    {"id": 16, "country": "UAE", "state": "Dubai", "city": "Dubai",
     "police": "999", "ambulance": "998", "fire": "997", "women": "800 111",
     "child": "800 555", "tourist": "+971 4 4567 8901", "disaster": "800 222",
     "medical": "998"},

    # AUSTRALIA
    {"id": 17, "country": "Australia", "state": "New South Wales", "city": "Sydney",
     "police": "000", "ambulance": "000", "fire": "000", "women": "1800 656 4636",
     "child": "1800 551 800", "tourist": "+61 2 4567 8901", "disaster": "132 500",
     "medical": "000"},

    # CANADA
    {"id": 18, "country": "Canada", "state": "Ontario", "city": "Toronto",
     "police": "911", "ambulance": "911", "fire": "911", "women": "1-800-363-9010",
     "child": "1-800-668-6868", "tourist": "+1 416 4567 8901", "disaster": "1-800-267-0453",
     "medical": "911"},

    # SINGAPORE
    {"id": 19, "country": "Singapore", "state": "Singapore", "city": "Singapore",
     "police": "999", "ambulance": "995", "fire": "995", "women": "1800 777 5555",
     "child": "1800 777 5555", "tourist": "+65 4567 8901", "disaster": "995",
     "medical": "995"},

    # CHINA
    {"id": 20, "country": "China", "state": "Beijing", "city": "Beijing",
     "police": "110", "ambulance": "120", "fire": "119", "women": "12338",
     "child": "12355", "tourist": "+86 10 4567 8901", "disaster": "119",
     "medical": "120"},

    # BRAZIL
    {"id": 21, "country": "Brazil", "state": "São Paulo", "city": "São Paulo",
     "police": "190", "ambulance": "192", "fire": "193", "women": "180",
     "child": "100", "tourist": "+55 11 4567 8901", "disaster": "199",
     "medical": "192"},

    # SOUTH AFRICA
    {"id": 22, "country": "South Africa", "state": "Gauteng", "city": "Johannesburg",
     "police": "10111", "ambulance": "10177", "fire": "10177", "women": "0800 150 150",
     "child": "0800 055 555", "tourist": "+27 11 4567 8901", "disaster": "112",
     "medical": "10177"},

    # THAILAND
    {"id": 23, "country": "Thailand", "state": "Bangkok", "city": "Bangkok",
     "police": "191", "ambulance": "1669", "fire": "199", "women": "1300",
     "child": "1300", "tourist": "+66 2 4567 8901", "disaster": "1784",
     "medical": "1669"},

    # ITALY
    {"id": 24, "country": "Italy", "state": "Lazio", "city": "Rome",
     "police": "113", "ambulance": "118", "fire": "115", "women": "1522",
     "child": "114", "tourist": "+39 06 4567 8901", "disaster": "112",
     "medical": "118"},

    # SPAIN
    {"id": 25, "country": "Spain", "state": "Madrid", "city": "Madrid",
     "police": "091", "ambulance": "112", "fire": "080", "women": "016",
     "child": "116 111", "tourist": "+34 91 4567 8901", "disaster": "112",
     "medical": "112"},

    # MEXICO
    {"id": 26, "country": "Mexico", "state": "Mexico City", "city": "Mexico City",
     "police": "911", "ambulance": "911", "fire": "911", "women": "800 822 4460",
     "child": "800 822 4460", "tourist": "+52 55 4567 8901", "disaster": "911",
     "medical": "911"},

    # EGYPT
    {"id": 27, "country": "Egypt", "state": "Cairo", "city": "Cairo",
     "police": "122", "ambulance": "123", "fire": "180", "women": "151",
     "child": "16000", "tourist": "+20 2 4567 8901", "disaster": "112",
     "medical": "123"},

    # INDONESIA
    {"id": 28, "country": "Indonesia", "state": "Jakarta", "city": "Jakarta",
     "police": "110", "ambulance": "118", "fire": "113", "women": "129",
     "child": "1500 555", "tourist": "+62 21 4567 8901", "disaster": "112",
     "medical": "118"},

    # MALAYSIA
    {"id": 29, "country": "Malaysia", "state": "Kuala Lumpur", "city": "Kuala Lumpur",
     "police": "999", "ambulance": "999", "fire": "994", "women": "15999",
     "child": "15999", "tourist": "+60 3 4567 8901", "disaster": "999",
     "medical": "999"},

    # NEW ZEALAND
    {"id": 30, "country": "New Zealand", "state": "Auckland", "city": "Auckland",
     "police": "111", "ambulance": "111", "fire": "111", "women": "0800 733 843",
     "child": "0800 543 754", "tourist": "+64 9 4567 8901", "disaster": "111",
     "medical": "111"},

    # TURKEY
    {"id": 31, "country": "Turkey", "state": "Istanbul", "city": "Istanbul",
     "police": "155", "ambulance": "112", "fire": "110", "women": "183",
     "child": "112", "tourist": "+90 212 4567 8901", "disaster": "112",
     "medical": "112"},

    # NETHERLANDS
    {"id": 32, "country": "Netherlands", "state": "Amsterdam", "city": "Amsterdam",
     "police": "112", "ambulance": "112", "fire": "112", "women": "0800 2000",
     "child": "116 111", "tourist": "+31 20 4567 8901", "disaster": "112",
     "medical": "112"},

    # SWITZERLAND
    {"id": 33, "country": "Switzerland", "state": "Bern", "city": "Bern",
     "police": "117", "ambulance": "144", "fire": "118", "women": "143",
     "child": "147", "tourist": "+41 31 4567 8901", "disaster": "112",
     "medical": "144"},

    # PAKISTAN
    {"id": 34, "country": "Pakistan", "state": "Islamabad", "city": "Islamabad",
     "police": "15", "ambulance": "115", "fire": "16", "women": "1090",
     "child": "1121", "tourist": "+92 51 4567 8901", "disaster": "1122",
     "medical": "115"},

    # BANGLADESH
    {"id": 35, "country": "Bangladesh", "state": "Dhaka", "city": "Dhaka",
     "police": "999", "ambulance": "999", "fire": "999", "women": "109",
     "child": "1098", "tourist": "+880 2 4567 8901", "disaster": "999",
     "medical": "999"},

    # SRI LANKA
    {"id": 36, "country": "Sri Lanka", "state": "Colombo", "city": "Colombo",
     "police": "119", "ambulance": "110", "fire": "110", "women": "193",
     "child": "192", "tourist": "+94 11 4567 8901", "disaster": "112",
     "medical": "110"},

    # NEPAL
    {"id": 37, "country": "Nepal", "state": "Kathmandu", "city": "Kathmandu",
     "police": "100", "ambulance": "102", "fire": "101", "women": "1145",
     "child": "104", "tourist": "+977 1 4567 8901", "disaster": "112",
     "medical": "102"},

    # VIETNAM
    {"id": 38, "country": "Vietnam", "state": "Hanoi", "city": "Hanoi",
     "police": "113", "ambulance": "115", "fire": "114", "women": "111",
     "child": "111", "tourist": "+84 24 4567 8901", "disaster": "112",
     "medical": "115"},

    # PHILIPPINES
    {"id": 39, "country": "Philippines", "state": "Manila", "city": "Manila",
     "police": "117", "ambulance": "112", "fire": "112", "women": "911",
     "child": "911", "tourist": "+63 2 4567 8901", "disaster": "112",
     "medical": "112"},

    # RUSSIA
    {"id": 40, "country": "Russia", "state": "Moscow", "city": "Moscow",
     "police": "102", "ambulance": "103", "fire": "101", "women": "8-800-700-8000",
     "child": "8-800-200-0122", "tourist": "+7 495 4567 8901", "disaster": "112",
     "medical": "103"}
]


# ================= FLASK ROUTES =================

@app.route('/emergency')
def emergency_page():
    """Render the emergency assistance page"""
    return render_template('emergency.html')


@app.route('/api/emergency/suggest')
def emergency_suggest():
    """Get search suggestions"""
    query = request.args.get('q', '').strip().lower()
    if not query or len(query) < 2:
        return jsonify({'suggestions': []})
    
    suggestions = set()
    for entry in EMERGENCY_DATABASE:
        country = entry.get('country', '').lower()
        state = entry.get('state', '').lower()
        city = entry.get('city', '').lower()
        
        if query in country:
            suggestions.add(entry['country'])
        if query in state:
            suggestions.add(f"{entry['state']} ({entry['country']})")
        if query in city:
            suggestions.add(f"{entry['city']} ({entry['country']})")
    
    return jsonify({'suggestions': list(suggestions)[:10]})


@app.route('/api/emergency/search')
def emergency_search():
    """Search emergency numbers"""
    query = request.args.get('q', '').strip()
    category = request.args.get('category', 'all').strip().lower()
    
    if not query:
        return jsonify({'error': 'Please enter a search term', 'results': []})
    
    query_lower = query.lower()
    results = []
    
    for entry in EMERGENCY_DATABASE:
        # Check if query matches country, state, or city
        matches = False
        if query_lower in entry.get('country', '').lower():
            matches = True
        elif query_lower in entry.get('state', '').lower():
            matches = True
        elif query_lower in entry.get('city', '').lower():
            matches = True
        
        # Also check category values
        if not matches:
            for key in ['police', 'ambulance', 'fire', 'women', 'child', 'tourist', 'disaster', 'medical']:
                if entry.get(key) and query_lower in str(entry[key]).lower():
                    matches = True
                    break
        
        if not matches:
            continue
        
        # Apply category filter
        if category != 'all':
            if not entry.get(category):
                continue
        
        # Determine which number to show
        number = None
        icon = '📞'
        display_category = 'Emergency'
        
        # Map category to icon
        icon_map = {
            'police': '🚓', 'ambulance': '🚑', 'fire': '🚒',
            'women': '👩', 'child': '👶', 'medical': '🏥',
            'disaster': '🚨', 'tourist': '🌍'
        }
        
        if category != 'all' and entry.get(category):
            number = entry[category]
            display_category = category.capitalize()
            icon = icon_map.get(category, '📞')
        else:
            # Show first available number
            priority = ['police', 'ambulance', 'fire', 'women', 'child', 'medical', 'tourist', 'disaster']
            for cat in priority:
                if entry.get(cat):
                    number = entry[cat]
                    display_category = cat.capitalize()
                    icon = icon_map.get(cat, '📞')
                    break
        
        if not number:
            continue
        
        results.append({
            'country': entry.get('country', 'Unknown'),
            'state': entry.get('state', 'All'),
            'city': entry.get('city', ''),
            'number': number,
            'category': display_category,
            'icon': icon
        })
    
    # Remove duplicates
    seen = set()
    unique_results = []
    for r in results:
        key = f"{r['number']}-{r['country']}-{r['category']}"
        if key not in seen:
            seen.add(key)
            unique_results.append(r)
    
    return jsonify({'results': unique_results, 'count': len(unique_results)})
