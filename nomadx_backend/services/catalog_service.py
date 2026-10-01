from sqlalchemy import or_

from ..models import CarRental, Hotel, Restaurant, Review


def _like(value):
    return f"%{value.strip()}%" if value else None


def hotel_query(params):
    query = Hotel.query
    if params.get("city"):
        query = query.filter(Hotel.city.ilike(_like(params["city"])))
    if params.get("country"):
        query = query.filter(Hotel.country.ilike(_like(params["country"])))
    if params.get("q"):
        needle = _like(params["q"])
        query = query.filter(or_(Hotel.name.ilike(needle), Hotel.address.ilike(needle)))
    if params.get("min_rating"):
        query = query.filter(Hotel.rating >= float(params["min_rating"]))
    if params.get("max_price"):
        query = query.filter(Hotel.price_min <= float(params["max_price"]))
    return query.order_by(Hotel.rating.desc(), Hotel.price_min.asc().nullslast())


def restaurant_query(params):
    query = Restaurant.query
    if params.get("city"):
        query = query.filter(Restaurant.city.ilike(_like(params["city"])))
    if params.get("cuisine"):
        query = query.filter(Restaurant.cuisine.ilike(_like(params["cuisine"])))
    if params.get("q"):
        needle = _like(params["q"])
        query = query.filter(or_(Restaurant.name.ilike(needle), Restaurant.address.ilike(needle)))
    if params.get("open_now") in {"1", "true", "yes"}:
        query = query.filter(Restaurant.is_open.is_(True))
    return query.order_by(Restaurant.rating.desc())


def rental_query(params):
    query = CarRental.query
    if params.get("city"):
        query = query.filter(CarRental.city.ilike(_like(params["city"])))
    if params.get("country"):
        query = query.filter(CarRental.country.ilike(_like(params["country"])))
    if params.get("vehicle_type"):
        query = query.filter(CarRental.vehicle_type.ilike(_like(params["vehicle_type"])))
    if params.get("available") in {"1", "true", "yes"}:
        query = query.filter(CarRental.availability_status == "available")
    if params.get("q"):
        needle = _like(params["q"])
        query = query.filter(or_(CarRental.vehicle.ilike(needle), CarRental.rental_agency.ilike(needle)))
    return query.order_by(CarRental.rating.desc(), CarRental.price_per_day.asc().nullslast())


def reviews_for(subject_type, subject_id):
    return Review.query.filter_by(subject_type=subject_type, subject_id=subject_id).order_by(Review.created_at.desc())


def availability_summary(item):
    if isinstance(item, Hotel):
        return {"available": item.available_rooms > 0, "rooms": item.available_rooms}
    if isinstance(item, Restaurant):
        return {"available": (item.available_tables or 0) > 0, "tables": item.available_tables, "is_open": item.is_open}
    if isinstance(item, CarRental):
        return {"available": item.availability_status == "available", "status": item.availability_status}
    return {"available": False}
