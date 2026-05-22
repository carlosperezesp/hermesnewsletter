# NHL Tracker

Local NHL dashboard using real data from the public NHL web API.

## Run

```bash
python3 -m http.server 8000
```

Open `http://localhost:8000/`.

The deployed site works as a static Vercel project because the root file is `index.html`.

## Refresh Data

```bash
python3 scripts/update_data.py
```

The script regenerates `data.js` from:

- `https://api-web.nhle.com/v1/standings/now`
- `https://api-web.nhle.com/v1/club-stats/{TEAM}/now`
- `https://api-web.nhle.com/v1/playoff-bracket/{YEAR}`

## Hosted Data Freshness

The Vercel deployment is static, so hosted data changes only when `data.js` changes in GitHub. This repo includes a GitHub Actions workflow that runs the updater every day and commits a fresh `data.js` when the NHL API has changed.

## Daily Refresh On macOS

```bash
chmod +x scripts/install_daily_update.sh
scripts/install_daily_update.sh
```

That installs a LaunchAgent that refreshes the data every day at 09:05 local time.
