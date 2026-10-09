"""Lokalizacja i ustawienia projektu; przyszłe strefy mogą być dodane tutaj."""
from dataclasses import dataclass


@dataclass(frozen=True)
class LakeZone:
    slug: str
    name: str
    latitude: float
    longitude: float
    teryt: str


ZONES = {
    "jezioro": LakeZone(
        slug="jezioro",
        name="Jezioro Tarnobrzeskie",
        latitude=50.54478,
        longitude=21.64471,
        teryt="1864",  # miasto Tarnobrzeg (nie powiat tarnobrzeski 1820)
    )
}
DEFAULT_ZONE = ZONES["jezioro"]
TIMEZONE = "Europe/Warsaw"
APP_TITLE = "Jezioro Tarnobrzeskie | Pogoda i aktywności"
OPEN_METEO_BASE = "https://api.open-meteo.com/v1/forecast"
IMGW_WARNINGS_URL = "https://danepubliczne.imgw.pl/api/data/warningsmeteo"

HOURLY = [
    "temperature_2m", "apparent_temperature", "relative_humidity_2m",
    "precipitation", "precipitation_probability", "cloud_cover", "uv_index",
    "weather_code", "wind_speed_10m", "wind_gusts_10m",
    "wind_direction_10m", "is_day",
]
WIND_FIELDS = ["wind_speed_10m", "wind_gusts_10m", "wind_direction_10m"]
