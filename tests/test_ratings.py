from datetime import datetime
from zoneinfo import ZoneInfo
import pandas as pd
from lake.wind import beaufort, compass, knots
from lake.ratings import score_hour, category
from lake.recommendations import best_windows, daily_summary
from lake.data_sources import parse_hourly, parse_imgw_warnings, active_water_warning, WeatherAPIError

BASE = {
    "temperature_2m": 23., "apparent_temperature": 23., "relative_humidity_2m": 50.,
    "precipitation": 0., "precipitation_probability": 5., "cloud_cover": 10.,
    "uv_index": 2., "weather_code": 0., "wind_speed_10m": 10., "wind_gusts_10m": 14.,
    "wind_direction_10m": 315., "is_day": 1.,
}


def test_beaufort_boundaries_and_units():
    assert beaufort(0) == 0
    assert beaufort(1) == 0
    assert beaufort(10) == 2
    assert beaufort(20) == 4
    assert beaufort(24) == 4
    assert beaufort(29) == 5
    assert beaufort(117) == 11
    assert beaufort(120) == 12
    assert beaufort(19.79) == 3
    assert beaufort(19.8) == 4
    assert beaufort(None) is None
    assert round(knots(18.52), 1) == 10.0
    assert compass(315) == "NW"
    assert compass(360) == "N"
    assert compass(None) == "—"


def test_beginner_sup_reacts_to_stronger_wind():
    calm = score_hour("sup", BASE, "beginner")
    gusty = score_hour("sup", {**BASE, "wind_speed_10m": 27, "wind_gusts_10m": 39}, "beginner")
    advanced = score_hour("sup", {**BASE, "wind_speed_10m": 27, "wind_gusts_10m": 39}, "advanced")
    assert calm.score > gusty.score
    assert advanced.score > gusty.score


def test_windsurf_has_different_wind_optimum():
    low = {**BASE, "wind_speed_10m": 2, "wind_gusts_10m": 4}
    preferred = {**BASE, "wind_speed_10m": 15, "wind_gusts_10m": 19}
    assert score_hour("windsurf", preferred).score > score_hour("windsurf", low).score


def test_running_hot_weather_is_worse():
    mild = {**BASE, "apparent_temperature": 14, "temperature_2m": 14}
    hot = {**BASE, "apparent_temperature": 36, "temperature_2m": 30}
    assert score_hour("run", mild).score > score_hour("run", hot).score


def test_thunder_blocked_for_any_level():
    for level in ("beginner", "advanced"):
        v = score_hour("sailing", {**BASE, "weather_code": 95}, level)
        assert v.blocked and v.score == 0


def test_unavailable_imgw_blocks_positive_water_recommendation():
    v = score_hour("sup", BASE, official_water_alert=None)
    assert v.blocked and v.score is None and "Nie udało" in v.reasons[0]
    assert not score_hour("run", BASE, official_water_alert=None).blocked


def test_missing_wind_not_synthetic_score():
    row = {**BASE, "wind_gusts_10m": None}
    assert score_hour("sup", row).score is None
    assert category(None)[0] == "Brak danych"


def test_warning_filters_teryt_and_validity():
    now = datetime(2026, 10, 9, 12, tzinfo=ZoneInfo("Europe/Warsaw"))
    data = [{"id": "one", "nazwa_zdarzenia": "Silny wiatr", "stopien": "2", "tresc": "Alert",
             "obowiazuje_od": "2026-10-09 09:00:00", "obowiazuje_do": "2026-10-09 20:00:00", "teryt": ["1864"]},
            {"id": "other", "nazwa_zdarzenia": "Silny wiatr", "stopien": "2",
             "obowiazuje_od": "2026-10-09 09:00:00", "obowiazuje_do": "2026-10-09 20:00:00", "teryt": ["1820"]}]
    result = parse_imgw_warnings(data, now=now)
    assert len(result) == 1 and result[0]["id"] == "one"
    assert active_water_warning(result, now) is True
    assert active_water_warning(None, now) is None


def test_unixtime_timezone_and_missing_optional_fields():
    hourly = {"time": [1791532800, 1791536400], "temperature_2m": [15, 16],
              "wind_speed_10m": [12, 14], "wind_gusts_10m": [18, 19],
              "wind_direction_10m": [90, 95], "precipitation": [0, 0], "weather_code": [0, 1]}
    parsed = parse_hourly({"hourly": hourly, "latitude": 50.5, "longitude": 21.6}, "Open-Meteo Best Match")
    assert str(parsed.data.index.tz) == "Europe/Warsaw"
    assert len(parsed.data) == 2
    assert parsed.data["temperature_2m"].iloc[1] == 16


def test_windows_require_continuous_hours():
    now = datetime(2026, 7, 4, 7, tzinfo=ZoneInfo("Europe/Warsaw"))
    df = pd.DataFrame([BASE for _ in range(5)], index=pd.date_range(now, periods=5, freq="h"))
    results = best_windows(df, "sup", {}, [], now)
    assert results and results[0]["hours"] == 5
    assert results[0]["score"] >= 70
    df.loc[df.index[2], "weather_code"] = 95
    split = best_windows(df, "sup", {}, [], now)
    assert len(split) == 2
    assert split[0]["hours"] == 2


def test_summary_for_user_favorites():
    now = datetime(2026, 7, 4, 7, tzinfo=ZoneInfo("Europe/Warsaw"))
    df = pd.DataFrame([BASE for _ in range(3)], index=pd.date_range(now, periods=3, freq="h"))
    summary = daily_summary(df, ["sup", "run"], {}, [], now)
    assert "sup" in summary.lower() or "bieg" in summary.lower()
