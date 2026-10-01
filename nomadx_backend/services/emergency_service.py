from ..extensions import db
from ..models import EmergencyRequest
from .emergency_numbers import emergency_contacts_for_category, emergency_profile
from .map_service import nearby, reverse_geocode
from .notification_service import queue_push, queue_sms_ready


def emergency_contacts(country=None, state=None):
    """Return helplines for a given country/state."""
    return emergency_profile(country=country, state=state)["helplines"]


def contacts_for_coords(lat, lon):
    """Reverse geocode coordinates to determine country/state and return helplines plus address info."""
    try:
        loc = reverse_geocode(lat, lon)
        addr = loc.get("address", {})
        country = addr.get("country") or addr.get("country_code")
        state = addr.get("state") or addr.get("region") or addr.get("state_district")
        helplines = emergency_contacts(country, state)
        return {"helplines": helplines, "address": loc}
    except Exception:
        return {"helplines": emergency_contacts(None), "address": {}}


def create_sos(user_id, category, latitude=None, longitude=None, location_text=None, country=None):
    contacts = emergency_contacts(country)
    contact_list = emergency_contacts_for_category(category=category, country=country)
    request = EmergencyRequest(
        user_id=user_id,
        category=category,
        latitude=latitude,
        longitude=longitude,
        location_text=location_text,
        status="logged",
        shared_with=[contacts["universal"]],
        metadata_json={"contacts": contacts, "selected_contacts": contact_list},
    )
    db.session.add(request)
    db.session.commit()
    if user_id:
        queue_push(user_id, f"SOS logged for {category}", {"emergency_request_id": request.id})
        queue_sms_ready(user_id, f"NomadX SOS: {category} at {location_text or 'unknown location'}", {"emergency_request_id": request.id})
    return request


def nearby_emergency_services(lat, lon):
    if lat is None or lon is None:
        return {"hospitals": [], "police": [], "pharmacy": []}
    return {
        "hospitals": nearby(lat, lon, "hospitals", radius=5000, limit=10),
        "police": nearby(lat, lon, "police", radius=5000, limit=10),
        "pharmacy": nearby(lat, lon, "pharmacy", radius=5000, limit=10),
    }
