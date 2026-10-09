"""Lokalny magazyn preferencji za pomocą oficjalnych komponentów Streamlit v2."""
from __future__ import annotations
import json
import streamlit as st
from .ratings import SPORTS, LEVEL_SPORTS

DEFAULTS = {
    "favorites": ["run", "sup", "beach"],
    "levels": {s: "beginner" for s in LEVEL_SPORTS},
    "theme": "auto",
    "wind_unit": "bft",
}

BRIDGE_JS = r"""
export default function({data, setStateValue}) {
  const KEY = "jezioro_tarnobrzeskie_preferences_v1";
  try {
    const media = window.matchMedia("(prefers-color-scheme: dark)");
    const updateTheme = () => setStateValue("system", media.matches ? "dark" : "light");
    updateTheme();
    media.addEventListener("change", updateTheme);
    if (data?.mode === "read") {
      const found = localStorage.getItem(KEY);
      setStateValue("json", found || "{}");
    } else if (data?.mode === "write") {
      const value = JSON.stringify(data?.preferences || {});
      if (localStorage.getItem(KEY) !== value) localStorage.setItem(KEY, value);
    }
    return () => media.removeEventListener("change", updateTheme);
  } catch (err) {
    if (data?.mode === "read") setStateValue("json", "{}");
  }
}
"""

bridge = st.components.v2.component(name="lake_local_preferences", html="<span></span>", js=BRIDGE_JS)


def sanitize(data):
    if not isinstance(data, dict):
        data = {}
    favs = data.get("favorites", DEFAULTS["favorites"])
    if not isinstance(favs, list):
        favs = DEFAULTS["favorites"]
    levels = data.get("levels", {})
    if not isinstance(levels, dict):
        levels = {}
    return {
        "favorites": list(dict.fromkeys(s for s in favs if isinstance(s, str) and s in SPORTS)),
        "levels": {s: levels.get(s, "beginner") if levels.get(s) in ("beginner", "advanced") else "beginner" for s in LEVEL_SPORTS},
        "theme": data.get("theme") if data.get("theme") in ("auto", "light", "dark") else "auto",
        "wind_unit": data.get("wind_unit") if data.get("wind_unit") in ("bft", "kmh", "knots", "ms") else "bft",
    }


def load_preferences():
    loaded = "lake_prefs" in st.session_state
    result = bridge(
        data={"mode": "write" if loaded else "read", "preferences": st.session_state.get("lake_prefs", {})},
        default={"json": "", "system": "light"},
        key="lake_preferences_bridge",
        on_json_change=lambda: None,
        on_system_change=lambda: None,
    )
    if not loaded:
        raw = result.json
        if not raw:
            st.caption("Wczytywanie ustawień zapisanych na urządzeniu…")
            st.stop()
        try:
            saved = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            saved = {}
        st.session_state["lake_prefs"] = sanitize(saved if saved else DEFAULTS)
        st.rerun()
    return st.session_state["lake_prefs"]


def toggle_favorite(sport: str):
    prefs = st.session_state["lake_prefs"]
    favs = prefs["favorites"]
    prefs["favorites"] = [s for s in favs if s != sport] if sport in favs else favs + [sport]
    st.rerun()
