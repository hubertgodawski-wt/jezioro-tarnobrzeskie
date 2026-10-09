"""Przejrzysty prototyp ocen komfortu meteorologicznego; NIE jest analizą bezpieczeństwa."""
from __future__ import annotations
from dataclasses import dataclass
import pandas as pd

SPORTS = {
    "sup": ("SUP", "🏄", True, True),
    "kayak": ("Kajakarstwo", "🛶", True, True),
    "windsurf": ("Windsurfing", "⛵", True, True),
    "kite": ("Kitesurfing", "🪁", True, True),
    "sailing": ("Żeglarstwo", "⛵", True, True),
    "swim": ("Pływanie", "🏊", True, False),
    "beach": ("Plażowanie", "🏖️", False, False),
    "run": ("Bieganie", "🏃", False, False),
    "walk": ("Spacerowanie", "🚶", False, False),
    "cycle": ("Rower", "🚴", False, False),
    "volley": ("Siatkówka plażowa", "🏐", False, False),
}
WATER_SPORTS = {key for key, (_, _, water, _) in SPORTS.items() if water}
LEVEL_SPORTS = {key for key, (_, _, _, levels) in SPORTS.items() if levels}


@dataclass(frozen=True)
class Evaluation:
    score: int | None
    blocked: bool
    reasons: tuple[str, ...]


def _value(row, key: str) -> float | None:
    val = row.get(key)
    if val is None or pd.isna(val):
        return None
    return float(val)


def _penalty_outside(v: float, low: float, high: float, slope: float, cap: float) -> float:
    return min(cap, max(0.0, low - v, v - high) * slope)


def score_hour(sport: str, row, level: str = "beginner", official_water_alert: bool | None = False) -> Evaluation:
    if sport not in SPORTS:
        raise ValueError("Nieznana aktywność")
    water = sport in WATER_SPORTS
    temp = _value(row, "temperature_2m")
    apparent = _value(row, "apparent_temperature")
    wind = _value(row, "wind_speed_10m")
    gust = _value(row, "wind_gusts_10m")
    rain = _value(row, "precipitation")
    prob = _value(row, "precipitation_probability")
    uv = _value(row, "uv_index")
    is_day = _value(row, "is_day")
    code = _value(row, "weather_code")

    # Najpierw sprawdzamy zagrożenia, nawet gdy inne pola nie dotarły.
    if code is not None and int(code) in (95, 96, 99):
        return Evaluation(0, True, ("Prognozowane zjawiska burzowe",))
    if water and official_water_alert:
        return Evaluation(0, True, ("Aktywne ostrzeżenie IMGW dotyczące warunków na wodzie",))
    if water and official_water_alert is None:
        # Nie utożsamiamy braku łączności z niebezpieczną pogodą (wynik 0).
        return Evaluation(None, True, ("Nie udało się zweryfikować oficjalnych ostrzeżeń IMGW; nie rekomendujemy wyjścia na wodę",))
    if water and is_day == 0:
        return Evaluation(0, True, ("Po zmroku nie rekomendujemy aktywności na wodzie",))
    if water and ((gust is not None and gust >= 70) or (wind is not None and wind >= 55)):
        return Evaluation(0, True, ("Bardzo silny wiatr lub porywy",))

    # Brak niezbędnych danych nie może dawać dodatniej punktacji.
    needed = (("temperatury", temp), ("wiatru", wind), ("porywów", gust),
              ("opadów", rain), ("zjawisk pogodowych", code))
    missing = [name for name, value in needed if value is None]
    if missing:
        return Evaluation(None, False, ("Brak danych: " + ", ".join(missing),))

    reasons: list[str] = []
    score = 100.0
    level = level if level in ("beginner", "advanced") else "beginner"
    if sport in ("sup", "kayak", "swim"):
        optimal = (0, 11) if level == "beginner" else (0, 18)
        if sport == "kayak":
            optimal = (0, 14) if level == "beginner" else (0, 21)
        if sport == "swim":
            optimal = (0, 13)
        score -= _penalty_outside(wind, *optimal, slope=4.2, cap=65)
        score -= _penalty_outside(gust, 0, 18 if level == "beginner" else 28, slope=1.5, cap=30)
        score -= _penalty_outside(temp, 18, 29, slope=2.0, cap=25)
        reasons.append("Spokojniejszy wiatr sprzyja tej aktywności" if wind <= optimal[1] else "Wiatr utrudnia aktywność")
        if sport == "swim":
            reasons.append("Ocena dotyczy wyłącznie pogody – brak temperatury i jakości wody")
    elif sport in ("windsurf", "kite", "sailing"):
        bands = {
            "windsurf": ((8, 18), (16, 32)),
            "kite": ((12, 21), (18, 34)),
            "sailing": ((6, 18), (12, 31)),
        }
        low, high = bands[sport][int(level == "advanced")]
        score -= _penalty_outside(wind, low, high, slope=3.5, cap=65)
        score -= max(0, gust - wind - (9 if level == "beginner" else 15)) * 1.6
        score -= _penalty_outside(temp, 12, 29, slope=1.6, cap=25)
        reasons.append("Wiatr w korzystnym zakresie dla tego profilu" if low <= wind <= high else "Siła wiatru poza preferowanym zakresem")
        if gust - wind >= 17:
            reasons.append("Duża różnica między średnim wiatrem a porywami")
        if sport == "kite":
            reasons.append("Wymagana lokalna ocena akwenu i odpowiednie szkolenie")
    elif sport == "run":
        feel = apparent if apparent is not None else temp
        score -= _penalty_outside(feel, 8, 18, slope=4.0, cap=68)
        score -= _penalty_outside(wind, 0, 24, slope=1.1, cap=20)
        if uv is not None and uv >= 6:
            score -= min(14, (uv - 5) * 2.5)
            reasons.append("Wysokie promieniowanie UV")
        reasons.append("Komfortowa temperatura do biegania" if 8 <= feel <= 18 else "Temperatura obniża komfort biegania")
    elif sport in ("beach", "volley"):
        feel = apparent if apparent is not None else temp
        optimum = (23, 29) if sport == "beach" else (18, 25)
        score -= _penalty_outside(feel, *optimum, slope=4.0, cap=75)
        score -= _penalty_outside(wind, 0, 24 if sport == "beach" else 17, slope=1.9, cap=32)
        if uv is not None and uv >= 6:
            score -= min(20, (uv - 5) * 4)
            reasons.append("Wysoki UV – konieczna ochrona przeciwsłoneczna")
        reasons.append("Przyjemna temperatura" if optimum[0] <= feel <= optimum[1] else "Temperatura mniej komfortowa")
    else:  # rower / spacer
        feel = apparent if apparent is not None else temp
        optimum = (8, 23) if sport == "cycle" else (8, 24)
        score -= _penalty_outside(feel, *optimum, slope=2.7, cap=55)
        score -= _penalty_outside(wind, 0, 21 if sport == "cycle" else 29, slope=1.3, cap=30)
        reasons.append("Komfortowa temperatura" if optimum[0] <= feel <= optimum[1] else "Temperatura obniża komfort")

    if rain is not None:
        if rain >= 4:
            score -= 45
            reasons.append("Intensywne opady")
        elif rain >= 1:
            score -= 25
            reasons.append("Opady deszczu")
        elif rain > 0:
            score -= 8
    if prob is not None and prob >= 70:
        score -= 8
        reasons.append("Duże prawdopodobieństwo opadów")
    if (not water or sport == "swim") and is_day == 0 and sport in ("beach", "volley", "swim"):
        score -= 50
        reasons.append("Po zmroku warunki są mniej odpowiednie")
    if gust >= 45 and sport not in ("windsurf", "kite", "sailing"):
        reasons.append("Silne porywy wiatru")
    result = int(round(max(0, min(100, score))))
    if not reasons:
        reasons = ["Warunki oceniono na podstawie dostępnych parametrów"]
    return Evaluation(result, False, tuple(reasons[:3]))


def category(score: int | None, blocked: bool = False) -> tuple[str, str]:
    if blocked:
        return "Wstrzymana rekomendacja", "red"
    if score is None:
        return "Brak danych", "gray"
    if score >= 85:
        return "Bardzo dobre", "green"
    if score >= 70:
        return "Dobre", "green"
    if score >= 50:
        return "Przeciętne", "yellow"
    if score >= 25:
        return "Niekorzystne", "orange"
    return "Bardzo niekorzystne", "red"
