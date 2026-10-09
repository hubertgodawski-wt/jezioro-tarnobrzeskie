"""Jezioro Tarnobrzeskie – cztery zakładki, bez kont i abonamentów."""
from datetime import datetime, timedelta, timezone
from threading import Lock
from zoneinfo import ZoneInfo
import streamlit as st

from lake.config import APP_TITLE, TIMEZONE, DEFAULT_ZONE
from lake.data_sources import get_primary, get_comparison, get_imgw_warnings, WeatherAPIError
from lake.preferences import load_preferences
from lake.ratings import SPORTS, LEVEL_SPORTS
from lake.ui import css_for, show_today, show_activities, show_wind, show_forecast

st.set_page_config(page_title=APP_TITLE, page_icon="🌊", layout="wide", initial_sidebar_state="collapsed")

@st.cache_data(ttl=1800, show_spinner=False)
def primary_cached():
    return get_primary()


@st.cache_resource(show_spinner=False)
def latest_good_forecast():
    # Współdzielony tylko w bieżącej instancji serwera; znika po restarcie.
    return {"lock": Lock(), "forecast": None}


def obtain_weather():
    """Zwróć prognozę i informację o ewentualnej awarii źródła."""
    store = latest_good_forecast()
    try:
        value = primary_cached()
        with store["lock"]:
            store["forecast"] = value
        return value, False
    except (WeatherAPIError, ValueError, KeyError):
        with store["lock"]:
            backup = store["forecast"]
        if backup is not None and datetime.now(timezone.utc) - backup.fetched_at <= timedelta(hours=3):
            return backup, True
        raise

@st.cache_data(ttl=3600, show_spinner=False)
def model_cached(model):
    return get_comparison(model)

@st.cache_data(ttl=600, show_spinner=False)
def imgw_cached():
    return get_imgw_warnings()

prefs = load_preferences()
theme = prefs["theme"]
if theme == "auto":
    theme = getattr(st.session_state.get("lake_preferences_bridge"), "system", "light")
css_for(theme)

heading, settings = st.columns([7, 2], vertical_alignment="center")
with heading:
    st.markdown("<div class='lake-name'>🌊 Jezioro Tarnobrzeskie</div><div class='lake-muted'>Pogoda · Sport · Rekreacja</div>", unsafe_allow_html=True)
with settings:
    with st.popover("⚙️ Ustawienia", width="stretch"):
        st.markdown("**Wygląd i preferencje**")
        theme_opts = ["auto", "light", "dark"]
        val = st.selectbox("Motyw", theme_opts, index=theme_opts.index(prefs["theme"]), format_func=lambda x: {"auto":"Automatyczny", "light":"Jasny", "dark":"Ciemny"}[x])
        if val != prefs["theme"]:
            prefs["theme"] = val
            st.rerun()
        unit_opts = ["bft", "kmh", "knots", "ms"]
        unit = st.selectbox("Preferowana jednostka wiatru", unit_opts, index=unit_opts.index(prefs["wind_unit"]),
                            format_func=lambda x: {"bft":"Beaufort (Bft)", "kmh":"km/h", "knots":"Węzły", "ms":"m/s"}[x])
        if unit != prefs["wind_unit"]:
            prefs["wind_unit"] = unit
            st.rerun()
        names = list(SPORTS)
        favorite_choices = st.multiselect("Ulubione aktywności", names, default=prefs["favorites"], format_func=lambda x: SPORTS[x][0])
        if favorite_choices != prefs["favorites"]:
            prefs["favorites"] = favorite_choices
            st.rerun()
        with st.expander("Poziomy doświadczenia"):
            for sport in sorted(LEVEL_SPORTS):
                level = st.selectbox(SPORTS[sport][0], ["beginner", "advanced"],
                                     index=["beginner", "advanced"].index(prefs["levels"][sport]),
                                     format_func=lambda x: "Początkujący" if x == "beginner" else "Zaawansowany", key=f"settings_level_{sport}")
                if level != prefs["levels"][sport]:
                    prefs["levels"][sport] = level
                    st.rerun()
        if st.button("🔄 Pobierz nowe dane", help="Czyści pamięć cache; nie używaj zbyt często"):
            primary_cached.clear()
            model_cached.clear()
            imgw_cached.clear()
            st.rerun()

if "lake_nav" not in st.session_state:
    st.session_state["lake_nav"] = "Dzisiaj"

@st.fragment(run_every="5m")
def content():
    now = datetime.now(ZoneInfo(TIMEZONE))
    with st.spinner("Sprawdzam prognozę…"):
        try:
            forecast, stale = obtain_weather()
        except (WeatherAPIError, ValueError, KeyError):
            st.error("Nie można pobrać prognozy Open-Meteo. Brak wystarczająco aktualnych danych, więc wstrzymuję prezentowanie ocen.")
            st.stop()
        if stale:
            st.warning("Nie udało się odświeżyć prognozy. Wyświetlam ostatnie zapisane dane – sprawdź godzinę pobrania. Zalecenia dla sportów wodnych wymagają dodatkowej weryfikacji na miejscu.")
        try:
            warnings = imgw_cached()
        except (WeatherAPIError, ValueError, KeyError):
            warnings = None  # Nie zamieniamy braku połączenia na brak ostrzeżeń.
    df = forecast.data
    if df.empty:
        st.error("Brak godzinowych danych prognozy")
        st.stop()
    page = st.session_state["lake_nav"]
    if page == "Dzisiaj":
        show_today(df, forecast.fetched_at, prefs, warnings, now, theme)
    elif page == "Aktywności":
        show_activities(df, prefs, warnings, now)
    elif page == "Wiatr":
        others = {}
        errors = []
        for name in ("ECMWF IFS", "DWD ICON"):
            try:
                others[name] = model_cached(name)
            except (WeatherAPIError, ValueError, KeyError):
                errors.append(f"Dane modelu {name} są teraz niedostępne.")
        show_wind(df, {"primary": forecast, "other": others, "errors": errors}, prefs, now, theme)
    elif page == "Prognoza":
        show_forecast(df, prefs, now, theme)

content()
with st.bottom:
    st.segmented_control("Nawigacja", ["Dzisiaj", "Aktywności", "Wiatr", "Prognoza"], key="lake_nav", label_visibility="collapsed", selection_mode="single", width="stretch")

st.caption("Źródła: [Open-Meteo](https://open-meteo.com/) (CC BY 4.0, warunki użycia) · [IMGW-PIB](https://danepubliczne.imgw.pl/). Oceny to prototypowe wskazówki pogodowe, nie potwierdzenie bezpieczeństwa. Temperatura wody i status kąpielisk: brak danych.")
