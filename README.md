# 🌊 Jezioro Tarnobrzeskie – Pogoda i Aktywności

Mobilna aplikacja pogodowa (Streamlit) dla Jeziora Tarnobrzeskiego. **Wersja 0.2 / prototyp algorytmów**; bez fikcyjnych pomiarów. Prognozy liczone dla punktu `50.54478 N, 21.64471 E` (jezioro). Kod TERYT miasta Tarnobrzega dla ostrzeżeń IMGW: `1864`.

## Funkcje

- 4 zakładki: **Dzisiaj**, **Aktywności**, **Wiatr**, **Prognoza**; mobilna nawigacja u dołu.
- 7 dni prognozy, szczegóły godzinowe, temperatura odczuwalna, opady, UV.
- Wiatr: **Bft** liczony z dokładnych progów m/s, km/h, węzły, m/s, porywy, kierunek i kompas, wykres godzinowy w Bft oraz tabela 48 h. Dodatkowo wykresy i porównanie prognoz ECMWF IFS i DWD ICON (jeśli dostępne).
- 11 aktywności, w tym SUP, kajaki, żeglarstwo, windsurfing, kitesurfing, pływanie, plażowanie, bieganie, spacery, rower i siatkówka plażowa.
- Heurystyczne oceny 0–100, osobne poziomy początkujący / zaawansowany dla wybranych sportów wodnych; wybór ulubionych i najlepszych niepokrywających się przedziałów 2–5 godzin.
- Ostrzeżenia IMGW dla **miasta Tarnobrzeg**, nie dla powiatu tarnobrzeskiego. Rozróżnienie braku ostrzeżeń i niedostępności danych.
- Zapis preferencji w **localStorage** przeglądarki bez konta, dzięki natywnemu komponentowi Streamlit v2.
- Motyw jasny / ciemny / automatyczny (odczyt systemowej preferencji przy uruchomieniu).

## Uruchamianie lokalnie

Wymagany Python 3.11 lub nowszy.

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## Publikacja na Streamlit Community Cloud

1. Utwórz nowe repozytorium na GitHub i wrzuć zawartość tego katalogu (tak, żeby `app.py` i `requirements.txt` były w katalogu głównym repozytorium).
2. Zaloguj się w [Streamlit Community Cloud](https://share.streamlit.io/), wybierz **Create app / Deploy** i wskaż repozytorium, gałąź oraz plik `app.py`.
3. Po zakończeniu wdrożenia aplikacja będzie dostępna pod adresem `.streamlit.app`. Aktualizacja kodu repozytorium uruchomi nowe wdrożenie.

Nie ma tu kluczy API. W niekomercyjnej wersji Open-Meteo stosuj się do limitów i zasad atrybucji. **Kwestia komercyjnego wykorzystania wymaga ponownego sprawdzenia licencji i warunków API.**

## Testy

```bash
pip install -r requirements-dev.txt
pytest -q
```

## Struktura

- `app.py`: Streamlit, cache, nawigacja i odświeżanie.
- `lake/config.py`: lokalizacja; przygotowane do przyszłych stref jeziora.
- `lake/data_sources.py`: zewnętrzne źródła, walidacja, filtrowanie ostrzeżeń.
- `lake/wind.py`: skala Beauforta, kierunek, rozbieżność modeli.
- `lake/ratings.py`: heurystyczne oceny aktywności.
- `lake/recommendations.py`: okna pogodowe i krótkie opisy.
- `lake/preferences.py`: personalizacja w localStorage.
- `lake/ui.py`: cztery widoki, karty, wykresy.
- `tests/`: testy jednostkowe oparte na syntetycznych danych (20 scenariuszy).
- `.github/workflows/tests.yml`: automatyczne testy po przesłaniu zmian na GitHub.
- `CHANGELOG.md`: historia zmian i otwarte punkty jakości.

## Aktualizacja i błędy

`st.cache_data` buforuje: prognozę podstawową 30 min, modele porównawcze 60 min, ostrzeżenia IMGW 10 min. W aktywnej sesji fragment strony odświeża się co 5 min. Po awarii Open-Meteo aplikacja może pokazać **ostatnio pobraną rzeczywistą prognozę** z pamięci serwera (najwyżej 3 godziny od jej pobrania), z wyraźną informacją o awarii. Po upływie tego okresu wstrzymuje prezentowanie prognozy. Awaryjna pamięć znika po restarcie instancji Streamlit Community Cloud. **Nie ma symulowanych danych pogodowych.** Przy niedostępności ostrzeżeń IMGW rekomendacje sportów wodnych są wstrzymane, bez sugerowania, że pogoda ma wynik 0/100.

## Ograniczenia – ważne

- Prognoza dla współrzędnych jeziora to **model**, nie odczyt z lokalnej stacji; 7-dniowe prognozy i lokalne porywy mogą znacząco odbiegać od rzeczywistości.
- Skala 0–100 ocenia tylko **dopasowanie pogody**. Nie stwierdza, czy aktywność jest bezpieczna, dozwolona lub nadzorowana. Progi są wstępne, wymagają kalibracji z użytkownikami i lokalnymi obserwacjami.
- Brak temperatury wody, jakości wody, aktualnego statusu kąpielisk, pomiarów fal i rzeczywistych pomiarów z portów.
- Róża wiatru to **schemat kompasu**; dokładny obrys jeziora na podkładzie mapowym będzie dodany po pozyskaniu odpowiednich danych geograficznych.
- Prognozy różnych modeli mogą mieć inną siatkę przestrzenną, czas aktualizacji i definicję porywów. Porównanie średniej prędkości jest orientacyjne, nie jest zweryfikowaną miarą prawdopodobieństwa trafności.
- Cache w Streamlit Community Cloud nie jest magazynem trwałym, a aplikacja może zostać uśpiona. Zbieranie całodobowych danych z przyszłych stacji wymaga osobnej usługi/bazy.
- Ulubione i poziomy są zapisane tylko w konkretnej przeglądarce/profilu. Czyszczenie danych przeglądarki je usunie.

## Źródła

- Open-Meteo Forecast API: https://open-meteo.com/en/docs
- ECMWF API: https://open-meteo.com/en/docs/ecmwf-api
- DWD ICON API: https://open-meteo.com/en/docs/dwd-api
- IMGW public API: https://dane.imgw.pl/apiinfo
- Streamlit Community Cloud: https://docs.streamlit.io/deploy/streamlit-community-cloud

## Przyszłe etapy

Stacje meteorologiczne w portach, archiwum pomiarów, weryfikacja modeli, podział jeziora na strefy, temperatura i jakość wody (tylko jeśli znajdziemy wiarygodne źródło danych).

## Test odbiorczy po opublikowaniu

1. Otwórz aplikację na smartfonie. Sprawdź, czy na dole ekranu są zakładki **Dzisiaj**, **Aktywności**, **Wiatr**, **Prognoza**.
2. Sprawdź, czy na stronie głównej i w zakładce **Wiatr** widoczne są stopnie Bft, prędkość, porywy oraz kierunek (to prognoza, nie pomiar).
3. W zakładce **Wiatr** sprawdź wykres Bft, tabelę 48 h i porównanie modeli. Niedostępny model powinien pojawić się jako komunikat, nie pusty wykres udający dane.
4. Zaznacz lub usuń ulubioną aktywność; odśwież stronę i ponownie otwórz aplikację w tej samej przeglądarce. Preferencja powinna pozostać zapisana.
5. Przełącz poziom początkujący / zaawansowany dla SUP-u i sprawdź, czy ocena zmienia się tam, gdzie warunki różnicują oba profile.
6. Przełącz jasny / ciemny / automatyczny motyw i sprawdź kontrast w obu wariantach.
7. Sprawdź zachowanie po braku dostępu do IMGW: aplikacja ma pokazać, że ostrzeżeń nie udało się zweryfikować, a nie „Brak zagrożeń”.
8. Zmniejsz szerokość ekranu do ok. 360 px. Żaden ważny komunikat i przycisk nie powinien zostać obcięty.

Do zakończenia odbioru nie nazywamy projektu wersją produkcyjną. Wyniki testów automatycznych nie zastępują testu w przeglądarce.
