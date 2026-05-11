import httpx

_OSRM_BASE = "http://router.project-osrm.org/route/v1/driving"
_cache: dict[tuple, list[list[float]]] = {}


def get_road_geometry(waypoints: list[tuple[float, float]]) -> list[list[float]]:
    """
    waypoints: list of (lat, lng)
    returns: [[lat, lng], ...] following actual roads via OSRM,
             falls back to straight line on any error.
    """
    if len(waypoints) < 2:
        return [[lat, lng] for lat, lng in waypoints]

    key = tuple(waypoints)
    if key in _cache:
        return _cache[key]

    coords_str = ";".join(f"{lng},{lat}" for lat, lng in waypoints)
    try:
        resp = httpx.get(
            f"{_OSRM_BASE}/{coords_str}",
            params={"overview": "full", "geometries": "geojson"},
            timeout=5.0,
        )
        data = resp.json()
        if data.get("code") == "Ok":
            # GeoJSON uses [lng, lat] — convert to [lat, lng] for folium
            result = [[c[1], c[0]] for c in data["routes"][0]["geometry"]["coordinates"]]
            _cache[key] = result
            return result
    except Exception:
        pass

    fallback = [[lat, lng] for lat, lng in waypoints]
    _cache[key] = fallback
    return fallback
