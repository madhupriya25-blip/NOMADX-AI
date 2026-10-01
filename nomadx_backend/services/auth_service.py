from datetime import datetime, timezone

from flask import current_app
from flask_jwt_extended import create_access_token, create_refresh_token

from ..extensions import db
from ..models import EmailVerificationToken, PasswordResetToken, User
from ..utils.validation import validate_email, validate_password
from .notification_service import queue_email


def register_user(username, email, password, phone=None):
    email = validate_email(email)
    validate_password(password)
    if User.query.filter_by(email=email).first():
        raise ValueError("Email is already registered")
    user = User(username=username.strip(), email=email, phone=phone)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    token = EmailVerificationToken(user_id=user.id)
    db.session.add(token)
    db.session.commit()
    verify_url = f"{current_app.config['PUBLIC_BASE_URL']}/api/v1/auth/verify-email/{token.token}"
    queue_email(user, "Verify your NomadX email", f"Verify your email: {verify_url}", {"token": token.token})
    return user


def login_user(email, password):
    user = User.query.filter_by(email=validate_email(email)).first()
    if not user or not user.check_password(password) or not user.is_active:
        raise ValueError("Invalid email or password")
    user.last_login_at = datetime.now(timezone.utc)
    db.session.commit()
    return {
        "user": user,
        "access_token": create_access_token(identity=str(user.id), additional_claims={"email": user.email}),
        "refresh_token": create_refresh_token(identity=str(user.id)),
    }


def create_password_reset(email):
    user = User.query.filter_by(email=validate_email(email)).first()
    if not user:
        return None
    token = PasswordResetToken(user_id=user.id)
    db.session.add(token)
    db.session.commit()
    reset_url = f"{current_app.config['PUBLIC_BASE_URL']}/reset-password/{token.token}"
    queue_email(user, "Reset your NomadX password", f"Reset your password: {reset_url}", {"token": token.token})
    return token


def reset_password(token_value, new_password):
    validate_password(new_password)
    token = PasswordResetToken.query.filter_by(token=token_value).first()
    if not token or not token.is_valid():
        raise ValueError("Password reset token is invalid or expired")
    user = User.query.get(token.user_id)
    user.set_password(new_password)
    token.used_at = datetime.now(timezone.utc)
    db.session.commit()
    return user


def verify_email(token_value):
    token = EmailVerificationToken.query.filter_by(token=token_value).first()
    if not token or token.used_at:
        raise ValueError("Email verification token is invalid")
    user = User.query.get(token.user_id)
    user.is_email_verified = True
    token.used_at = datetime.now(timezone.utc)
    db.session.commit()
    return user
