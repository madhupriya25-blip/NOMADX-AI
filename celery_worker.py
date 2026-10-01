from app import app
from nomadx_backend.extensions import make_celery


celery = make_celery(app)
