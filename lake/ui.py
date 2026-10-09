"""Wizualizacje i widoki Streamlit (w miarę możliwości przyjazne mobilnie)."""
from __future__ import annotations
from datetime import datetime
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from .ratings import SPORTS, WATER_SPORTS, LEVEL_SPORTS, category, score_hour
from .recommendations import best_windows, daily_ratings, daily_summary
from .data_sources import active_water_warning
from .wind import beaufort, BFT_LABELS, compass, knots, model_spread, convert_speed


def css_for(theme):
    background, secondary, foreground, muted, border = (
        ("#0D2030", "#18344A", "#EEF7FC", "#AAC3D2", "#29485D") if theme == "dark" else
        ("#F5FAFC", "#FFFFFF", "#142E42", "#58788B", "#D6E5EC")
    )
    st.markdown(f"""
    <style>
    html,body,[data-testid="stAppViewContainer"],.stApp {{background:{background}!important; color:{foreground};}}
    :root {{ --lake-bg:{background}; --lake-card:{secondary}; --lake-text:{foreground}; --lake-muted:{muted}; --lake-border:{border};
             --st-background-color:{background}; --st-secondary-background-color:{secondary}; --st-text-color:{foreground}; --st-primary-color:#119D9A; }}
    [data-testid="stHeader"] {{background:transparent!important;}}
    [data-testid="stMainBlockContainer"] {{max-width:1050px; padding-top:1.5rem; padding-bottom:7rem;}}
    .lake-hero {{background:linear-gradient(120deg,{secondary}, {background}); border:1px solid {border};
       border-radius:22px; padding:22px 24px; margin:10px 0 15px;}}
    .lake-eyebrow {{font-size:.8rem; color:{muted}; font-weight:600; letter-spacing:.03em;}}
    .lake-big {{font-size:clamp(2.8rem,7vw,4.1rem); font-weight:750; line-height:1.2; color:{foreground};}}
    .lake-chips {{display:flex; flex-wrap:wrap; gap:9px; margin-top:13px;}}
    .lake-chip {{background:{background}; border:1px solid {border}; padding:8px 11px; border-radius:13px; font-size:.85rem;}}
    .lake-name {{font-weight:700; font-size:clamp(1.32rem,4vw,2.0rem); line-height:1.3; color:{foreground};}}
    .lake-muted {{color:{muted}; font-size:.87rem;}}
    .lake-card {{background:{secondary}; border:1px solid {border}; border-radius:16px; padding:18px; margin:8px 0;}}
    .lake-label {{font-size:.74rem; font-weight:650; letter-spacing:.07em; text-transform:uppercase; color:{muted};}}
    .lake-stat {{font-size:1.7rem; font-weight:750; color:{foreground};}}
    [data-testid="stBottom"] {{background:{background}!important; border-top:1px solid {border};}}
    [data-testid="stMetric"] {{background:{secondary}; border:1px solid {border}; border-radius:15px; padding:13px;}}
    .stPlotlyChart {{border-radius:15px; overflow:hidden;}}
    .stButton button {{border-radius:12px;}}
    @media(max-width:650px) {{
      [data-testid="stMainBlockContainer"] {{padding-left:1rem; padding-right:1rem; padding-top:1rem;}}
      .lake-hero {{padding:16px;}}
      .lake-stat {{font-size:1.35rem;}}
      [data-testid="stBottom"] [data-testid="stSegmentedControl"] button {{font-size:.8rem;}}
    }}
    </style>
    """, unsafe_allow_html=True)


def _num(v, digits=0, unit=""):
    if v is None or pd.isna(v):
        return "—"
    return f"{float(v):.{digits}f}{unit}"


def _wind_text(kmh, units: str = "bft"):
    if kmh is None or pd.isna(kmh):
        return "—"
    return {"bft": f"{beaufort(kmh)} Bft", "kmh": f"{kmh:.0f} km/h", "knots": f"{knots(kmh):.1f} kn", "ms": f"{kmh/3.6:.1f} m/s"}.get(units, "—")


def _current(df, now):
    index = df.index.get_indexer([pd.Timestamp(now)], method="pad")
    return df.iloc[max(0, int(index[0]))], df.index[max(0, int(index[0]))]


def _chart_style(fig, theme="light", height=300):
    light = theme != "dark"
    color = "#142E42" if light else "#EDF5FF"
    fig.update_layout(
        height=height,
        margin=dict(l=7, r=7, t=20, b=7),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=color, family="sans-serif", size=12),
        legend=dict(orientation="h", y=-0.26),
        hovermode="x unified",
    )
    fig.update_xaxes(showgrid=False)
fig.update_yaxes(gridcolor="rgba(123,152,172,0.20)", zeroline=False)
return fig


def _show_alerts(warnings: list[dict] | None, now: datetime):
    if warnings is None:
        st.warning("Nie udało się sprawdzić ostrzeżeń IMGW. Brak komunikatu nie oznacza braku zagrożenia.", icon="⚠️")
        return
    for alert in warnings:
        if not (alert["start"] <= now <= alert["end"]):
            continue
        st.error(
            f"**IMGW · stopień {alert['level']} · {alert['name']}**\n\n"
            f"{alert['text']}\n\nObowiązuje do: {alert['end'].strftime('%d.%m, %H:%M')}.",
            icon="⚠️",
        )
    planned = [w for w in warnings if w["start"] > now]
    if planned:
        st.warning(f"Zapowiedziane ostrzeżenia IMGW: {', '.join(w['name'] for w in planned)}. Sprawdź szczegóły na stronie IMGW.", icon="⚠️")


def _score_badge(score, blocked):
    label, color = category(score, blocked)
    emoji = {"green": "🟢", "yellow": "🟡", "orange": "🟠", "red": "🔴", "gray": "⚪"}[color]
    return f"{emoji} {label}"


def _activity_card(sport, row, when, prefs, warnings, compact=False):
    name, emoji, water, levels = SPORTS[sport]
    evaluation = score_hour(sport, row, prefs["levels"].get(sport, "beginner"), active_water_warning(warnings, when.to_pydatetime()))
    with st.container(border=True):
        c1, c2 = st.columns([7, 2], vertical_alignment="center")
        with c1:
            st.markdown(f"**{emoji} {name}**  ")
            st.caption(_score_badge(evaluation.score, evaluation.blocked))
        with c2:
            if st.button("★" if sport in prefs["favorites"] else "☆", key=f"star_{sport}", help="Dodaj lub usuń z ulubionych"):
                from .preferences import toggle_favorite
                toggle_favorite(sport)
        if evaluation.score is None:
            st.caption("Ocena wstrzymana – brak danych lub weryfikacji ostrzeżeń" if evaluation.blocked else "Nie można policzyć wyniku – brak danych")
        else:
            st.progress(evaluation.score / 100, text=f"{evaluation.score}/100 · ocena meteorologiczna")
        if not compact:
            for reason in evaluation.reasons[:2]:
                st.caption("• " + reason)
            if water:
                st.caption("Ocena nie uwzględnia temperatury wody ani lokalnych zagrożeń.")


def show_today(df, fetched_at, prefs, warnings, now, theme):
    row, when = _current(df, now)
    wind = row.get("wind_speed_10m")
    gust = row.get("wind_gusts_10m")
    temp = row.get("temperature_2m")
    desc = "Prognoza modelowa dla jeziora · nie pomiar stacji"
    _show_alerts(warnings, now)  # Zagrożenia ponad zwykłą prognozą.
    st.markdown(
        f"<div class='lake-hero'><div class='lake-eyebrow'>PROGNOZA DLA JEZIORA · {when.strftime('%H:%M')}</div>"
        f"<div class='lake-big'>{_num(temp, 0, '°C')}</div>"
        f"<div class='lake-muted'>{desc}</div>"
        f"<div class='lake-chips'><span class='lake-chip'>💨 {_wind_text(wind, 'bft')} · {BFT_LABELS[beaufort(wind)] if beaufort(wind) is not None else 'brak danych'}</span>"
        f"<span class='lake-chip'>📏 {_wind_text(wind, prefs['wind_unit'] if prefs['wind_unit'] != 'bft' else 'kmh')}</span>"
        f"<span class='lake-chip'>🧭 {compass(row.get('wind_direction_10m'))}</span>"
        f"<span class='lake-chip'>💥 Porywy {_num(gust, 0, ' km/h')}</span>"
        f"<span class='lake-chip'>☀️ UV {_num(row.get('uv_index'), 1)}</span></div></div>",
        unsafe_allow_html=True,
    )
    st.caption(f"Źródło: Open-Meteo Best Match · pobrano {fetched_at.astimezone(now.tzinfo).strftime('%d.%m.%Y o %H:%M')} · współrzędne jeziora")
    st.subheader("✨ Dzisiaj nad jeziorem")
    st.info(daily_summary(df, prefs["favorites"] or ["run", "sup", "beach"], prefs["levels"], warnings, now), icon="💡")
    st.subheader("★ Moje aktywności")
    if not prefs["favorites"]:
        st.caption("Wybierz ulubione aktywności w zakładce Aktywności lub ustawieniach.")
    for sport in prefs["favorites"]:
        if sport in SPORTS:
            _activity_card(sport, row, when, prefs, warnings, compact=True)
    st.subheader("Nadchodzące dni")
    _daily_overview(df, now)
    st.caption("Wyniki 0–100 są orientacyjną oceną dopasowania pogody, a nie oceną bezpieczeństwa. Przed wejściem na wodę sprawdź warunki lokalne.")


def _daily_overview(df, now):
    upcoming = df.loc[df.index >= pd.Timestamp(now).floor("h")]
    rows = []
    for day, part in upcoming.groupby(upcoming.index.date):
        temp = part.get("temperature_2m")
        wind = part.get("wind_speed_10m")
        if temp is None or wind is None:
            continue
        rows.append({
            "Dzień": pd.Timestamp(day).strftime("%a %d.%m"),
            "Temp. min": _num(temp.min(), 0, "°C"),
            "Temp. max": _num(temp.max(), 0, "°C"),
            "Wiatr maks.": _wind_text(float(wind.max())),
        })
    if rows:
        st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)


def show_activities(df, prefs, warnings, now):
    st.subheader("Aktywności nad jeziorem")
    row, when = _current(df, now)
    favorites = [s for s in prefs["favorites"] if s in SPORTS]
    for sport in favorites + [s for s in SPORTS if s not in favorites]:
        _activity_card(sport, row, when, prefs, warnings)
    st.divider()
    sport = st.selectbox("Sprawdź najlepsze godziny dla aktywności", list(SPORTS), format_func=lambda s: f"{SPORTS[s][1]} {SPORTS[s][0]}")
    if sport in LEVEL_SPORTS:
        level = st.radio("Poziom doświadczenia", ["beginner", "advanced"], index=["beginner", "advanced"].index(prefs["levels"][sport]),
                         format_func=lambda x: "Początkujący" if x == "beginner" else "Zaawansowany", horizontal=True, key=f"level_control_{sport}")
        if level != prefs["levels"][sport]:
            prefs["levels"][sport] = level
            st.rerun()
    windows = best_windows(df, sport, prefs["levels"], warnings, now)
    st.markdown("**Najkorzystniejsze ciągłe okna pogodowe (7 dni)**")
    if windows:
        for win in windows:
            end_label = win['end'].strftime('%d.%m %H:%M') if win['start'].date() != win['end'].date() else win['end'].strftime('%H:%M')
            st.success(f"{win['start'].strftime('%d.%m %H:%M')}–{end_label} · średnia ocena {win['score']}/100")
    else:
        st.info("Brak co najmniej dwugodzinnych przedziałów o ocenie 70/100 lub wyższej.")
    daily = daily_ratings(df, sport, prefs["levels"], warnings, now)
    if daily:
        st.dataframe(pd.DataFrame([{"Dzień": d["day"].strftime("%d.%m"), "Najlepsze godziny (średnia z 3)": f"{d['score']}/100" if d["score"] is not None else "—"} for d in daily]), hide_index=True, use_container_width=True)
    st.caption("Progi są eksperymentalne; oceny należy zweryfikować na podstawie doświadczeń lokalnych użytkowników i obserwacji. Nie są instrukcją bezpieczeństwa.")


def show_wind(df, models, prefs, now, theme):
    st.subheader("Wiatr nad jeziorem")
    row, when = _current(df, now)
    speed = row.get("wind_speed_10m")
    gust = row.get("wind_gusts_10m")
    direction = row.get("wind_direction_10m")
    a, b, c = st.columns(3)
    a.metric("Siła wiatru", f"{beaufort(speed)} Bft" if beaufort(speed) is not None else "—")
    b.metric("Prędkość", _num(speed, 0, " km/h"))
    c.metric("Porywy", _num(gust, 0, " km/h"))
    st.caption(f"{_num(speed, 1, ' km/h')} · {_num(knots(speed), 1, ' węzłów')} · {_num(speed / 3.6 if speed is not None else None, 1, ' m/s')}")
    st.markdown("**Róża kierunku wiatru – kierunek, Z KTÓREGO wieje**")
    if direction is not None and not pd.isna(direction):
        fig = go.Figure()
        fig.add_trace(go.Scatterpolar(r=[0, 0.9], theta=[direction, direction], mode="lines+markers",
                                       line=dict(color="#14B8A6", width=7), marker=dict(size=[1, 15], color="#14B8A6"), showlegend=False))
        fig.update_layout(polar=dict(radialaxis=dict(visible=False, range=[0, 1]),
                                     angularaxis=dict(direction="clockwise", rotation=90, tickmode="array", tickvals=[0, 45, 90, 135, 180, 225, 270, 315], ticktext=["N", "NE", "E", "SE", "S", "SW", "W", "NW"])))
        st.plotly_chart(_chart_style(fig, theme, 270), use_container_width=True, config={"displayModeBar": False})
        st.caption(f"Kierunek: {compass(direction)} ({direction:.0f}°). Wykres jest kompasem, nie pomiarem wiatru w porcie.")
    else:
        st.warning("Brak prognozy kierunku wiatru.")
    sub = df.loc[df.index >= pd.Timestamp(now).floor("h")].head(48)
    chart_unit = prefs.get("wind_unit", "bft")
    if chart_unit == "bft":
        chart_unit = "kmh"  # Porywów nie przeliczamy na stopnie Beauforta.
    unit_text = {"kmh": "km/h", "knots": "węzły", "ms": "m/s"}[chart_unit]
    st.markdown(f"**Prognoza godzinowa: wiatr i porywy ({unit_text})**")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=sub.index, y=sub["wind_speed_10m"].apply(lambda x: convert_speed(x, chart_unit)),
                            name="Wiatr średni", line=dict(color="#0EA5A4", width=3)))
    fig.add_trace(go.Scatter(x=sub.index, y=sub["wind_gusts_10m"].apply(lambda x: convert_speed(x, chart_unit)),
                            name="Porywy", line=dict(color="#EA8B38", width=2)))
    fig.update_yaxes(title=unit_text)
    st.plotly_chart(_chart_style(fig, theme, 320), use_container_width=True, config={"displayModeBar": False})
    st.markdown("**Wiatr w skali Beauforta – kolejne 48 godzin**")
    if "wind_speed_10m" in sub:
        bft_values = sub["wind_speed_10m"].apply(beaufort)
        bft_fig = go.Figure()
        bft_fig.add_trace(go.Scatter(x=sub.index, y=bft_values, mode="lines+markers", name="Siła wiatru (Bft)", line=dict(color="#0EA5A4", shape="hv", width=3)))
        bft_fig.update_yaxes(title="Bft", range=[-0.2, 12.2], dtick=1)
        st.plotly_chart(_chart_style(bft_fig, theme, 260), use_container_width=True, config={"displayModeBar": False})
    st.markdown("**Kierunek i porywy w kolejnych godzinach**")
    hour_table = sub[[k for k in ("wind_speed_10m", "wind_gusts_10m", "wind_direction_10m") if k in sub]].copy()
    if not hour_table.empty:
        hour_table["Bft"] = hour_table["wind_speed_10m"].apply(lambda v: f"{beaufort(v)} Bft" if beaufort(v) is not None else "—")
        hour_table["Kierunek"] = hour_table["wind_direction_10m"].apply(compass)
        hour_table = hour_table.rename(columns={"wind_speed_10m": "Wiatr km/h", "wind_gusts_10m": "Porywy km/h"})
        hour_table = hour_table.drop(columns=["wind_direction_10m"])[["Bft", "Wiatr km/h", "Porywy km/h", "Kierunek"]]
        hour_table.index = hour_table.index.strftime("%d.%m %H:%M")
        hour_table.index.name = "Czas"
        st.dataframe(hour_table, use_container_width=True)
    st.subheader("Porównanie modeli")
    for name in models.get("errors", []):
        st.caption("⚠️ " + name)
    available = {"Best Match": models["primary"], **models.get("other", {})}
    fig = go.Figure()
    for name, forecast in available.items():
        piece = forecast.data.loc[forecast.data.index >= pd.Timestamp(now).floor("h")].head(48)
        if "wind_speed_10m" in piece:
            fig.add_trace(go.Scatter(x=piece.index, y=piece["wind_speed_10m"], mode="lines", name=name))
    fig.update_yaxes(title="Wiatr średni (km/h)")
    st.plotly_chart(_chart_style(fig, theme, 320), use_container_width=True, config={"displayModeBar": False})
    spread, label = model_spread(available, when)
    if spread is None:
        st.info("Brak wystarczającej liczby modeli do porównania.")
    else:
        st.info(f"**{label}: {spread:.1f} km/h** różnicy między modelami dla bieżącej godziny. Nie jest to prognoza prawdopodobieństwa.")
    st.caption("Ważne: porywy mogą odnosić się do różnych przedziałów czasu w poszczególnych modelach, dlatego nie łączymy ich w jedną średnią. Obrys jeziora i pomiary z portów zaplanowano na kolejny etap.")


def show_forecast(df, prefs, now, theme):
    st.subheader("Prognoza na 7 dni")
    _daily_overview(df, now)
    days = list(dict.fromkeys(df.index.date))
    future = [day for day in days if day >= now.date()]
    if not future:
        st.warning("Brak dni prognozy")
        return
    date = st.selectbox("Wybierz dzień", future, format_func=lambda d: pd.Timestamp(d).strftime("%A %d.%m.%Y"))
    part = df.loc[df.index.date == date]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=part.index, y=part["temperature_2m"], mode="lines+markers", name="Temperatura", line=dict(color="#0EA5A4", width=3)))
    if "apparent_temperature" in part:
        fig.add_trace(go.Scatter(x=part.index, y=part["apparent_temperature"], mode="lines", name="Odczuwalna", line=dict(color="#F59E0B", dash="dot")))
    fig.update_yaxes(title="°C")
    st.plotly_chart(_chart_style(fig, theme), use_container_width=True, config={"displayModeBar": False})
    fig = go.Figure()
    fig.add_trace(go.Bar(x=part.index, y=part["precipitation"], name="Opady (mm)", marker_color="#3B82F6"))
    fig.update_yaxes(title="Opady (mm)")
    st.plotly_chart(_chart_style(fig, theme, 240), use_container_width=True, config={"displayModeBar": False})
    columns = [x for x in ("temperature_2m", "wind_speed_10m", "wind_gusts_10m", "precipitation_probability", "uv_index") if x in part]
    formatted = part[columns].copy()
    formatted.index = formatted.index.strftime("%H:%M")
    formatted.index.name = "Godzina"
    formatted.rename(columns={"temperature_2m":"Temperatura °C", "wind_speed_10m":"Wiatr km/h", "wind_gusts_10m":"Porywy km/h", "precipitation_probability":"Opady %", "uv_index":"UV"}, inplace=True)
    st.dataframe(formatted.round(1), use_container_width=True)
    st.caption("Prognozy na dalsze dni są obarczone większą niepewnością. Nie przedstawiają pomiarów temperatury wody ani statusu kąpielisk.")
