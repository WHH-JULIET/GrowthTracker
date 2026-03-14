# GrowthTracker (FastAPI + Mobile-First Web App)

This replaces Kivy to support Python 3.13 and Vercel deployment.

## Run locally
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python app\main.py
# or
python -m app.main
```
Open: http://127.0.0.1:8000

## Vercel deploy
Vercel runs `api/index.py` as a serverless function. **Note:** the filesystem is ephemeral, so saved entries in `/tmp` will not persist across deployments or cold starts. For real persistence, switch to a DB (e.g., Supabase, Neon, SQLite on external volume).

### `vercel.json` (optional)
If you need routing:
```json
{
  "rewrites": [{ "source": "/(.*)", "destination": "/api/index" }]
}
```

## Features
- Goals
- Communication (work vs timepass with colors)
- Phone time and notifications
- Food items
- Sports
- Medicines taken
- Local summary with improvement suggestions
