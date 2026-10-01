import smtplib
from email.message import EmailMessage

from flask import current_app

from ..extensions import db
from ..models import Notification


def create_notification(user_id, channel, message, subject=None, metadata=None):
    notification = Notification(
        user_id=user_id,
        channel=channel,
        subject=subject,
        message=message,
        metadata_json=metadata or {},
    )
    db.session.add(notification)
    db.session.commit()
    return notification


def send_email(to_email, subject, body):
    msg = EmailMessage()
    msg["From"] = current_app.config["MAIL_FROM"]
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.set_content(body)
    with smtplib.SMTP(current_app.config["MAIL_SERVER"], current_app.config["MAIL_PORT"], timeout=15) as smtp:
        if current_app.config.get("MAIL_USE_TLS"):
            smtp.starttls()
        if current_app.config.get("MAIL_USERNAME"):
            smtp.login(current_app.config["MAIL_USERNAME"], current_app.config["MAIL_PASSWORD"])
        smtp.send_message(msg)


def queue_email(user, subject, body, metadata=None):
    notification = create_notification(user.id, "email", body, subject=subject, metadata=metadata)
    try:
        send_email(user.email, subject, body)
        notification.status = "sent"
    except Exception as exc:
        notification.status = "failed"
        notification.metadata_json = {**(notification.metadata_json or {}), "error": str(exc)}
    db.session.commit()
    return notification


def queue_push(user_id, message, metadata=None):
    return create_notification(user_id, "push", message, metadata=metadata)


def queue_sms_ready(user_id, message, metadata=None):
    payload = {"provider": "twilio-ready", **(metadata or {})}
    return create_notification(user_id, "sms", message, metadata=payload)
