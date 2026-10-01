import json
import re
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

import requests
from flask import current_app, jsonify, request, session

try:
    from services.openai_service import OpenAIService, OpenAIServiceError
except Exception:
    OpenAIService = None
    OpenAIServiceError = Exception


HISTORY_SESSION_KEY = "chat_history"
MAX_HISTORY_ENTRIES = 20
MAX_MESSAGE_CHARS = 2000
DEFAULT_CITY = "Bangalore"


def register_chatbot_routes(api_bp):
    @api_bp.route("/chat", methods=["POST"])
    def chat():
        data = request.get_json(silent=True) or {}
        message = data.get("message") or data.get("prompt") or data.get("text") or ""
        if not isinstance(message, str):
            message = str(message or "")

        message = message.strip()
        history = _load_history()

        if not message:
            reply = "I am here when you are ready. Type a destination, hotel, restaurant, weather, trip plan, or emergency question."
            return jsonify(_chat_payload(reply, "local", history))

        if len(message) > MAX_MESSAGE_CHARS:
            message = message[:MAX_MESSAGE_CHARS].strip()

        try:
            reply, provider = _generate_reply(message, history)
        except Exception:
            current_app.logger.exception("Chatbot fallback handled an unexpected error")
            reply, provider = _fallback_reply(message, history), "local"

        history.append({"message": message, "reply": reply, "created_at": datetime.utcnow().isoformat(timespec="seconds")})
        history = history[-MAX_HISTORY_ENTRIES:]
        _save_history(history)
        _store_chat_turn(message, reply, provider)

        return jsonify(_chat_payload(reply, provider, history))


def _chat_payload(reply, provider, history):
    return {
        "success": True,
        "reply": reply,
        "response": reply,
        "message": reply,
        "provider": provider,
        "typing_delay_ms": min(900, max(250, len(reply) * 5)),
        "history": history[-MAX_HISTORY_ENTRIES:],
    }


def _load_history():
    history = session.get(HISTORY_SESSION_KEY, [])
    if not isinstance(history, list):
        return []

    clean = []
    for item in history:
        if isinstance(item, dict) and isinstance(item.get("message"), str) and isinstance(item.get("reply"), str):
            clean.append(
                {
                    "message": item["message"][:MAX_MESSAGE_CHARS],
                    "reply": item["reply"][:MAX_MESSAGE_CHARS],
                    "created_at": item.get("created_at") or "",
                }
            )
    return clean[-MAX_HISTORY_ENTRIES:]


def _save_history(history):
    session[HISTORY_SESSION_KEY] = history[-MAX_HISTORY_ENTRIES:]
    session.modified = True


def _generate_reply(message, history):
    local_reply = _smart_local_reply(message, history)
    if local_reply:
        return local_reply, "local"

    if OpenAIService:
        try:
            service_history = []
            for item in history[-6:]:
                service_history.append({"role": "user", "content": item["message"]})
                service_history.append({"role": "assistant", "content": item["reply"]})
            return OpenAIService().generate_reply(message, service_history), "openai"
        except OpenAIServiceError:
            pass
        except Exception:
            current_app.logger.warning("OpenAI chat provider unavailable; using local fallback", exc_info=True)

    return _fallback_reply(message, history), "local"


def _smart_local_reply(message, history):
    text = _normalize(message)
    city = _extract_city(text) or DEFAULT_CITY

    if text in {"hi", "hii", "hello", "hey", "hey there", "good morning", "good evening"}:
        return "Hello 👋 How can I help you today? I can find hotels, restaurants, weather, trip plans, rentals, maps, or emergency support."

    if _contains(text, "emergency", "sos", "police", "ambulance", "hospital", "fire", "unsafe", "help me"):
        contacts = _emergency_contacts()
        lines = [f"{item['name']}: {item['phone']}" for item in contacts]
        return (
            "Emergency support is ready. If there is immediate danger, call the local emergency number now.\n\n"
            + "\n".join(lines)
            + "\n\nShare your city or nearest landmark and I can help you decide the fastest next step."
        )

    if _contains(text, "weather", "temperature", "forecast", "rain", "climate"):
        return _weather_reply(city)

    if _contains(text, "hotel", "hotels", "stay", "room", "rooms", "resort"):
        hotels = _catalog("hotels", city=city)
        if not hotels and city != DEFAULT_CITY:
            hotels = _catalog("hotels", city=DEFAULT_CITY)
        if not hotels:
            return "I can help with hotels. Share the city, dates, budget, and preferred area, and I will narrow the best options."
        intro = f"Here are smart hotel suggestions in {hotels[0]['city']}:"
        rows = [
            f"{idx}. {hotel['name']} - {hotel['rating']} rating, {hotel['available_rooms']} rooms, {hotel['address']}, from {hotel['price']}/night."
            for idx, hotel in enumerate(hotels[:3], start=1)
        ]
        return f"{intro}\n" + "\n".join(rows) + "\n\nBest quick pick: choose the highest rating if comfort matters, or the lowest price if this is a budget trip."

    if _contains(text, "restaurant", "restaurants", "food", "cafe", "dinner", "lunch", "breakfast", "near me"):
        restaurants = _catalog("restaurants", city=DEFAULT_CITY if "near me" in text else city)
        if not restaurants and city != DEFAULT_CITY:
            restaurants = _catalog("restaurants", city=DEFAULT_CITY)
        if not restaurants:
            return "I can suggest restaurants. Tell me your city, cuisine, budget, and whether you want local food, vegetarian options, cafes, or fine dining."
        place = "near you" if "near me" in text else f"in {restaurants[0]['city']}"
        rows = [
            f"{idx}. {item['name']} - {item['cuisine']}, {item['location']}, {item['rating']} rating, {item['available_tables']} tables, {item['price_range']}."
            for idx, item in enumerate(restaurants[:3], start=1)
        ]
        return f"Good restaurant options {place}:\n" + "\n".join(rows) + "\n\nFor a smooth plan, book the table before your evening route."

    if _contains(text, "trip plan", "trip", "itinerary", "plan my trip", "travel plan", "budget", "vacation", "holiday", "destination", "visit", "travel", "explore"):
        return _trip_plan_reply(city)

    if _contains(text, "what", "how", "where", "when", "who", "why", "can you", "tell me", "show me"):
        # Provide a helpful travel response for general questions and broad requests.
        if city:
            return _trip_plan_reply(city)
        return (
            "I can answer your travel questions for any place in the world. "
            "Tell me a destination like Paris, New York, Goa, or Tokyo and I will build a travel plan, hotel suggestions, restaurant ideas, local safety tips, and weather guidance."
        )

    if _contains(text, "rental", "rentals", "car", "bike", "scooter", "vehicle"):
        rentals = _catalog("rentals", city=city) or _catalog("rentals", city=None)
        rows = [
            f"{idx}. {item['vehicle']} - {item['vehicle_type']}, {item['rental_agency']}, {item['availability']}, Rs {item['price']}/day, pickup at {item['pickup_address']}."
            for idx, item in enumerate(rentals[:3], start=1)
        ]
        return "Rental options I found:\n" + "\n".join(rows) + "\n\nTell me your pickup date and budget and I can help you choose."

    if _contains(text, "map", "route", "nearby places", "attraction", "attractions", "tourist", "visit"):
        return (
            f"For {city}, I would start with a heritage walk, a local market, a viewpoint route, and an evening food district. "
            "Use Smart Maps for nearby hotels, restaurants, hospitals, police stations, fuel, rentals, and route ETA."
        )

    return None


def _fallback_reply(message, history):
    user_question = message.strip() or "your question"
    if history:
        last = history[-1]["message"]
        return (
            f"You asked: '{user_question}'. I can help with any destination or question. "
            f"If you want a travel plan, just tell me the city or place. "
            f"Building on your last request about '{last}', I can refine this by city, budget, dates, duration, interests, weather, or safety."
        )
    return (
        f"You asked: '{user_question}'. I am a travel assistant for any destination in the world. "
        "Ask me about a city, country, attraction, hotel, restaurant, itinerary, or travel tip — and I will give you a plan or suggestion."
    )


def _trip_plan_reply(city):
    city_name = city or "your destination"
    hotels = _catalog("hotels", city=city) or _catalog("hotels", city=None)
    restaurants = _catalog("restaurants", city=city) or _catalog("restaurants", city=None)
    weather = _safe_weather(city_name if city_name != "your destination" else DEFAULT_CITY)
    travel_date = (datetime.now() + timedelta(days=14)).date().isoformat()
    hotel_name = hotels[0]["name"] if hotels else "a comfortable central stay"
    food_name = restaurants[0]["name"] if restaurants else "a popular local restaurant"
    daily_budget = round(float(hotels[0]["price"]) + 65, 2) if hotels else 150
    return (
        f"Here is a versatile 3-day trip plan for {city_name} starting around {travel_date}:\n"
        f"Day 1: Arrive in {city_name}, settle into {hotel_name}, explore a local landmark, and enjoy dinner at {food_name}.\n"
        f"Day 2: Visit the top attractions, discover a cultural experience, and spend the evening at a scenic viewpoint or nightlife district.\n"
        f"Day 3: Take a relaxed morning activity, shop or visit a museum, then prepare for your departure with flexible travel time.\n\n"
        f"Weather note: {weather}\n"
        f"Estimated daily budget: about {daily_budget} plus transport, tickets, and local experiences."
    )


def _weather_reply(city):
    return f"Live weather for travel in {city}: {_safe_weather(city)}"


def _safe_weather(city):
    try:
        place = _geocode(city)
        if not place:
            return "I could not confirm the live location, so carry water, check rain before leaving, and keep a light backup layer."
        response = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": place["lat"],
                "longitude": place["lon"],
                "current": "temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,weather_code,wind_speed_10m",
                "timezone": "auto",
            },
            timeout=5,
        )
        response.raise_for_status()
        current = response.json().get("current", {})
        condition = _weather_label(current.get("weather_code"))
        temp = current.get("temperature_2m")
        feels = current.get("apparent_temperature")
        humidity = current.get("relative_humidity_2m")
        wind = current.get("wind_speed_10m")
        return f"{condition}, {temp}C, feels like {feels}C, humidity {humidity}%, wind {wind} km/h. Pack for comfort and check rain before heading out."
    except Exception:
        return "Live weather is taking longer than expected. For now, keep water, a power bank, sun/rain protection, and check conditions again before leaving."


def _geocode(city):
    response = requests.get(
        "https://geocoding-api.open-meteo.com/v1/search",
        params={"name": city or DEFAULT_CITY, "count": 1, "language": "en", "format": "json"},
        timeout=5,
    )
    response.raise_for_status()
    results = response.json().get("results") or []
    if not results:
        return None
    item = results[0]
    return {"lat": item["latitude"], "lon": item["longitude"], "name": item.get("name") or city}


def _weather_label(code):
    labels = {
        0: "Clear sky",
        1: "Mostly clear",
        2: "Partly cloudy",
        3: "Cloudy",
        45: "Fog",
        48: "Fog",
        51: "Light drizzle",
        53: "Drizzle",
        55: "Dense drizzle",
        61: "Light rain",
        63: "Rain",
        65: "Heavy rain",
        71: "Light snow",
        80: "Rain showers",
        95: "Thunderstorm",
    }
    return labels.get(int(code or 0), "Weather data available")


def _catalog(table, city=None, limit=5):
    if table not in {"hotels", "restaurants", "rentals"}:
        return []
    try:
        with sqlite3.connect(_db_path()) as conn:
            conn.row_factory = sqlite3.Row
            params = []
            sql = f"SELECT * FROM {table}"
            if city:
                sql += " WHERE LOWER(city) LIKE ?"
                params.append(f"%{city.lower()}%")
            if table == "restaurants":
                sql += " ORDER BY rating DESC, available_tables DESC LIMIT ?"
            else:
                sql += " ORDER BY rating DESC, price ASC LIMIT ?"
            params.append(limit)
            return [dict(row) for row in conn.execute(sql, params).fetchall()]
    except Exception:
        current_app.logger.warning("Catalog query failed for %s", table, exc_info=True)
        return []


def _store_chat_turn(message, reply, provider):
    try:
        user_id = session.get("user_id")
        with sqlite3.connect(_db_path()) as conn:
            conn.execute(
                "INSERT INTO chatbot_history(user_id, message, reply) VALUES(?,?,?)",
                (user_id, message, reply),
            )
            conn.execute(
                "INSERT INTO chats(user_id, message, reply, provider) VALUES(?,?,?,?)",
                (user_id, message, reply, provider),
            )
    except Exception:
        current_app.logger.warning("Chat history storage skipped", exc_info=True)


def _db_path():
    configured = current_app.config.get("NOMADX_DB_PATH")
    if configured:
        return Path(configured)
    return Path(current_app.root_path) / "database" / "nomadx.db"


def _extract_city(text):
    known = _known_cities()
    for city in known:
        if city.lower() in text:
            return city
    match = re.search(r"\b(?:in|at|near|for)\s+([a-z][a-z\s]{2,40})", text)
    if not match:
        return ""
    candidate = match.group(1)
    candidate = re.sub(r"\b(hotel|hotels|restaurant|restaurants|weather|trip|plan|near|me|today|tomorrow)\b", "", candidate)
    candidate = " ".join(candidate.split())
    return candidate.title() if candidate else ""


def _known_cities():
    cities = set()
    for table in ("hotels", "restaurants", "rentals"):
        try:
            with sqlite3.connect(_db_path()) as conn:
                rows = conn.execute(f"SELECT DISTINCT city FROM {table}").fetchall()
                cities.update(row[0] for row in rows if row and row[0])
        except Exception:
            pass
    return sorted(cities, key=len, reverse=True)


def _emergency_contacts():
    return [
        {"name": "Universal Emergency", "phone": "112"},
        {"name": "Police", "phone": "100"},
        {"name": "Ambulance", "phone": "108"},
        {"name": "Fire", "phone": "101"},
        {"name": "Women Safety", "phone": "1091"},
    ]


def _normalize(value):
    return " ".join(str(value or "").lower().strip().split())


def _contains(text, *needles):
    return any(needle in text for needle in needles)
