# Car Deal Finder v0.5 – Strict Deals + WOW Cars + Chainsaw Fixers

Táto verzia je zámerne prísnejšia. Cieľ nie je ukázať veľa výsledkov, ale vyhodiť diely, kolesá a bežné autá a nechať iba kandidátov, ktorí majú reálny dôvod byť zaujímaví.

## Hlavné zmeny

- Pred scoringom sa klasifikuje, či inzerát naozaj predstavuje celé auto. Kolesá, pneumatiky, disky a samostatné diely sa nezapočítavajú do Deal/Rare výsledkov.
- Deal Score potrebuje minimálne 8 porovnateľných áut rovnakého make/modelu a používa prísnejšie rozdiely roku, km, paliva, výkonu a karosérie.
- Cenový rozdiel pod približne 8–12 % už nevytvorí silný deal.
- Rare/WOW sekcia je oveľa prísnejšia. Samotné RS/GTI/AMG/M Sport/S-line alebo bežná karoséria nestačí.
- Scarcity sama o sebe už nevytvorí rare výsledok bez ďalšieho konkrétneho dôkazu.
- Cenový filter používa textové číselné polia a predvolený rozumný 99. percentil namiesto slidera natiahnutého jedným extrémnym inzerátom.
- km a počet videní majú vlastné min/max filtre.
- Bazoš SK/CZ deep scan ide až na 120 strán; ďalšie zdroje majú zvýšený rozsah.
- Nová samostatná sekcia **Pokazené motorové píly** s vlastným scanom, databázou a scoringom opraviteľnosti.
- Píly filtrujú samostatné reťaze, lišty a diely a hľadajú hlavne celé pokazené píly (iskra, karburátor, palivo, štartér, mazanie, spojka). Zadretý motor/nízka kompresia sú penalizované.

## Spustenie

1. Rozbaľ ZIP do nového priečinka.
2. Spusti `setup_windows.bat`.
3. Spusti `run_dashboard.bat`.
4. V sekcii Autá odporúčam prvýkrát `Hlboký scan áut`.
5. V sekcii Motorové píly spusti vlastný `Hlboký scan píl`.

Projekt je nastavený na Python 3.14 cez `py -3.14`.

## AI

OpenAI API je voliteľné. Bez kľúča sa každý inzerát stále analyzuje lokálne. Ak nastavíš `AI_ANALYSIS_MODE=all`, AI bude druhá kontrolná vrstva každého nového auta; to môže zvýšiť API náklady.

## Poznámka

Odhad cien a opráv je screening, nie diagnostika. Pred nákupom treba fyzicky preveriť stav, VIN/históriu a pri závadách spraviť diagnostiku.
