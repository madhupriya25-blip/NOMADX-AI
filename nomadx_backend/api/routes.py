from datetime import datetime, timezone

from flask import Blueprint, Response, current_app, request
from flask_jwt_extended import (
    create_access_token,
    get_jwt,
    get_jwt_identity,
    jwt_required,
)

from ..extensions import db, limiter
from ..models import (
    Bookmark,
    CarRental,
    Favorite,
    Hotel,
    Notification,
    Restaurant,
    Review,
    TokenBlocklist,
    User,
)
from ..services.ai_service import generate_itinerary, stream_chat_reply, chat_reply
from ..services.auth_service import (
    create_password_reset,
    login_user,
    register_user,
    reset_password,
    verify_email,
)
from ..services.catalog_service import availability_summary, hotel_query, rental_query, restaurant_query, reviews_for
from ..services.emergency_numbers import emergency_profile, infer_region_from_coordinates
from ..services.emergency_service import create_sos, emergency_contacts, nearby_emergency_services
from ..services.map_service import distance, geocode, nearby, reverse_geocode, route
from ..services.places_service import place_details, realtime_search
from ..services.weather_service import current_weather, forecast
from ..utils.responses import error, ok, paginate
from ..utils.security import save_upload, xss_safe_text
from ..utils.validation import (
    ValidationError,
    allowed_subject,
    clean_string,
    parse_date,
    parse_decimal,
    parse_float,
    require_json,
    validate_email,
)


api_v1_bp = Blueprint("nomadx_api_v1", __name__, url_prefix="/api/v1")


def user_id():
    identity = get_jwt_identity()
    return int(identity) if identity is not None else None


def current_user():
    return User.query.get(user_id())


@api_v1_bp.errorhandler(ValidationError)
def validation_error(exc):
    return error(str(exc), 422)


@api_v1_bp.errorhandler(ValueError)
def value_error(exc):
    return error(str(exc), 400)


@api_v1_bp.errorhandler(404)
def not_found(exc):
    return error("Resource not found", 404)


@api_v1_bp.route("/health")
def health():
    return ok(status="ok", database="sqlalchemy", version="v1")


@api_v1_bp.route("/auth/register", methods=["POST"])
@limiter.limit("5 per minute")
def auth_register():
    data = request.get_json(silent=True) or {}
    require_json(data, "username", "email", "password")
    user = register_user(
        clean_string(data["username"], 80),
        data["email"],
        data["password"],
        clean_string(data.get("phone"), 40),
    )
    return ok(user=user.to_dict()), 201


@api_v1_bp.route("/auth/login", methods=["POST"])
@limiter.limit("10 per minute")
def auth_login():
    data = request.get_json(silent=True) or {}
    require_json(data, "email", "password")
    result = login_user(data["email"], data["password"])
    return ok(user=result["user"].to_dict(), access_token=result["access_token"], refresh_token=result["refresh_token"])


@api_v1_bp.route("/auth/refresh", methods=["POST"])
@jwt_required(refresh=True)
def auth_refresh():
    user = current_user()
    return ok(access_token=create_access_token(identity=str(user.id), additional_claims={"email": user.email}))


@api_v1_bp.route("/auth/logout", methods=["POST"])
@jwt_required()
def auth_logout():
    payload = get_jwt()
    TokenBlocklist.revoke(
        payload["jti"],
        payload["type"],
        user_id(),
        datetime.fromtimestamp(payload["exp"], tz=timezone.utc),
    )
    return ok(message="Logged out")


@api_v1_bp.route("/auth/password-reset", methods=["POST"])
@limiter.limit("3 per minute")
def auth_password_reset_request():
    data = request.get_json(silent=True) or {}
    require_json(data, "email")
    create_password_reset(data["email"])
    return ok(message="If that email exists, a reset link has been sent.")


@api_v1_bp.route("/auth/password-reset/confirm", methods=["POST"])
def auth_password_reset_confirm():
    data = request.get_json(silent=True) or {}
    require_json(data, "token", "password")
    user = reset_password(data["token"], data["password"])
    return ok(user=user.to_dict())


@api_v1_bp.route("/auth/verify-email/<token>")
def auth_verify_email(token):
    user = verify_email(token)
    return ok(user=user.to_dict(), message="Email verified")


@api_v1_bp.route("/profile", methods=["GET", "PATCH"])
@jwt_required()
def profile():
    user = current_user()
    if request.method == "GET":
        return ok(user=user.to_dict())
    data = request.get_json(silent=True) or {}
    for attr, max_len in {"username": 80, "phone": 40, "home_city": 120, "country": 120}.items():
        if attr in data:
            setattr(user, attr, clean_string(data.get(attr), max_len))
    if "email" in data:
        user.email = validate_email(data["email"])
        user.is_email_verified = False
    db.session.commit()
    return ok(user=user.to_dict())


@api_v1_bp.route("/maps/search")
def maps_search():
    query = clean_string(request.args.get("q"), 255)
    if not query:
        return error("q is required", 422)
    return ok(places=geocode(query, int(request.args.get("limit", 8))))


@api_v1_bp.route("/maps/reverse")
def maps_reverse():
    lat = parse_float(request.args.get("lat"))
    lon = parse_float(request.args.get("lon"))
    return ok(location=reverse_geocode(lat, lon))


@api_v1_bp.route("/maps/route")
def maps_route():
    return ok(route=route(
        parse_float(request.args.get("start_lat")),
        parse_float(request.args.get("start_lon")),
        parse_float(request.args.get("end_lat")),
        parse_float(request.args.get("end_lon")),
        request.args.get("profile", "driving"),
    ))


@api_v1_bp.route("/maps/distance")
def maps_distance():
    return ok(distance=distance(
        parse_float(request.args.get("start_lat")),
        parse_float(request.args.get("start_lon")),
        parse_float(request.args.get("end_lat")),
        parse_float(request.args.get("end_lon")),
    ))


@api_v1_bp.route("/maps/nearby")
def maps_nearby():
    return ok(places=nearby(
        parse_float(request.args.get("lat")),
        parse_float(request.args.get("lon")),
        request.args.get("type", "restaurants"),
        int(request.args.get("radius", 3000)),
        int(request.args.get("limit", 20)),
    ))


@api_v1_bp.route("/hotels")
def hotels():
    if request.args.get("realtime") in {"1", "true", "yes"}:
        query = request.args.get("q") or f"hotels in {request.args.get('city', '')}".strip()
        return ok(hotels=realtime_search(query, "lodging", request.args.get("lat"), request.args.get("lon")))
    result = paginate(hotel_query(request.args), default_per_page=20)
    return ok(hotels=result["items"], pagination=result["pagination"])


@api_v1_bp.route("/hotels/<int:hotel_id>")
def hotel_details(hotel_id):
    hotel = Hotel.query.get_or_404(hotel_id)
    return ok(hotel=hotel.to_dict(), availability=availability_summary(hotel), reviews=[r.to_dict() for r in reviews_for("hotel", hotel_id).limit(20)])


@api_v1_bp.route("/restaurants")
def restaurants():
    if request.args.get("realtime") in {"1", "true", "yes"}:
        query = request.args.get("q") or f"restaurants in {request.args.get('city', '')}".strip()
        return ok(restaurants=realtime_search(query, "restaurant", request.args.get("lat"), request.args.get("lon")))
    result = paginate(restaurant_query(request.args), default_per_page=20)
    return ok(restaurants=result["items"], pagination=result["pagination"])


@api_v1_bp.route("/restaurants/<int:restaurant_id>")
def restaurant_details(restaurant_id):
    restaurant = Restaurant.query.get_or_404(restaurant_id)
    return ok(restaurant=restaurant.to_dict(), availability=availability_summary(restaurant), reviews=[r.to_dict() for r in reviews_for("restaurant", restaurant_id).limit(20)])


@api_v1_bp.route("/providers/google-places/<path:place_id>")
def google_place_details(place_id):
    return ok(place=place_details(place_id))


@api_v1_bp.route("/rentals")
def rentals():
    result = paginate(rental_query(request.args), default_per_page=20)
    return ok(rentals=result["items"], pagination=result["pagination"])


@api_v1_bp.route("/rentals/<int:rental_id>")
def rental_details(rental_id):
    rental = CarRental.query.get_or_404(rental_id)
    return ok(rental=rental.to_dict(), availability=availability_summary(rental), reviews=[r.to_dict() for r in reviews_for("rental", rental_id).limit(20)])


@api_v1_bp.route("/trips", methods=["GET", "POST"])
@jwt_required()
def trips():
    if request.method == "GET":
        return ok(trips=[trip.to_dict() for trip in current_user().trips])
    data = request.get_json(silent=True) or {}
    require_json(data, "destination")
    trip = generate_itinerary(
        user_id(),
        clean_string(data["destination"], 255),
        data.get("start_date") or data.get("travel_date"),
        int(data.get("days", 3)),
        parse_decimal(data.get("budget_amount") or data.get("budget")),
        data.get("interests") or ["culture", "food", "sightseeing"],
    )
    return ok(trip=trip.to_dict()), 201


@api_v1_bp.route("/chat", methods=["POST"])
@jwt_required()
def chat():
    data = request.get_json(silent=True) or {}
    require_json(data, "message")
    return ok(**chat_reply(user_id(), xss_safe_text(data["message"]), data.get("conversation_id"), data.get("context")))


@api_v1_bp.route("/chat/history")
@jwt_required()
def chat_history():
    conversation_id = request.args.get("conversation_id")
    query = current_user().chats
    if conversation_id:
        query = [item for item in query if item.conversation_id == conversation_id]
    return ok(history=[item.to_dict() for item in query[-50:]])


@api_v1_bp.route("/chat/stream", methods=["POST"])
@jwt_required()
def chat_stream():
    data = request.get_json(silent=True) or {}
    require_json(data, "message")
    return Response(
        stream_chat_reply(user_id(), xss_safe_text(data["message"]), data.get("conversation_id"), data.get("context")),
        mimetype="application/x-ndjson",
    )


@api_v1_bp.route("/weather/current")
def weather_current():
    return ok(weather=current_weather(request.args.get("city"), request.args.get("lat"), request.args.get("lon")))


@api_v1_bp.route("/weather/forecast")
def weather_forecast():
    return ok(forecast=forecast(request.args.get("city"), request.args.get("lat"), request.args.get("lon"), int(request.args.get("days", 5))))


@api_v1_bp.route("/emergency/sos", methods=["POST"])
@jwt_required(optional=True)
@limiter.limit("20 per hour")
def emergency_sos():
    data = request.get_json(silent=True) or {}
    require_json(data, "category")
    sos = create_sos(
        user_id(),
        clean_string(data["category"], 80),
        parse_float(data.get("latitude"), None),
        parse_float(data.get("longitude"), None),
        clean_string(data.get("location_text"), 500),
        clean_string(data.get("country"), 120),
    )
    return ok(request=sos.to_dict()), 201


@api_v1_bp.route("/emergency/services")
def emergency_services():
    lat = parse_float(request.args.get("lat"))
    lon = parse_float(request.args.get("lon"))
    country = clean_string(request.args.get("country"), 120)
    state = clean_string(request.args.get("state"), 120)
    category = clean_string(request.args.get("category"), 80)
    address = None
    helplines = None
    if (not country) and lat is not None and lon is not None:
        # try to detect from coordinates
        try:
            info = reverse_geocode(lat, lon)
            addr = info.get("address", {})
            country = addr.get("country") or addr.get("country_code")
            state = addr.get("state") or addr.get("region") or addr.get("state_district")
            address = info
        except Exception:
            address = None
    if (not country) and lat is not None and lon is not None:
        inferred = infer_region_from_coordinates(lat, lon)
        country = inferred.get("country")
        state = state or inferred.get("state")

    helplines = emergency_contacts(country, state)
    profile = emergency_profile(country=country, state=state, category=category)
    return ok(services=nearby_emergency_services(lat, lon), helplines=helplines, profile=profile, address=address)


@api_v1_bp.route("/notifications", methods=["GET"])
@jwt_required()
def notifications():
    result = paginate(Notification.query.filter_by(user_id=user_id()).order_by(Notification.created_at.desc()))
    return ok(notifications=result["items"], pagination=result["pagination"])


@api_v1_bp.route("/notifications/<int:notification_id>/read", methods=["POST"])
@jwt_required()
def notification_read(notification_id):
    notification = Notification.query.filter_by(id=notification_id, user_id=user_id()).first_or_404()
    notification.read_at = datetime.now(timezone.utc)
    db.session.commit()
    return ok(notification=notification.to_dict())


@api_v1_bp.route("/reviews", methods=["GET", "POST"])
@jwt_required(optional=True)
def reviews():
    if request.method == "GET":
        subject_type = allowed_subject(request.args.get("subject_type"))
        subject_id = int(request.args.get("subject_id"))
        result = paginate(reviews_for(subject_type, subject_id))
        return ok(reviews=result["items"], pagination=result["pagination"])
    if user_id() is None:
        return error("Authentication required", 401)
    data = request.get_json(silent=True) or {}
    require_json(data, "subject_type", "subject_id", "rating")
    review = Review(
        user_id=user_id(),
        subject_type=allowed_subject(data["subject_type"]),
        subject_id=int(data["subject_id"]),
        rating=max(1, min(int(data["rating"]), 5)),
        title=clean_string(data.get("title"), 255),
        body=clean_string(data.get("body"), 4000),
    )
    db.session.add(review)
    db.session.commit()
    return ok(review=review.to_dict()), 201


def _collection(model, name):
    if request.method == "GET":
        result = paginate(model.query.filter_by(user_id=user_id()).order_by(model.created_at.desc()))
        return ok(**{name: result["items"], "pagination": result["pagination"]})
    data = request.get_json(silent=True) or {}
    require_json(data, "subject_type", "subject_id")
    payload = {
        "user_id": user_id(),
        "subject_type": allowed_subject(data["subject_type"]),
        "subject_id": int(data["subject_id"]),
        "metadata_json": data.get("metadata") or {},
    }
    if model is Bookmark:
        payload["notes"] = clean_string(data.get("notes"), 1000)
    item = model(**payload)
    db.session.add(item)
    db.session.commit()
    return ok(**{name[:-1]: item.to_dict()}), 201


@api_v1_bp.route("/favorites", methods=["GET", "POST"])
@jwt_required()
def favorites():
    return _collection(Favorite, "favorites")


@api_v1_bp.route("/bookmarks", methods=["GET", "POST"])
@jwt_required()
def bookmarks():
    return _collection(Bookmark, "bookmarks")
