import json
from uuid import uuid4

from flask import current_app

from ..extensions import db
from ..models import ChatHistory, Trip
from ..utils.validation import parse_date
from .catalog_service import hotel_query, restaurant_query
from .weather_service import current_weather


def _openai_client():
    api_key = current_app.config.get("OPENAI_API_KEY")
    if not api_key:
        return None
    try:
        from openai import OpenAI
    except ImportError:
        return None
    return OpenAI(api_key=api_key)


def chat_reply(user_id, message, conversation_id=None, context=None):
    conversation_id = conversation_id or str(uuid4())
    prior = (
        ChatHistory.query.filter_by(user_id=user_id, conversation_id=conversation_id)
        .order_by(ChatHistory.created_at.asc())
        .limit(12)
        .all()
    )
    messages = [
        {
            "role": "system",
            "content": "You are NomadX AI, a concise travel assistant. Recommend safe, practical travel options.",
        }
    ]
    messages.extend({"role": item.role, "content": item.content} for item in prior)
    messages.append({"role": "user", "content": message})

    client = _openai_client()
    if client:
        response = client.chat.completions.create(
            model=current_app.config.get("OPENAI_MODEL", "gpt-4o-mini"),
            messages=messages,
            temperature=0.5,
        )
        reply = response.choices[0].message.content
    else:
        reply = (
            "I can help plan routes, hotels, restaurants, rentals, weather checks, and safety steps. "
            f"For your request, start with: {message[:180]}"
        )

    db.session.add(ChatHistory(user_id=user_id, conversation_id=conversation_id, role="user", content=message, context_json=context or {}))
    db.session.add(ChatHistory(user_id=user_id, conversation_id=conversation_id, role="assistant", content=reply, context_json=context or {}))
    db.session.commit()
    return {"conversation_id": conversation_id, "reply": reply}


def stream_chat_reply(user_id, message, conversation_id=None, context=None):
    result = chat_reply(user_id, message, conversation_id, context)
    for word in result["reply"].split():
        yield json.dumps({"token": word + " ", "conversation_id": result["conversation_id"]}) + "\n"
    yield json.dumps({"done": True, "conversation_id": result["conversation_id"]}) + "\n"


def generate_itinerary(user_id, destination, start_date, days=3, budget_amount=None, interests=None):
    days = max(1, min(int(days or 3), 30))
    interests = interests or ["culture", "food", "sightseeing"]
    hotels = [item.to_dict() for item in hotel_query({"city": destination}).limit(3)]
    restaurants = [item.to_dict() for item in restaurant_query({"city": destination}).limit(3)]
    weather = current_weather(city=destination)
    start = parse_date(start_date)

    prompt = {
        "destination": destination,
        "days": days,
        "budget_amount": str(budget_amount) if budget_amount else None,
        "interests": interests,
        "hotels": hotels,
        "restaurants": restaurants,
        "weather": weather,
    }
    client = _openai_client()
    if client:
        response = client.chat.completions.create(
            model=current_app.config.get("OPENAI_MODEL", "gpt-4o-mini"),
            messages=[
                {"role": "system", "content": "Return strict JSON for a multi-day travel itinerary."},
                {"role": "user", "content": json.dumps(prompt)},
            ],
            response_format={"type": "json_object"},
        )
        itinerary = json.loads(response.choices[0].message.content)
    else:
        itinerary = {
            "summary": f"{days}-day practical itinerary for {destination}",
            "daily_budget": round(float(budget_amount or 0) / days, 2) if budget_amount else None,
            "days": [
                {
                    "day": day,
                    "morning": f"Explore a top attraction in {destination}",
                    "afternoon": "Use nearby restaurant and route APIs for local options",
                    "evening": "Reserve a hotel or rental based on availability",
                }
                for day in range(1, days + 1)
            ],
            "hotels": hotels,
            "restaurants": restaurants,
            "weather": weather,
        }

    trip = Trip(
        user_id=user_id,
        destination=destination,
        start_date=start,
        budget_amount=budget_amount,
        interests=interests,
        itinerary_json=itinerary,
        status="planned",
    )
    db.session.add(trip)
    db.session.commit()
    return trip
