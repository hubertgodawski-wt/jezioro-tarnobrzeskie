"""Deterministyczne podsumowania i wybór ciągłych okien pogodowych."""
from __future__ import annotations
from datetime import datetime
import pandas as pd
from .ratings import score_hour, SPORTS
from .data_sources import active_water_warning


def _eval(sport: str, when, row, levels: dict, warnings: list | None):
    return score_hour(
        sport,
        row,
        levels.get(sport, "beginner"),
        active_water_warning(warnings, when.to_pydatetime()),
    )


def best_windows(df: pd.DataFrame, sport: str, levels: dict, warnings: list | None,
                 now: datetime, max_windows=3):
    """Najlepsze krótkie okna (2–5 h), bez przechodzenia przez północ.

    Nie wybieramy pojedynczej szczęśliwej godziny ani 16-godzinnych bloków.
    Okna w rezultacie nie nakładają się na siebie.
    """
    if df.empty:
        return []
    selected = df.loc[df.index >= pd.Timestamp(now).ceil("h")]
    candidates = []
    for _, day_df in selected.groupby(selected.index.date):
        hours = []
        for when, row in day_df.iterrows():
            rating = _eval(sport, when, row, levels, warnings)
            value = rating.score if not rating.blocked and rating.score is not None and rating.score >= 70 else None
            hours.append((when, value))
        for i in range(len(hours)):
            for duration in range(2, min(5, len(hours) - i) + 1):
                part = hours[i:i + duration]
                if any(value is None for _, value in part):
                    continue
                if any(part[j][0] - part[j-1][0] != pd.Timedelta(hours=1)
                       for j in range(1, len(part))):
                    continue
                start, end = part[0][0], part[-1][0] + pd.Timedelta(hours=1)
                candidates.append({"start": start, "end": end,
                                   "score": round(sum(score for _, score in part) / duration),
                                   "hours": duration})
    # Wyższy wynik, potem dłuższe okno, potem bliższy termin.
    candidates.sort(key=lambda b: (-b["score"], -b["hours"], b["start"]))
    result = []
    for item in candidates:
        if any(not (item["end"] <= picked["start"] or item["start"] >= picked["end"]) for picked in result):
            continue
        result.append(item)
        if len(result) >= max_windows:
            break
    return result


def daily_ratings(df: pd.DataFrame, sport: str, levels: dict, warnings: list | None, now: datetime):
    upcoming = df.loc[df.index >= pd.Timestamp(now).floor("h")]
    result = []
    for day, part in upcoming.groupby(upcoming.index.date):
        scores = [x.score for when, row in part.iterrows() if (x := _eval(sport, when, row, levels, warnings)).score is not None and not x.blocked]
        result.append({"day": day, "score": round(sum(sorted(scores, reverse=True)[:3]) / min(3, len(scores))) if scores else None})
    return result


def daily_summary(df: pd.DataFrame, favorites: list[str], levels: dict, warnings: list | None, now: datetime) -> str:
    if df.empty:
        return "Nie udało się uzyskać danych do dzisiejszego podsumowania."
    today = now.date()
    today_df = df[(df.index.date == today) & (df.index >= pd.Timestamp(now).floor("h"))]
    if today_df.empty:
        return "Dzisiejsza prognoza godzinowa jest już zakończona. Sprawdź kolejny dzień."
    candidates = []
    for sport in favorites[:7]:
        if sport not in SPORTS:
            continue
        vals = [(when, _eval(sport, when, row, levels, warnings)) for when, row in today_df.iterrows()]
        usable = [(when, x.score) for when, x in vals if x.score is not None and not x.blocked]
        if usable:
            best = max(usable, key=lambda item: item[1])
            candidates.append((sport, best))
    candidates.sort(key=lambda item: -item[1][1])
    recommended = [(SPORTS[s][0], when.strftime("%H:%M"), score) for s, (when, score) in candidates if score >= 70]
    if not recommended:
        return "Dla wybranych aktywności dzisiejsza prognoza nie wskazuje wyraźnie korzystnego okna pogodowego. Sprawdź wykresy i ostrzeżenia."
    names = "; ".join(f"{name.lower()} – okolice {hour}" for name, hour, _ in recommended[:3])
    return f"Najkorzystniejsze prognozowane godziny dla Twoich aktywności: {names}. To ocena meteorologiczna, nie potwierdzenie bezpieczeństwa."
