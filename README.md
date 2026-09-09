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
- autor zmian w historii: `Cidex`,
- budowa jednego pliku `Cidex.exe`.

## Zasady bezpieczeństwa

CIDEX nie usuwa automatycznie zleceń. Pozycja `Usunięte w Excelu` jest wyłącznie informacją.

Nowe zlecenia tworzone przez CIDEX nie rezerwują materiałów i nie modyfikują magazynu. Aktualizacja ilości jest blokowana, gdy istniejące zlecenie ma rezerwacje materiałowe albo chroniony status. Dzięki temu CIDEX nie próbuje odtwarzać wewnętrznej logiki rezerwacji Warsztat Menager.

## Uruchomienie

```bat
run.bat
```

Przy pierwszym uruchomieniu zostaną doinstalowane wymagane biblioteki.

## Budowa EXE

```bat
build_exe.bat
```

Po udanym buildzie w katalogu projektu pojawi się:

```text
Cidex.exe
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

- `main.py` — interfejs CIDEX,
- `cidex_config.py` — zapamiętanie ROOT,
- `wm_store.py` — odczyt i bezpieczny zapis danych WM,
- `excel_reader.py` — odczyt `.xlsx`,
- `excel_diff.py` — porównanie Excel ↔ WM,
- `sync_service.py` — zastosowanie wyłącznie zatwierdzonych zmian.

Dalszy rozwój może dodać kolejne moduły, ale v1.0 celowo ogranicza się do Planisty.
