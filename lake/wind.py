"""Siła i kierunek wiatru — wspólne jednostki w całej aplikacji.

Bft jest pochodną średniej prędkości, NIE porywów. Granice z
konwencjonalnej skali WMO odnoszą się do prędkości w m/s.
"""
from __future__ import annotations
import math
import pandas as pd

# Dolne granice 0–12 Bft w m/s, a nie zaokrąglone pełne km/h.
_BEAUFORT_START_MS = (0, 0.3, 1.6, 3.4, 5.5, 8.0, 10.8, 13.9,
                      17.2, 20.8, 24.5, 28.5, 32.7)
BFT_LABELS = [
    "Cisza", "Powiew", "Słaby wiatr", "Łagodny wiatr", "Umiarkowany wiatr",
    "Dość silny wiatr", "Silny wiatr", "Bardzo silny wiatr", "Gwałtowny wiatr",
    "Wichura", "Silna wichura", "Gwałtowna wichura", "Huragan",
]
DIRECTIONS = ("N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
              "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW")


def valid_number(value) -> float | None:
    try:
        v = float(value)
    except (ValueError, TypeError):
        return None
    return v if math.isfinite(v) else None


def beaufort(kmh: float | None) -> int | None:
    """Pełne stopnie Bft dla km/h, bez zaokrąglania km/h do całkowitych."""
    value = valid_number(kmh)
    if value is None or value < 0:
        return None
    speed_ms = value / 3.6
    return max(i for i, lower in enumerate(_BEAUFORT_START_MS) if speed_ms + 1e-10 >= lower)


def compass(degrees: float | None) -> str:
    value = valid_number(degrees)
    if value is None:
        return "—"
    return DIRECTIONS[int((value % 360 + 11.25) // 22.5) % 16]


def knots(kmh: float | None) -> float | None:
    value = valid_number(kmh)
    return None if value is None or value < 0 else value / 1.852


def convert_speed(kmh: float | None, unit: str) -> float | None:
    value = valid_number(kmh)
    if value is None or value < 0:
        return None
    if unit == "bft":
        return beaufort(value)
    if unit == "kmh":
        return value
    if unit == "knots":
        return knots(value)
    if unit == "ms":
        return value / 3.6
    raise ValueError(f"Nieznana jednostka: {unit}")


def model_spread(models: dict, when: pd.Timestamp) -> tuple[float | None, str]:
    """Rozstęp prędkości w modelach (nie prawdopodobieństwo trafności)."""
    vals = []
    for forecast in models.values():
        df = forecast.data
        if df.empty or "wind_speed_10m" not in df.columns:
            continue
        indices = df.index.get_indexer([when], method="nearest", tolerance=pd.Timedelta(minutes=45))
        if indices[0] < 0:
            continue
        v = valid_number(df.iloc[indices[0]]["wind_speed_10m"])
        if v is not None and v >= 0:
            vals.append(v)
    if len(vals) < 2:
        return None, "Za mało modeli do porównania"
    spread = max(vals) - min(vals)
    label = "Mała rozbieżność" if spread <= 7 else "Umiarkowana rozbieżność" if spread <= 15 else "Duża rozbieżność"
    return spread, label
