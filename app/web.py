from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path
from datetime import datetime
import json
import os

BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / 'templates'
STATIC_DIR = BASE_DIR / 'static'

app = FastAPI(title='Growth Tracker')

app.mount('/static', StaticFiles(directory=STATIC_DIR), name='static')

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def _data_path():
    if os.environ.get('VERCEL'):
        data_dir = Path('/tmp') / 'growthtracker'
    else:
        data_dir = BASE_DIR.parent / 'data'
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir / 'growth_data.json'


def _read_entries():
    path = _data_path()
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return []


def _write_entries(entries):
    path = _data_path()
    path.write_text(json.dumps(entries, indent=2), encoding='utf-8')


def _today_str():
    return datetime.now().strftime('%Y-%m-%d')


def _safe_int(value, default=0):
    try:
        return int(value)
    except Exception:
        return default


def _generate_summary(entry):
    lines = []
    phone_minutes = entry.get('phone_minutes', 0)
    notifications = entry.get('notifications', 0)
    work = entry.get('communication_work', '')
    timepass = entry.get('communication_timepass', '')
    sports = entry.get('sports', '')
    medicines = entry.get('medicines_taken', False)
    goals = entry.get('goals', '')

    if phone_minutes > 240:
        lines.append('Reduce phone usage; consider focused blocks without phone.')
    elif phone_minutes > 120:
        lines.append('Phone time is moderate; try 15-30 min less tomorrow.')
    else:
        lines.append('Phone usage looks controlled; keep the same or slightly lower.')

    if notifications > 80:
        lines.append('High notifications; mute non-essential apps for deep work.')
    elif notifications > 30:
        lines.append('Moderate notifications; batch-check instead of constant checks.')
    else:
        lines.append('Low notifications; good focus potential.')

    if not work:
        lines.append('Add at least one work-related communication or progress check-in.')
    if timepass and work:
        lines.append('Balance timepass with work tasks; keep timepass limited to breaks.')

    if not sports:
        lines.append('Add 15-30 minutes of physical activity.')

    if not medicines:
        lines.append('Remember medicines if required in your routine.')

    if goals:
        lines.append('Review goals at the start and end of day to close loops.')
    else:
        lines.append('Set 1-3 clear goals for tomorrow.')

    return ' '.join(lines)


@app.get('/', response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse('index.html', {'request': request, 'today': _today_str()})


@app.get('/api/entries')
def list_entries():
    entries = _read_entries()
    return JSONResponse(entries)


@app.post('/api/entries')
async def create_entry(request: Request):
    payload = await request.json()

    entry = {
        'date': payload.get('date') or _today_str(),
        'goals': (payload.get('goals') or '').strip(),
        'communication_work': (payload.get('communication_work') or '').strip(),
        'communication_timepass': (payload.get('communication_timepass') or '').strip(),
        'phone_minutes': _safe_int(payload.get('phone_minutes'), 0),
        'notifications': _safe_int(payload.get('notifications'), 0),
        'food': (payload.get('food') or '').strip(),
        'sports': (payload.get('sports') or '').strip(),
        'medicines_taken': bool(payload.get('medicines_taken')),
    }
    entry['summary'] = _generate_summary(entry)

    entries = _read_entries()
    entries.append(entry)
    _write_entries(entries)

    return JSONResponse(entry)


@app.get('/api/entries/last')
def last_entry():
    entries = _read_entries()
    if not entries:
        return JSONResponse({})
    return JSONResponse(entries[-1])
