"""Pobieranie i normalizacja danych. W module nie ma przykładowych odczytów."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .config import DEFAULT_ZONE, HOURLY, IMGW_WARNINGS_URL, TIMEZONE, WIND_FIELDS


class WeatherAPIError(RuntimeError):
    """Brak lub niepoprawny wynik źródła danych."""


def _get_json(url: str, params: dict | None = None):
    retry = Retry(total=2, backoff_factor=0.3, status_forcelist=[429, 500, 502, 503, 504])
    with requests.Session() as session:
        session.mount("https://", HTTPAdapter(max_retries=retry))
        try:
            response = session.get(url, params=params, timeout=(5, 12), headers={"User-Agent": "LakeTarnobrzeg/0.1 (weather dashboard)"})
            response.raise_for_status()
            return response.json()
        except (requests.RequestException, ValueError) as exc:
            raise WeatherAPIError(f"Nie można pobrać danych ze źródła: {type(exc).__name__}") from exc


def _request_params(fields, days: int):
    return {
        "latitude": DEFAULT_ZONE.latitude,
        "longitude": DEFAULT_ZONE.longitude,
        "hourly": ",".join(fields),
        "forecast_days": days,
        "timezone": TIMEZONE,
        "timeformat": "unixtime",
        "wind_speed_unit": "kmh",
    }


@dataclass
class Forecast:
    data: pd.DataFrame
    fetched_at: datetime
    source: str
    provider_lat: float | None
    provider_lon: float | None


def parse_hourly(payload: dict, source: str) -> Forecast:
    hourly = payload.get("hourly")
    if not isinstance(hourly, dict) or not isinstance(hourly.get("time"), list):
        raise WeatherAPIError("Źródło nie zwróciło poprawnej prognozy godzinowej")
    try:
        index = pd.to_datetime(hourly["time"], unit="s", utc=True).tz_convert(TIMEZONE)
    except (TypeError, ValueError, OverflowError) as exc:
        raise WeatherAPIError("Niepoprawny format czasu prognozy") from exc
    if len(index) == 0:
        raise WeatherAPIError("Prognoza jest pusta")
    if index.has_duplicates:
        raise WeatherAPIError("Prognoza zawiera powtarzające się godziny")
    df = pd.DataFrame(index=index)
    df.index.name = "czas"
    for field, values in hourly.items():
        if field == "time":
            continue
        if not isinstance(values, list) or len(values) != len(index):
            continue
        df[field] = pd.to_numeric(values, errors="coerce")
    required = {"wind_speed_10m", "wind_gusts_10m", "wind_direction_10m", "temperature_2m", "precipitation", "weather_code"}
    if source == "Open-Meteo Best Match" and not required.issubset(set(df.columns)):
        raise WeatherAPIError("Prognoza nie zawiera wymaganych parametrów")
    if "wind_speed_10m" not in df or df["wind_speed_10m"].notna().sum() == 0:
        raise WeatherAPIError("Brak użytecznej prognozy wiatru")
    if source == "Open-Meteo Best Match" and df["temperature_2m"].notna().sum() == 0:
        raise WeatherAPIError("Brak użytecznej prognozy temperatury")
    return Forecast(
        data=df.sort_index(),
        fetched_at=datetime.now(timezone.utc),
        source=source,
        provider_lat=payload.get("latitude"),
        provider_lon=payload.get("longitude"),
    )


def get_primary() -> Forecast:
    return parse_hourly(
        _get_json("https://api.open-meteo.com/v1/forecast", _request_params(HOURLY, 7)),
        "Open-Meteo Best Match",
    )


MODEL_ENDPOINTS = {
    # Domyślne rodzinne zestawy modeli dostawców; ich zakres bywa krótszy.
    "ECMWF IFS": ("https://api.open-meteo.com/v1/ecmwf", 7),
    "DWD ICON": ("https://api.open-meteo.com/v1/dwd-icon", 5),
}


def get_comparison(name: str) -> Forecast:
    if name not in MODEL_ENDPOINTS:
        raise ValueError("Nieznany model")
    url, days = MODEL_ENDPOINTS[name]
    return parse_hourly(_get_json(url, _request_params(WIND_FIELDS, days)), name)


def parse_imgw_warnings(payload: list, teryt: str = DEFAULT_ZONE.teryt, now: datetime | None = None) -> list[dict]:
    if not isinstance(payload, list):
        raise WeatherAPIError("Niepoprawny format ostrzeżeń IMGW")
    now = now or datetime.now(ZoneInfo(TIMEZONE))
    if payload and not any(isinstance(item, dict) and "teryt" in item for item in payload):
        raise WeatherAPIError("Nieznany format danych o obszarach ostrzeżeń IMGW")
    out = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        codes = item.get("teryt") or []
        if not isinstance(codes, (list, tuple, set)):
            codes = [codes]
        if teryt not in [str(code) for code in codes]:
            continue
        try:
            start = datetime.fromisoformat(item["obowiazuje_od"])
            end = datetime.fromisoformat(item["obowiazuje_do"])
            # IMGW może zwrócić czas lokalny bez strefy albo czas ze strefą.
            start = start.replace(tzinfo=ZoneInfo(TIMEZONE)) if start.tzinfo is None else start.astimezone(ZoneInfo(TIMEZONE))
            end = end.replace(tzinfo=ZoneInfo(TIMEZONE)) if end.tzinfo is None else end.astimezone(ZoneInfo(TIMEZONE))
        except (TypeError, KeyError, ValueError):
            continue
        if end < now or start > now + timedelta(hours=48):
            continue
        out.append({
            "id": str(item.get("id", "")),
            "name": str(item.get("nazwa_zdarzenia", "Ostrzeżenie")),
            "level": str(item.get("stopien", "?")),
            "text": str(item.get("tresc", "")),
            "start": start,
            "end": end,
            "active": start <= now <= end,
        })
    return sorted(out, key=lambda a: (not a["active"], a["start"]))


def get_imgw_warnings() -> list[dict]:
    return parse_imgw_warnings(_get_json(IMGW_WARNINGS_URL))


def warning_applies_to_water(warning: dict) -> bool:
    name = warning.get("name", "").casefold()
    return any(s in name for s in ("burz", "wiatr", "szkwa", "sztorm", "deszcz", "grad", "mgł", "śnieg"))


def active_water_warning(warnings: list[dict] | None, at: datetime) -> bool | None:
    if warnings is None:
        return None  # brak weryfikacji: nie wolno sugerować braku ostrzeżeń
    return any(warning_applies_to_water(w) and w["start"] <= at <= w["end"] for w in warnings)
