# CIDEX

CIDEX to osobny program pomocniczy dla Warsztat Menager. Nie zmienia kodu WM i nie importuje jego modułów Pythona. Korzysta wyłącznie z istniejącej struktury danych `WM_ROOT/data`.

## Zakres v1.0 — Planista

- wybór i zapamiętanie `WM_ROOT`,
- odczyt aktualnych zleceń i produktów,
- ręczne dodawanie zleceń,
- import `.xlsx`,
- porównanie Excel ↔ WM,
- podgląd różnic przed zapisem,
- jawne zaznaczenie pozycji do zapisu,
- tworzenie nowych zleceń,
- bezpieczna aktualizacja ilości i terminu,
- brak automatycznego usuwania,
- autor zmian w historii: `Cidex`.

## Etap 11 — Maszyny

CIDEX ma osobny adapter Maszyn, który czyta obecne źródła WM:

- `data/maszyny/maszyny.json`,
- awaryjnie stare `data/maszyny.json`.

Obsługiwane są oba formaty danych spotykane w WM: lista oraz dokument `{"maszyny": [...]}`. Przy zapisie CIDEX używa kanonicznego `data/maszyny/maszyny.json` i formatu używanego obecnie przez WM.

Dostępne operacje dla Cidex Mobile:

- lista Maszyn,
- karta Maszyny po istniejącym ID / `nr_ewid`,
- QR w formacie `CIDEX:MACHINE:<ID>`, np. `CIDEX:MACHINE:42`,
- zmiana statusu `Sprawna / Serwis / przegląd / Awaria`,
- dodanie uwagi do bieżącego statusu,
- dodanie zdjęcia do `data/maszyny/attachments/<ID>/...` i do istniejącego pola `status_current.photos`.

Zmiana na Awarię albo Serwis / przegląd wymaga opisu. Zapisy są oznaczane autorem `Cidex`. Adapter nie zmienia modelu danych WM — wykorzystuje istniejące pola `status_current`, `status_history` i `photos`.

## Etap 12 — API dla Cidex Mobile

Uruchom najpierw zwykły CIDEX i ustaw poprawny `WM_ROOT`. Następnie:

```bat
run_api.bat
```

Serwer pokaże m.in.:

```text
Emulator Android: http://10.0.2.2:8765
Telefon w LAN:    http://ADRES_KOMPUTERA:8765
Token:            ...
```

Telefon musi być w tej samej sieci LAN/Wi-Fi co komputer. Windows może zapytać o zgodę Zapory — zezwalaj tylko dla sieci prywatnych/firmowych.

Każde wywołanie `/api/v1/...` wymaga nagłówka:

```text
X-Cidex-Token: <token>
```

Najważniejsze endpointy:

- `GET /health`,
- `GET /api/v1/info`,
- `GET /api/v1/planista/orders`,
- `GET /api/v1/planista/products`,
- `GET /api/v1/machines`,
- `GET /api/v1/machines/<ID>`,
- `GET /api/v1/qr/resolve?code=CIDEX:MACHINE:42`,
- `POST /api/v1/machines/<ID>/status`,
- `POST /api/v1/machines/<ID>/note`,
- `POST /api/v1/machines/<ID>/photos`.

API nie daje telefonu bezpośredniego dostępu do plików `WM_ROOT`. Telefon wysyła operację do CIDEX, a CIDEX wykonuje kontrolowany zapis na komputerze.

## Zasady bezpieczeństwa Planisty

CIDEX nie usuwa automatycznie zleceń. Pozycja `Usunięte w Excelu` jest wyłącznie informacją.

Nowe zlecenia tworzone przez CIDEX nie rezerwują materiałów i nie modyfikują magazynu. Aktualizacja ilości jest blokowana, gdy istniejące zlecenie ma rezerwacje materiałowe albo chroniony status. Dzięki temu CIDEX nie próbuje odtwarzać wewnętrznej logiki rezerwacji Warsztat Menager.

## Uruchomienie aplikacji PC

```bat
run.bat
```

Przy pierwszym uruchomieniu zostaną doinstalowane wymagane biblioteki.

## Budowa EXE

```bat
build_exe.bat
```

Po udanym buildzie pojawią się:

```text
Cidex.exe
Cidex_Api.exe
```

`Cidex_Api.exe` jest na razie osobnym procesem serwera dla Mobile. Docelowo serwer zostanie sterowany z głównego `Cidex.exe`, po ustabilizowaniu komunikacji z aplikacją Android.

## Excel

Wymagane kolumny są rozpoznawane m.in. jako:

- `Nr zlec.` / `Nr zlecenia` / `Zlecenie wew`,
- `Produkt` / `Oznaczenie` / `Kod produktu`,
- `Ilość`.

Opcjonalne:

- `Data wysyłki` / `Termin`,
- `Proces`.

Produkt jest dopasowywany najpierw po kodzie WM, a następnie po jednoznacznej nazwie.

## Struktura

- `main.py` — interfejs CIDEX,
- `cidex_config.py` — `WM_ROOT`, token i port API,
- `wm_store.py` — Planista: odczyt i kontrolowany zapis danych WM,
- `machine_store.py` — Maszyny: odczyt, QR, statusy, uwagi i zdjęcia,
- `api_server.py` — lokalne API dla Cidex Mobile,
- `excel_reader.py` — odczyt `.xlsx`,
- `excel_diff.py` — porównanie Excel ↔ WM,
- `sync_service.py` — zastosowanie wyłącznie zatwierdzonych zmian.

Kod repozytorium Warsztat-Menager pozostaje niezależny i nie jest przez CIDEX modyfikowany.
