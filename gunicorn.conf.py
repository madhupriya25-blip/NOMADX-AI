import multiprocessing
import os


bind = f"0.0.0.0:{os.environ.get('PORT', '5000')}"
worker_class = "eventlet"
workers = int(os.environ.get("WEB_CONCURRENCY", max(2, multiprocessing.cpu_count() // 2)))
threads = 1
timeout = int(os.environ.get("GUNICORN_TIMEOUT", "90"))
accesslog = "-"
errorlog = "-"
loglevel = os.environ.get("GUNICORN_LOG_LEVEL", "info")
