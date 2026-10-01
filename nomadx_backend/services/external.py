import os
from math import asin, cos, radians, sin, sqrt

import requests


DEFAULT_HEADERS = {"User-Agent": "NomadX-AI/1.0"}


def request_json(url, params=None, headers=None, timeout=12):
    response = requests.get(
        url,
        params=params or {},
        headers={**DEFAULT_HEADERS, **(headers or {})},
        timeout=timeout,
    )
    response.raise_for_status()
    return response.json()


def post_json(url, payload=None, headers=None, timeout=30):
    response = requests.post(
        url,
        json=payload or {},
        headers={**DEFAULT_HEADERS, **(headers or {})},
        timeout=timeout,
    )
    response.raise_for_status()
    return response.json()


def haversine_km(lat1, lon1, lat2, lon2):
    radius = 6371.0
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    return round(2 * radius * asin(sqrt(a)), 2)


def env(name, default=None):
    return os.environ.get(name, default)
