from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import Index, UniqueConstraint, func
from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db


def utcnow():
    return datetime.now(timezone.utc)


class TimestampMixin:
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = db.Column(
        db.DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class User(db.Model, TimestampMixin):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    public_id = db.Column(db.String(36), unique=True, nullable=False, default=lambda: str(uuid4()))
    username = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    phone = db.Column(db.String(40))
    profile_image = db.Column(db.String(512))
    home_city = db.Column(db.String(120))
    country = db.Column(db.String(120))
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    is_email_verified = db.Column(db.Boolean, nullable=False, default=False)
    last_login_at = db.Column(db.DateTime(timezone=True))

    trips = db.relationship("Trip", back_populates="user", cascade="all, delete-orphan")
    chats = db.relationship("ChatHistory", back_populates="user", cascade="all, delete-orphan")
    notifications = db.relationship("Notification", back_populates="user", cascade="all, delete-orphan")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            "id": self.id,
            "public_id": self.public_id,
            "username": self.username,
            "email": self.email,
            "phone": self.phone,
            "profile_image": self.profile_image,
            "home_city": self.home_city,
            "country": self.country,
            "is_email_verified": self.is_email_verified,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Location(db.Model, TimestampMixin):
    __tablename__ = "locations"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False, index=True)
    address = db.Column(db.Text)
    city = db.Column(db.String(120), index=True)
    state = db.Column(db.String(120))
    country = db.Column(db.String(120), index=True)
    latitude = db.Column(db.Numeric(10, 7), index=True)
    longitude = db.Column(db.Numeric(10, 7), index=True)
    provider = db.Column(db.String(80), default="local")
    provider_ref = db.Column(db.String(255))
    metadata_json = db.Column(db.JSON, nullable=False, default=dict)

    __table_args__ = (
        UniqueConstraint("provider", "provider_ref", name="uq_locations_provider_ref"),
        Index("ix_locations_lat_lon", "latitude", "longitude"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "address": self.address,
            "city": self.city,
            "state": self.state,
            "country": self.country,
            "lat": float(self.latitude) if self.latitude is not None else None,
            "lon": float(self.longitude) if self.longitude is not None else None,
            "metadata": self.metadata_json or {},
        }


class Trip(db.Model, TimestampMixin):
    __tablename__ = "trips"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    destination = db.Column(db.String(255), nullable=False)
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    budget_amount = db.Column(db.Numeric(12, 2))
    budget_currency = db.Column(db.String(8), default="INR")
    interests = db.Column(db.JSON, nullable=False, default=list)
    itinerary_json = db.Column(db.JSON, nullable=False, default=dict)
    status = db.Column(db.String(40), nullable=False, default="draft")

    user = db.relationship("User", back_populates="trips")

    def to_dict(self):
        return {
            "id": self.id,
            "destination": self.destination,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "budget_amount": float(self.budget_amount) if self.budget_amount is not None else None,
            "budget_currency": self.budget_currency,
            "interests": self.interests or [],
            "itinerary": self.itinerary_json or {},
            "status": self.status,
        }


class Hotel(db.Model, TimestampMixin):
    __tablename__ = "hotels"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False, index=True)
    location_id = db.Column(db.Integer, db.ForeignKey("locations.id"), index=True)
    city = db.Column(db.String(120), index=True)
    country = db.Column(db.String(120), index=True)
    address = db.Column(db.Text)
    rating = db.Column(db.Numeric(3, 2), default=0)
    review_count = db.Column(db.Integer, default=0)
    price_min = db.Column(db.Numeric(12, 2))
    price_currency = db.Column(db.String(8), default="INR")
    available_rooms = db.Column(db.Integer, default=0)
    amenities = db.Column(db.JSON, nullable=False, default=list)
    image_url = db.Column(db.String(512))
    provider = db.Column(db.String(80), default="local")
    provider_ref = db.Column(db.String(255))
    metadata_json = db.Column(db.JSON, nullable=False, default=dict)

    location = db.relationship("Location")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "city": self.city,
            "country": self.country,
            "address": self.address,
            "rating": float(self.rating or 0),
            "review_count": self.review_count,
            "price_min": float(self.price_min) if self.price_min is not None else None,
            "price_currency": self.price_currency,
            "available_rooms": self.available_rooms,
            "amenities": self.amenities or [],
            "image": self.image_url,
            "provider": self.provider,
            "metadata": self.metadata_json or {},
        }


class Restaurant(db.Model, TimestampMixin):
    __tablename__ = "restaurants"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False, index=True)
    location_id = db.Column(db.Integer, db.ForeignKey("locations.id"), index=True)
    cuisine = db.Column(db.String(120), index=True)
    city = db.Column(db.String(120), index=True)
    country = db.Column(db.String(120), index=True)
    address = db.Column(db.Text)
    phone = db.Column(db.String(40))
    rating = db.Column(db.Numeric(3, 2), default=0)
    review_count = db.Column(db.Integer, default=0)
    price_range = db.Column(db.String(40))
    is_open = db.Column(db.Boolean)
    available_tables = db.Column(db.Integer, default=0)
    image_url = db.Column(db.String(512))
    provider = db.Column(db.String(80), default="local")
    provider_ref = db.Column(db.String(255))
    metadata_json = db.Column(db.JSON, nullable=False, default=dict)

    location = db.relationship("Location")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "cuisine": self.cuisine,
            "city": self.city,
            "country": self.country,
            "address": self.address,
            "phone": self.phone,
            "rating": float(self.rating or 0),
            "review_count": self.review_count,
            "price_range": self.price_range,
            "is_open": self.is_open,
            "available_tables": self.available_tables,
            "image": self.image_url,
            "metadata": self.metadata_json or {},
        }


class CarRental(db.Model, TimestampMixin):
    __tablename__ = "car_rentals"

    id = db.Column(db.Integer, primary_key=True)
    vehicle = db.Column(db.String(180), nullable=False, index=True)
    vehicle_type = db.Column(db.String(80), index=True)
    registration_number = db.Column(db.String(80), unique=True)
    city = db.Column(db.String(120), index=True)
    state = db.Column(db.String(120))
    country = db.Column(db.String(120), index=True)
    pickup_address = db.Column(db.Text)
    rental_agency = db.Column(db.String(180))
    owner_phone = db.Column(db.String(40))
    fuel_type = db.Column(db.String(60))
    transmission = db.Column(db.String(60))
    price_per_day = db.Column(db.Numeric(12, 2))
    price_currency = db.Column(db.String(8), default="INR")
    rating = db.Column(db.Numeric(3, 2), default=0)
    availability_status = db.Column(db.String(40), default="available")
    image_url = db.Column(db.String(512))
    metadata_json = db.Column(db.JSON, nullable=False, default=dict)

    def to_dict(self):
        return {
            "id": self.id,
            "vehicle": self.vehicle,
            "vehicle_type": self.vehicle_type,
            "registration_number": self.registration_number,
            "city": self.city,
            "state": self.state,
            "country": self.country,
            "pickup_address": self.pickup_address,
            "rental_agency": self.rental_agency,
            "owner_phone": self.owner_phone,
            "fuel_type": self.fuel_type,
            "transmission": self.transmission,
            "price_per_day": float(self.price_per_day) if self.price_per_day is not None else None,
            "price_currency": self.price_currency,
            "rating": float(self.rating or 0),
            "availability": self.availability_status,
            "image": self.image_url,
        }


class ChatHistory(db.Model, TimestampMixin):
    __tablename__ = "chat_history"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), index=True)
    conversation_id = db.Column(db.String(36), nullable=False, index=True, default=lambda: str(uuid4()))
    role = db.Column(db.String(20), nullable=False)
    content = db.Column(db.Text, nullable=False)
    context_json = db.Column(db.JSON, nullable=False, default=dict)

    user = db.relationship("User", back_populates="chats")

    def to_dict(self):
        return {
            "id": self.id,
            "conversation_id": self.conversation_id,
            "role": self.role,
            "content": self.content,
            "context": self.context_json or {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class EmergencyRequest(db.Model, TimestampMixin):
    __tablename__ = "emergency_requests"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), index=True)
    category = db.Column(db.String(80), nullable=False)
    latitude = db.Column(db.Numeric(10, 7))
    longitude = db.Column(db.Numeric(10, 7))
    location_text = db.Column(db.Text)
    status = db.Column(db.String(40), nullable=False, default="logged")
    shared_with = db.Column(db.JSON, nullable=False, default=list)
    metadata_json = db.Column(db.JSON, nullable=False, default=dict)

    def to_dict(self):
        return {
            "id": self.id,
            "category": self.category,
            "latitude": float(self.latitude) if self.latitude is not None else None,
            "longitude": float(self.longitude) if self.longitude is not None else None,
            "location_text": self.location_text,
            "status": self.status,
            "shared_with": self.shared_with or [],
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Notification(db.Model, TimestampMixin):
    __tablename__ = "notifications"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    channel = db.Column(db.String(40), nullable=False)
    subject = db.Column(db.String(255))
    message = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(40), nullable=False, default="queued")
    read_at = db.Column(db.DateTime(timezone=True))
    metadata_json = db.Column(db.JSON, nullable=False, default=dict)

    user = db.relationship("User", back_populates="notifications")

    def to_dict(self):
        return {
            "id": self.id,
            "channel": self.channel,
            "subject": self.subject,
            "message": self.message,
            "status": self.status,
            "read_at": self.read_at.isoformat() if self.read_at else None,
            "metadata": self.metadata_json or {},
        }


class Review(db.Model, TimestampMixin):
    __tablename__ = "reviews"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    subject_type = db.Column(db.String(40), nullable=False, index=True)
    subject_id = db.Column(db.Integer, nullable=False, index=True)
    rating = db.Column(db.Integer, nullable=False)
    title = db.Column(db.String(255))
    body = db.Column(db.Text)

    __table_args__ = (Index("ix_reviews_subject", "subject_type", "subject_id"),)

    def to_dict(self):
        return {
            "id": self.id,
            "subject_type": self.subject_type,
            "subject_id": self.subject_id,
            "rating": self.rating,
            "title": self.title,
            "body": self.body,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Favorite(db.Model, TimestampMixin):
    __tablename__ = "favorites"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    subject_type = db.Column(db.String(40), nullable=False)
    subject_id = db.Column(db.Integer, nullable=False)
    metadata_json = db.Column(db.JSON, nullable=False, default=dict)

    __table_args__ = (UniqueConstraint("user_id", "subject_type", "subject_id", name="uq_favorites_user_subject"),)

    def to_dict(self):
        return {"id": self.id, "subject_type": self.subject_type, "subject_id": self.subject_id, "metadata": self.metadata_json or {}}


class Bookmark(db.Model, TimestampMixin):
    __tablename__ = "bookmarks"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    subject_type = db.Column(db.String(40), nullable=False)
    subject_id = db.Column(db.Integer, nullable=False)
    notes = db.Column(db.Text)
    metadata_json = db.Column(db.JSON, nullable=False, default=dict)

    __table_args__ = (UniqueConstraint("user_id", "subject_type", "subject_id", name="uq_bookmarks_user_subject"),)

    def to_dict(self):
        return {"id": self.id, "subject_type": self.subject_type, "subject_id": self.subject_id, "notes": self.notes, "metadata": self.metadata_json or {}}


class PasswordResetToken(db.Model, TimestampMixin):
    __tablename__ = "password_reset_tokens"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    token = db.Column(db.String(128), unique=True, nullable=False, default=lambda: uuid4().hex)
    expires_at = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: utcnow() + timedelta(hours=1))
    used_at = db.Column(db.DateTime(timezone=True))

    def is_valid(self):
        return not self.used_at and self.expires_at > utcnow()


class EmailVerificationToken(db.Model, TimestampMixin):
    __tablename__ = "email_verification_tokens"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    token = db.Column(db.String(128), unique=True, nullable=False, default=lambda: uuid4().hex)
    expires_at = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: utcnow() + timedelta(days=2))
    used_at = db.Column(db.DateTime(timezone=True))


class TokenBlocklist(db.Model):
    __tablename__ = "token_blocklist"

    id = db.Column(db.Integer, primary_key=True)
    jti = db.Column(db.String(36), unique=True, nullable=False, index=True)
    token_type = db.Column(db.String(16), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), index=True)
    expires_at = db.Column(db.DateTime(timezone=True), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now(), nullable=False)

    @classmethod
    def revoke(cls, jti, token_type, user_id, expires_at):
        db.session.add(cls(jti=jti, token_type=token_type, user_id=user_id, expires_at=expires_at))
        db.session.commit()

    @classmethod
    def is_revoked(cls, jti):
        return db.session.query(cls.id).filter_by(jti=jti).first() is not None
