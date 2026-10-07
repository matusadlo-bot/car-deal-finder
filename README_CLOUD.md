# Car Deal Finder v0.6 Cloud – GitHub Pages edition

Táto verzia nepotrebuje server bežiaci doma ani platený hosting.

## Architektúra

- **GitHub Actions** spustí rýchly scan každú hodinu a hlboký scan raz denne.
- Plná pracovná SQLite databáza sa drží komprimovaná na vetve `data`.
- Do `docs/data/results.json` sa exportujú iba silné výsledky pre web.
- **GitHub Pages** servíruje statický dashboard z priečinka `docs/`.
- API kľúče sa ukladajú iba do **GitHub Actions Secrets**, nikdy nie do repozitára.

## Prvé nasadenie

1. Vytvor nový **public** GitHub repozitár, napr. `car-deal-finder`.
2. Nahraj obsah tohto priečinka do repozitára.
3. V GitHub repozitári otvor **Settings → Actions → General → Workflow permissions** a povoľ `Read and write permissions`.
4. Otvor **Settings → Pages** a zvoľ `Deploy from a branch`, branch `main`, folder `/docs`.
5. V **Actions** spusti workflow `Update finder data` ručne v režime `deep`.
6. Po dokončení bude web na adrese `https://TVOJ-LOGIN.github.io/car-deal-finder/`.

## Voliteľné secrets

V `Settings → Secrets and variables → Actions` môžeš pridať:

- `OPENAI_API_KEY`
- `OPENAI_MODEL`
- `AI_ANALYSIS_MODE` (`top` alebo `all`)
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`
- `MOBILE_DE_USERNAME` a `MOBILE_DE_PASSWORD` iba ak máš skutočné Mobile.de API credentials.

Bez OpenAI API funguje lokálny scoring. Mobile.de je v `config.json` defaultne vypnuté.

## Dôležité

GitHub Pages je pre bezplatné použitie najjednoduchší pri public repozitári. Web nezobrazuje `.env`, API kľúče ani plnú SQLite databázu; vetva `data` však obsahuje zozbierané verejné inzeráty a pri public repozitári je tiež verejne čitateľná.
