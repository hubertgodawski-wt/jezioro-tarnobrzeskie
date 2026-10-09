# Historia zmian

## 0.2.0 — ulepszony prototyp

- Poprawna, dokładna konwersja prędkości na skalę Beauforta z granic m/s (w tym okolice progów pomiędzy stopniami).
- W zakładce „Wiatr” dodatkowe wykresy 48 h w Bft, tabela porywów/kierunków i wykres prędkości z jednostkami zgodnymi z preferencją użytkownika.
- Prognozowane burze mają pierwszeństwo przed wyliczaniem punktacji nawet przy brakujących danych.
- Gdy IMGW jest nieosiągalne, wodne rekomendacje są wstrzymywane z wynikiem „brak weryfikacji”, nie z fałszywą oceną pogodową 0/100.
- Ostrzeżenia zaplanowane i aktywne rozróżniane na podstawie bieżącego czasu, także przy danych z pamięci podręcznej.
- Dostępna awaryjna ostatnia prognoza z pamięci serwera (do 3 h), oznaczona ostrzeżeniem.
- Wybór okien 2–5 h, bez przejścia przez północ, bez nakładających się rekomendacji i bez częściowej aktualnej godziny.
- Staranniejsza kontrola duplikatów czasu, pustych danych kluczowych i struktury alertów IMGW.
- Testy (`pytest.ini`) i GitHub Actions; 20 testów logiki bez konieczności podłączania internetu.

## 0.1.0 — MVP

- Cztery zakładki, 7-dniowa prognoza, Open-Meteo i IMGW, oceny aktywności, motywy i ulubione w przeglądarce.

## Pozostało przed publicznym wdrożeniem

- Rzeczywisty test aplikacji w przeglądarce z zainstalowanym Streamlit 1.65, na telefonie i komputerze.
- Testy pobierania danych z Open-Meteo i IMGW na serwerze Streamlit Community Cloud.
- Dalsza kalibracja heurystyk ocen w oparciu o obserwacje i doświadczenia lokalnych użytkowników.
- Opcjonalny dokładny obrys jeziora na róży wiatrów dopiero po pozyskaniu danych geograficznych.
