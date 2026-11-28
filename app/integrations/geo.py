"""Geocoding and weather: Open-Meteo (primary), GeoNames (optional), MET Norway (weather fallback)."""
from __future__ import annotations

from app.config import cred
from app.providers.base import Gateway, ProviderError
from app.schemas.cards import card

WMO = {0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast", 45: "Fog", 48: "Rime fog", 51: "Light drizzle", 53: "Drizzle", 55: "Dense drizzle",
       61: "Light rain", 63: "Rain", 65: "Heavy rain", 71: "Light snow", 73: "Snow", 75: "Heavy snow", 80: "Rain showers", 81: "Rain showers", 82: "Violent showers",
       95: "Thunderstorm", 96: "Thunderstorm with hail", 99: "Thunderstorm with hail"}


async def geocode(gw: Gateway, city: str, country: str = "") -> dict:
    """Resolve a city to coordinates. Raises ProviderError('bad_response') when nothing matches."""
    params = {"name": city, "count": 5, "language": "en"}
    if country:
        params["countryCode"] = country
    data = await gw.get("open_meteo", "https://geocoding-api.open-meteo.com/v1/search", params=params, capability="geocoding")
    hits = data.get("results") or []
    if not hits and country:
        return await geocode(gw, city, "")
    if not hits:
        if cred("GEONAMES_USERNAME"):
            g = await gw.get("geonames", "https://secure.geonames.org/searchJSON", params={"q": city, "maxRows": 1, "username": cred("GEONAMES_USERNAME")}, capability="geocoding")
            if g.get("geonames"):
                x = g["geonames"][0]
                return {"name": x["name"], "lat": float(x["lat"]), "lon": float(x["lng"]), "country": x.get("countryCode", ""), "admin": x.get("adminName1", ""), "timezone": "auto", "provider": "GeoNames"}
        raise ProviderError("open_meteo", "bad_response", f"No location named '{city}' was found")
    x = max(hits, key=lambda h: h.get("population") or 0)
    return {"name": x["name"], "lat": x["latitude"], "lon": x["longitude"], "country": x.get("country_code", ""), "admin": x.get("admin1", ""), "timezone": x.get("timezone", "auto"), "provider": "Open-Meteo"}


async def weather(gw: Gateway, city: str, country: str = "", days: int = 5) -> list[dict]:
    place = await geocode(gw, city, country)
    try:
        d = await gw.get("open_meteo", "https://api.open-meteo.com/v1/forecast", capability="weather", params={
            "latitude": place["lat"], "longitude": place["lon"], "timezone": "auto", "forecast_days": days,
            "current": "temperature_2m,apparent_temperature,relative_humidity_2m,weather_code,wind_speed_10m",
            "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max,sunrise,sunset"})
    except ProviderError as exc:
        if exc.kind not in ("timeout", "unavailable", "circuit_open", "rate_limit"):
            raise
        return await _met_norway(gw, place)
    cur, daily = d.get("current", {}), d.get("daily", {})
    out = [card("open_meteo", "weather", f"Now in {place['name']}: {cur.get('temperature_2m')}°C, {WMO.get(cur.get('weather_code'), 'conditions unavailable')}",
                "https://open-meteo.com/en/docs", when=cur.get("time", ""), where=f"{place['name']}, {place['admin']}",
                summary=f"Feels like {cur.get('apparent_temperature')}°C · humidity {cur.get('relative_humidity_2m')}% · wind {cur.get('wind_speed_10m')} km/h",
                temperature_c=cur.get("temperature_2m"), condition=WMO.get(cur.get("weather_code"), ""), current=True, lat=place["lat"], lon=place["lon"])]
    for i, day in enumerate(daily.get("time", [])):
        code = daily["weather_code"][i]
        out.append(card("open_meteo", "forecast", f"{day}: {WMO.get(code, 'Forecast')}", "https://open-meteo.com/en/docs", when=day, where=place["name"],
                        summary=f"{daily['temperature_2m_min'][i]}–{daily['temperature_2m_max'][i]}°C · rain chance {daily['precipitation_probability_max'][i]}%",
                        t_min=daily["temperature_2m_min"][i], t_max=daily["temperature_2m_max"][i], rain_probability=daily["precipitation_probability_max"][i],
                        condition=WMO.get(code, ""), outdoor_ok=(daily["precipitation_probability_max"][i] or 0) < 40 and code < 60))
    return out


async def _met_norway(gw: Gateway, place: dict) -> list[dict]:
    d = await gw.get("met_norway", "https://api.met.no/weatherapi/locationforecast/2.0/compact", capability="weather",
                     params={"lat": round(place["lat"], 4), "lon": round(place["lon"], 4)})
    series = d.get("properties", {}).get("timeseries", [])
    out = []
    for row in series[:1] + series[12:60:24]:
        inst = row["data"]["instant"]["details"]
        symbol = (row["data"].get("next_6_hours") or row["data"].get("next_1_hours") or {}).get("summary", {}).get("symbol_code", "")
        out.append(card("met_norway", "weather" if not out else "forecast", f"{row['time'][:10]} in {place['name']}: {inst.get('air_temperature')}°C {symbol.replace('_', ' ')}",
                        "https://api.met.no/weatherapi/locationforecast/2.0/documentation", when=row["time"], where=place["name"],
                        summary=f"Humidity {inst.get('relative_humidity')}% · wind {inst.get('wind_speed')} m/s", temperature_c=inst.get("air_temperature"), condition=symbol, current=not out))
    return out
