import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation


EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class ValidationError(ValueError):
    pass


def require_json(data, *fields):
    missing = [field for field in fields if data.get(field) in (None, "")]
    if missing:
        raise ValidationError(f"Missing required field(s): {', '.join(missing)}")


def clean_string(value, max_len=255, default=None):
    if value is None:
        return default
    value = str(value).strip()
    if not value:
        return default
    if len(value) > max_len:
        raise ValidationError(f"Value exceeds {max_len} characters")
    return value


def validate_email(value):
    email = clean_string(value, max_len=255)
    if not email or not EMAIL_RE.match(email):
        raise ValidationError("A valid email address is required")
    return email.lower()


def validate_password(value):
    if not value or len(value) < 8:
        raise ValidationError("Password must contain at least 8 characters")
    return value


def parse_decimal(value, default=None):
    if value in (None, ""):
        return default
    try:
        return Decimal(str(value))
    except InvalidOperation as exc:
        raise ValidationError("Invalid number") from exc


def parse_float(value, default=None):
    if value in (None, ""):
        return default
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ValidationError("Invalid coordinate") from exc


def parse_date(value, default=None):
    if value in (None, ""):
        return default
    if isinstance(value, date):
        return value
    try:
        return datetime.fromisoformat(str(value)).date()
    except ValueError as exc:
        raise ValidationError("Invalid ISO date") from exc


def allowed_subject(value):
    value = clean_string(value, max_len=40)
    if value not in {"hotel", "restaurant", "rental", "location", "trip", "attraction"}:
        raise ValidationError("Unsupported subject type")
    return value
