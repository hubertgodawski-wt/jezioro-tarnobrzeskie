"""Testy logiki działające bez internetu, bez uruchomionego Streamlit."""
from datetime import datetime
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import pandas as pd
import pytest

from lake.data_sources import WeatherAPIError, parse_hourly, parse_imgw_warnings, active_water_warning
from lake.ratings import score_hour
from lake.wind import beaufort, compass, convert_speed, model_spread

NOW = datetime(2026, 10, 9, 15, 30, tzinfo=ZoneInfo("Europe/Warsaw"))
HOUR = int(pd.Timestamp(NOW).timestamp())
GOOD = {"hourly": {
    "time": [HOUR, HOUR + 3600],
    "temperature_2m": [21., 22.], "precipitation": [0., 0.],
    "weather_code": [1, 1], "wind_speed_10m": [15., 17.],
    "wind_gusts_10m": [21., 24.], "wind_direction_10m": [230., 245.],
}}


def test_wind_exact_beaufort_and_units():
    assert beaufort(19.79) == 3
    assert beaufort(19.8) == 4
    assert beaufort(28.79) == 4
    assert beaufort(28.8) == 5
    assert beaufort(117.71) == 11
    assert beaufort(117.72) == 12
    assert compass(359) == 'N'
    assert compass(1) == 'N'
    assert compass(float('inf')) == '—'
    assert beaufort(-1) is None
    assert convert_speed(18.52, 'knots') == pytest.approx(10)
    assert convert_speed(18, 'ms') == pytest.approx(5)
    assert convert_speed(None, 'bft') is None


def test_parse_fails_cleanly_on_incomplete_or_duplicate_data():
    payload = {"hourly": {**GOOD["hourly"], "time": [HOUR, HOUR]}}
    with pytest.raises(WeatherAPIError, match="powtarzające"):
        parse_hourly(payload, "Open-Meteo Best Match")
    no_temperature = {"hourly": {**GOOD["hourly"], "temperature_2m": [None, None]}}
    with pytest.raises(WeatherAPIError, match="temperatury"):
        parse_hourly(no_temperature, "Open-Meteo Best Match")
    no_wind = {"hourly": {**GOOD["hourly"], "wind_speed_10m": [None, None]}}
    with pytest.raises(WeatherAPIError, match="wiatru"):
        parse_hourly(no_wind, "Open-Meteo Best Match")


def test_imgw_scalar_teryt_and_time_zone_normalization():
    fixture = [{
        "id": "1", "teryt": "1864", "obowiazuje_od": "2026-10-09T13:00:00Z",
        "obowiazuje_do": "2026-10-09T17:00:00Z", "nazwa_zdarzenia": "Silny wiatr",
        "stopien": 1,
    }]
    alerts = parse_imgw_warnings(fixture, now=NOW)
    assert len(alerts) == 1
    assert alerts[0]["start"].hour == 15  # Europe/Warsaw = UTC+2 w październiku
    assert active_water_warning(alerts, NOW) is True
    assert active_water_warning(alerts, datetime(2026, 10, 9, 20, 0, tzinfo=ZoneInfo("Europe/Warsaw"))) is False


def test_forecast_alert_unknown_is_not_a_zero_weather_score():
    row = GOOD['hourly']
    available = {key: val[0] for key, val in row.items() if key != 'time'}
    unknown = score_hour('kayak', available, official_water_alert=None)
    assert unknown.blocked and unknown.score is None
    confirmed = score_hour('kayak', available, official_water_alert=True)
    assert confirmed.blocked and confirmed.score == 0
    safe_weather_only = score_hour('kayak', available, official_water_alert=False)
    assert safe_weather_only.score is not None and not safe_weather_only.blocked


def test_thunder_has_precedence_when_other_forecast_fields_missing():
    result = score_hour('sup', {'weather_code': 95, 'wind_gusts_10m': None})
    assert result.blocked and result.score == 0


def test_spread_comparison_is_not_available_with_a_single_model():
    a = SimpleNamespace(data=parse_hourly(GOOD, "Open-Meteo Best Match").data)
    spread, label = model_spread({'one': a}, pd.Timestamp(NOW))
    assert spread is None
    b_payload = {"hourly": {**GOOD['hourly'], 'wind_speed_10m': [28., 30.]}}
    b = SimpleNamespace(data=parse_hourly(b_payload, "ECMWF IFS").data)
    spread, label = model_spread({'one': a, 'two': b}, pd.Timestamp(NOW))
    assert spread == 13
    assert label == "Umiarkowana rozbieżność"
