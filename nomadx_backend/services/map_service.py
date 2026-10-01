from urllib.parse import quote

from .external import haversine_km, request_json


def geocode(query, limit=8):
    data = request_json(
        "https://nominatim.openstreetmap.org/search",
        {"q": query, "format": "json", "addressdetails": 1, "limit": limit},
    )
    return [
        {
            "name": item.get("name") or item.get("display_name", "").split(",")[0],
            "display_name": item.get("display_name"),
            "lat": float(item["lat"]),
            "lon": float(item["lon"]),
            "type": item.get("type"),
            "address": item.get("address", {}),
            "provider": "nominatim",
            "provider_ref": item.get("osm_id"),
        }
        for item in data
    ]


def reverse_geocode(lat, lon):
    data = request_json(
        "https://nominatim.openstreetmap.org/reverse",
        {"lat": lat, "lon": lon, "format": "json", "addressdetails": 1},
    )
    return {
        "display_name": data.get("display_name"),
        "address": data.get("address", {}),
        "lat": lat,
        "lon": lon,
    }


def route(start_lat, start_lon, end_lat, end_lon, profile="driving"):
    profile = profile if profile in {"driving", "walking", "cycling"} else "driving"
    url = (
        "https://router.project-osrm.org/route/v1/"
        f"{quote(profile)}/{start_lon},{start_lat};{end_lon},{end_lat}"
    )
    data = request_json(url, {"overview": "full", "geometries": "geojson", "steps": "true"})
    best = data["routes"][0]
    return {
        "distance_km": round(best["distance"] / 1000, 2),
        "duration_min": round(best["duration"] / 60, 1),
        "points": [[lat, lon] for lon, lat in best["geometry"]["coordinates"]],
        "provider": "osrm",
    }


def distance(lat1, lon1, lat2, lon2):
    return {"distance_km": haversine_km(lat1, lon1, lat2, lon2)}


def nearby(lat, lon, kind="tourism", radius=3000, limit=20):
    amenity = {
        "hotels": "hotel",
        "restaurants": "restaurant",
        "hospitals": "hospital",
        "police": "police",
        "fuel": "fuel",
        "pharmacy": "pharmacy",
    }.get(kind, kind)
    query = f"""
    [out:json][timeout:25];
    (
      node["amenity"="{amenity}"](around:{int(radius)},{lat},{lon});
      way["amenity"="{amenity}"](around:{int(radius)},{lat},{lon});
      node["tourism"="{amenity}"](around:{int(radius)},{lat},{lon});
      way["tourism"="{amenity}"](around:{int(radius)},{lat},{lon});
    );
    out center {int(limit)};
    """
    data = request_json("https://overpass-api.de/api/interpreter", {"data": query})
    places = []
    for item in data.get("elements", [])[:limit]:
        tags = item.get("tags", {})
        plat = item.get("lat") or item.get("center", {}).get("lat")
        plon = item.get("lon") or item.get("center", {}).get("lon")
        if plat is None or plon is None:
            continue
        places.append(
            {
                "name": tags.get("name") or amenity.title(),
                "lat": float(plat),
                "lon": float(plon),
                "type": tags.get("amenity") or tags.get("tourism") or kind,
                "distance_km": haversine_km(float(lat), float(lon), float(plat), float(plon)),
                "details": tags,
            }
        )
    return places
