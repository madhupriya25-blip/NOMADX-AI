from flask import current_app

from .external import request_json


def current_weather(city=None, lat=None, lon=None):
    key = current_app.config.get("OPENWEATHER_API_KEY")
    if key:
        params = {"appid": key, "units": "metric"}
        if lat is not None and lon is not None:
            params.update({"lat": lat, "lon": lon})
        else:
            params["q"] = city or "Bangalore"
        data = request_json("https://api.openweathermap.org/data/2.5/weather", params)
        return {
            "location": data.get("name"),
            "country": data.get("sys", {}).get("country"),
            "temperature": data.get("main", {}).get("temp"),
            "condition": data.get("weather", [{}])[0].get("description", "Clear").title(),
            "humidity": data.get("main", {}).get("humidity"),
            "wind": data.get("wind", {}).get("speed"),
            "rain_prediction": bool(data.get("rain")),
            "provider": "openweather",
        }

    if lat is None or lon is None:
        from .map_service import geocode

        places = geocode(city or "Bangalore", limit=1)
        lat, lon = places[0]["lat"], places[0]["lon"]
        location = places[0]["name"]
    else:
        location = f"{lat}, {lon}"

    data = request_json(
        "https://api.open-meteo.com/v1/forecast",
        {
            "latitude": lat,
            "longitude": lon,
            "current": "temperature_2m,relative_humidity_2m,wind_speed_10m,rain,weather_code",
            "forecast_days": 1,
        },
    )
    current = data.get("current", {})
    return {
        "location": location,
        "country": "",
        "temperature": current.get("temperature_2m"),
        "condition": "Rain" if current.get("rain") else "Clear",
        "humidity": current.get("relative_humidity_2m"),
        "wind": current.get("wind_speed_10m"),
        "rain_prediction": bool(current.get("rain")),
        "provider": "open-meteo",
    }


def forecast(city=None, lat=None, lon=None, days=5):
    if lat is None or lon is None:
        from .map_service import geocode

        places = geocode(city or "Bangalore", limit=1)
        lat, lon = places[0]["lat"], places[0]["lon"]
    data = request_json(
        "https://api.open-meteo.com/v1/forecast",
        {
            "latitude": lat,
            "longitude": lon,
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max",
            "forecast_days": max(1, min(int(days), 14)),
        },
    )
    daily = data.get("daily", {})
    return [
        {
            "date": daily.get("time", [])[i],
            "temp_max": daily.get("temperature_2m_max", [])[i],
            "temp_min": daily.get("temperature_2m_min", [])[i],
            "rain_probability": daily.get("precipitation_probability_max", [])[i],
        }
        for i in range(len(daily.get("time", [])))
    ]
