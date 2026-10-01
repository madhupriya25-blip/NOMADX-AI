from .extensions import celery_app, db
from .models import Notification
from .services.notification_service import send_email


def _task():
    if celery_app is None:
        def decorator(func):
            return func
        return decorator
    return celery_app.task


@_task()
def deliver_email_notification(notification_id):
    notification = Notification.query.get(notification_id)
    if not notification or notification.channel != "email":
        return {"status": "missing"}
    user = notification.user
    try:
        send_email(user.email, notification.subject or "NomadX notification", notification.message)
        notification.status = "sent"
    except Exception as exc:
        notification.status = "failed"
        notification.metadata_json = {**(notification.metadata_json or {}), "error": str(exc)}
    db.session.commit()
    return {"status": notification.status}
