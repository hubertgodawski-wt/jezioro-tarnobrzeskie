from datetime import datetime
from zoneinfo import ZoneInfo
import pandas as pd
from lake.recommendations import best_windows

BASE = {"temperature_2m": 15, "apparent_temperature": 15, "relative_humidity_2m": 45,
        "precipitation": 0, "precipitation_probability": 0, "weather_code": 0,
        "wind_speed_10m": 7, "wind_gusts_10m": 12, "is_day": 1, "uv_index": 1}


def test_long_good_day_does_not_yield_all_day_window():
    now = datetime(2026, 7, 1, 7, tzinfo=ZoneInfo('Europe/Warsaw'))
    df = pd.DataFrame([BASE] * 13, index=pd.date_range(now, periods=13, freq='h'))
    results = best_windows(df, 'run', {}, [], now)
    assert results
    assert all(2 <= item['hours'] <= 5 for item in results)
    for i, item in enumerate(results):
        assert item['start'].date() == (item['end'] - pd.Timedelta(seconds=1)).date()
        for other in results[i + 1:]:
            assert item['end'] <= other['start'] or other['end'] <= item['start']


def test_best_window_skips_incomplete_start_hour():
    now = datetime(2026, 7, 1, 7, 50, tzinfo=ZoneInfo('Europe/Warsaw'))
    df = pd.DataFrame([BASE] * 5, index=pd.date_range(now.replace(minute=0), periods=5, freq='h'))
    results = best_windows(df, 'run', {}, [], now)
    assert results
    assert all(item['start'].hour >= 8 for item in results)


def test_no_cross_midnight_even_when_every_hour_is_good():
    now = datetime(2026, 7, 1, 21, tzinfo=ZoneInfo('Europe/Warsaw'))
    df = pd.DataFrame([BASE] * 8, index=pd.date_range(now, periods=8, freq='h'))
    results = best_windows(df, 'run', {}, [], now)
    assert results
    assert all(item['start'].date() == (item['end'] - pd.Timedelta(seconds=1)).date() for item in results)
