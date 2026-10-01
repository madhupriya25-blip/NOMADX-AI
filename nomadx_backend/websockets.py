from flask import request
from flask_jwt_extended import decode_token

from .services.ai_service import chat_reply
from .services.emergency_service import create_sos


def _identity_from_token(token):
    if not token:
        return None
    try:
        return int(decode_token(token)["sub"])
    except Exception:
        return None


def register_socketio_handlers(socketio):
    @socketio.on("connect")
    def on_connect(auth=None):
        user_id = _identity_from_token((auth or {}).get("token"))
        request.environ["nomadx_user_id"] = user_id
        socketio.emit("connected", {"success": True, "user_id": user_id}, room=request.sid)

    @socketio.on("location:update")
    def on_location_update(payload):
        socketio.emit("location:updated", payload or {}, room=request.sid)

    @socketio.on("chat:message")
    def on_chat_message(payload):
        payload = payload or {}
        user_id = request.environ.get("nomadx_user_id")
        result = chat_reply(user_id, payload.get("message", ""), payload.get("conversation_id"), payload.get("context"))
        socketio.emit("chat:reply", result, room=request.sid)

    @socketio.on("emergency:sos")
    def on_emergency_sos(payload):
        payload = payload or {}
        user_id = request.environ.get("nomadx_user_id")
        sos = create_sos(
            user_id,
            payload.get("category", "SOS"),
            payload.get("latitude"),
            payload.get("longitude"),
            payload.get("location_text"),
            payload.get("country"),
        )
        socketio.emit("emergency:logged", sos.to_dict(), room=request.sid)
