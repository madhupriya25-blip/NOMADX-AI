try:
    from celery import Celery
    from flask_jwt_extended import JWTManager
    from flask_limiter import Limiter
    from flask_limiter.util import get_remote_address
    from flask_migrate import Migrate
    from flask_socketio import SocketIO
    from flask_sqlalchemy import SQLAlchemy
    from flask_wtf.csrf import CSRFProtect
except ImportError:
    Celery = None
    JWTManager = None
    Limiter = None
    Migrate = None
    SocketIO = None
    SQLAlchemy = None
    CSRFProtect = None
    get_remote_address = None


BACKEND_DEPS_AVAILABLE = all(
    [Celery, JWTManager, Limiter, Migrate, SocketIO, SQLAlchemy, CSRFProtect]
)

db = SQLAlchemy() if SQLAlchemy else None
migrate = Migrate() if Migrate else None
jwt = JWTManager() if JWTManager else None
socketio = SocketIO(cors_allowed_origins="*") if SocketIO else None
csrf = CSRFProtect() if CSRFProtect else None
limiter = Limiter(key_func=get_remote_address) if Limiter and get_remote_address else None
celery_app = None


def make_celery(app):
    celery = Celery(
        app.import_name,
        broker=app.config["CELERY_BROKER_URL"],
        backend=app.config["CELERY_RESULT_BACKEND"],
    )
    celery.conf.update(app.config)

    class FlaskTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery.Task = FlaskTask
    return celery


def init_extensions(app):
    global celery_app
    if not BACKEND_DEPS_AVAILABLE:
        app.logger.warning(
            "NomadX production backend dependencies are not installed; "
            "legacy Flask routes remain active."
        )
        return False

    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    limiter.init_app(app)
    socketio.init_app(app, message_queue=app.config.get("REDIS_URL"))

    if app.config.get("ENABLE_CSRF"):
        csrf.init_app(app)

    celery_app = make_celery(app)
    return True


def init_backend(app):
    if not init_extensions(app):
        return False

    from .api.routes import api_v1_bp
    from .models import TokenBlocklist
    from .websockets import register_socketio_handlers

    @jwt.token_in_blocklist_loader
    def token_in_blocklist(jwt_header, jwt_payload):
        return TokenBlocklist.is_revoked(jwt_payload["jti"])

    app.register_blueprint(api_v1_bp)
    register_socketio_handlers(socketio)
    return True
