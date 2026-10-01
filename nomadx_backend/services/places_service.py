from flask import current_app

from .external import request_json


GOOGLE_TEXT_URL = "https://maps.googleapis.com/maps/api/place/textsearch/json"
GOOGLE_DETAILS_URL = "https://maps.googleapis.com/maps/api/place/details/json"


def _key():
    key = current_app.config.get("GOOGLE_PLACES_API_KEY")
    if not key:
        raise ValueError("GOOGLE_PLACES_API_KEY is required for realtime Google Places lookup")
    return key


def _place(item):
    location = item.get("geometry", {}).get("location", {})
    return {
        "provider": "google_places",
        "provider_ref": item.get("place_id"),
        "name": item.get("name"),
        "address": item.get("formatted_address") or item.get("vicinity"),
        "rating": item.get("rating"),
        "review_count": item.get("user_ratings_total"),
        "price_level": item.get("price_level"),
        "is_open": item.get("opening_hours", {}).get("open_now"),
        "lat": location.get("lat"),
        "lon": location.get("lng"),
        "types": item.get("types", []),
    }


def realtime_search(query, place_type, lat=None, lon=None, radius=5000):
    params = {"key": _key(), "query": query, "type": place_type}
    if lat is not None and lon is not None:
        params["location"] = f"{lat},{lon}"
        params["radius"] = radius
    data = request_json(GOOGLE_TEXT_URL, params)
    return [_place(item) for item in data.get("results", [])]


def place_details(place_id):
    data = request_json(
        GOOGLE_DETAILS_URL,
        {
            "key": _key(),
            "place_id": place_id,
            "fields": "place_id,name,formatted_address,geometry,rating,user_ratings_total,opening_hours,formatted_phone_number,website,reviews,price_level,types",
        },
    )
    item = data.get("result", {})
    details = _place(item)
    details.update(
        {
            "phone": item.get("formatted_phone_number"),
            "website": item.get("website"),
            "opening_hours": item.get("opening_hours", {}),
            "reviews": [
                {
                    "author": review.get("author_name"),
                    "rating": review.get("rating"),
                    "text": review.get("text"),
                    "relative_time": review.get("relative_time_description"),
                }
                for review in item.get("reviews", [])
            ],
        }
    )
    return details
