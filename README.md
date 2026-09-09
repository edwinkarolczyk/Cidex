# CIDEX

CIDEX to osobny program pomocniczy dla Warsztat Menager. Nie zmienia kodu WM i nie importuje jego modułów Pythona. Korzysta wyłącznie z istniejącej struktury danych `WM_ROOT/data`.

## Zakres v1.1 — Planista + Mobile

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
- autor zmian w historii: `Cidex`,
- lokalne API dla Cidex Mobile,
- uruchamianie i zatrzymywanie Mobile API z głównego `Cidex.exe`.

## Planista — zasady z pliku projektu

CIDEX pozostaje zewnętrznym „dokładaczem / synchronizatorem wejściowym” dla Planisty. Excel jest wyłącznie źródłem odczytu, a zapis następuje tylko do bieżącego `WM_ROOT` i tylko dla jawnie zatwierdzonych operacji `Utwórz` / `Aktualizuj`.

`Usunięte w Excelu` jest informacją — CIDEX nie wykonuje automatycznego delete. Brak jednoznacznego dopasowania produktu lub zlecenia blokuje automatyczny zapis.

## Maszyny dla Cidex Mobile

CIDEX ma osobny adapter Maszyn, który czyta obecne źródła WM:

- `data/maszyny/maszyny.json`,
- awaryjnie stare `data/maszyny.json`.

Obsługiwane są formaty danych spotykane w WM. Przy bieżącej strukturze WM zapis używa kanonicznego `data/maszyny/maszyny.json`.

Dostępne operacje dla Cidex Mobile:

- lista Maszyn,
- karta Maszyny po istniejącym ID / `nr_ewid`,
- QR w formacie `CIDEX:MACHINE:<ID>`, np. `CIDEX:MACHINE:42`,
- zmiana statusu `Sprawna / Serwis / przegląd / Awaria`,
- dodanie uwagi do bieżącego statusu,
- dodanie zdjęcia do `data/maszyny/attachments/<ID>/...` i do istniejącego pola `status_current.photos`.

Zmiana na Awarię albo Serwis / przegląd wymaga opisu. Zapisy są oznaczane autorem `Cidex`. Adapter nie tworzy równoległego modelu danych — wykorzystuje istniejące pola WM `status_current`, `status_history` i `photos`.

## Mobile API — najprostsze uruchomienie

1. Uruchom `Cidex.exe`.
2. Wybierz i zweryfikuj `WM_ROOT`.
3. W lewym panelu kliknij `CIDEX Mobile`.
4. Potwierdź uruchomienie API.

CIDEX pokaże:

- adres dla emulatora,
- adres komputera w LAN dla telefonu,
- port,
- token.

Token jest automatycznie kopiowany do schowka. Ponowne kliknięcie `CIDEX Mobile` pozwala zatrzymać serwer. Przy zamykaniu CIDEX program ostrzega, jeśli API nadal działa, i po potwierdzeniu zatrzymuje proces API.

W wersji EXE pliki:

```text
Cidex.exe
Cidex_Api.exe
```

powinny znajdować się obok siebie. Główny `Cidex.exe` uruchamia i kontroluje `Cidex_Api.exe` — użytkownik nie musi uruchamiać serwera ręcznie.

## Alternatywne uruchomienie API z BAT

W wersji źródłowej nadal można użyć:

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
- `POST /api/v1/planista/orders`,
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

- `main.py` — interfejs CIDEX i sterowanie Mobile API,
- `cidex_config.py` — `WM_ROOT`, token i port API,
- `wm_store.py` — Planista: odczyt i kontrolowany zapis danych WM,
- `machine_store.py` — Maszyny: odczyt, QR, statusy, uwagi i zdjęcia,
- `api_server.py` — lokalne API dla Cidex Mobile,
- `mobile_api_launcher.py` — bezpieczne uruchamianie/zatrzymywanie API z GUI,
- `excel_reader.py` — odczyt `.xlsx`,
- `excel_diff.py` — porównanie Excel ↔ WM,
- `sync_service.py` — zastosowanie wyłącznie zatwierdzonych zmian.

Kod repozytorium Warsztat-Menager pozostaje niezależny i nie jest przez CIDEX modyfikowany.

## Przed produkcją

Ostatni odbiór powinien zostać wykonany na kopii aktualnego `WM_ROOT`: dodać jedno zlecenie z CIDEX PC, jedno z Cidex Mobile, sprawdzić import Excel, status maszyny, zdjęcie i QR, a następnie potwierdzić widoczność zmian po odświeżeniu WM. Dopiero po tym te same zapisy należy wykonywać na danych produkcyjnych.
