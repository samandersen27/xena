# Xena 🌵
A personal cactus museum — synced from iNaturalist, hosted on GitHub Pages.

**Live site:** `https://samandersen27.github.io/xena`

## How it works
- `sync.py` pulls all your cactus observations from iNaturalist and writes them to `frontend/public/data.json`
- The React frontend reads that JSON file — no backend, no database
- GitHub Actions runs the sync and rebuilds the site automatically on every push to `main`

## Local setup

### 1. Clone the repo
```bash
git clone https://github.com/YOUR_USERNAME/xena.git
cd xena
```

### 2. Run the sync (Python 3.7+, no packages needed)
```bash
python sync.py
```
This creates `frontend/public/data.json` with all your iNat data.

### 3. Start the frontend
```bash
cd frontend
npm install
npm run dev
# Opens at http://localhost:5173/xena/
```

## Updating your data
Whenever you've added new observations on iNaturalist:
```bash
python sync.py        # pull fresh data
git add -A
git commit -m "sync"
git push              # GitHub Actions auto-deploys
```

## GitHub Pages setup (one-time)
1. Push this repo to GitHub
2. Go to repo Settings → Pages → Source → **GitHub Actions**
3. Push to `main` — the workflow runs automatically
4. Your site will be live at `https://YOUR_USERNAME.github.io/xena`

## Customising
- `sync.py` — change `USERNAME` at the top if needed
- `frontend/vite.config.js` — change `base` to match your repo name
- `frontend/src/lib/data.jsx` — change the fetch path if your base changes
