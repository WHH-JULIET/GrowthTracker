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


import random

_CLOSERS_HIGH = [
    "You're building something real. Keep that energy tomorrow.",
    "Solid day. One more like this and it becomes a streak.",
    "This is what growth looks like. Show up the same way tomorrow.",
    "You did the work. That's what separates people who talk from people who do.",
]
_CLOSERS_MID = [
    "Not perfect, but you showed up. That already puts you ahead of most.",
    "Good foundation. Tomorrow, pick one thing to do better and own it.",
    "Progress isn't always loud. You moved forward today — build on it.",
    "Every average day you push through is training for your best days.",
]
_CLOSERS_LOW = [
    "Today wasn't your best — and that's okay. Reset, sleep well, attack tomorrow.",
    "The fact that you're tracking means you care. Use that energy tomorrow.",
    "One rough day doesn't define the week. Tomorrow is a clean slate.",
    "You logged it. That's honesty. Now use it as fuel, not guilt.",
]



def _generate_summary(entry):
    phone = entry.get('phone_minutes', 0)
    goals = (entry.get('goals') or '').strip()
    sports = (entry.get('sports') or '').strip()
    food = (entry.get('food') or '').strip()
    people = (entry.get('people_involved') or '').strip()
    medicines = entry.get('medicines_taken', False)
    lines = []

    if phone <= 60:
        lines.append(f'Only {phone} min on phone — your focus was sharp today.')
    elif phone <= 120:
        lines.append(f'{phone} min on phone is decent. Try cutting 20 min tomorrow for an extra focus block.')
    elif phone <= 240:
        lines.append(f'{phone} min on phone is eating into your productive hours. Set app limits tonight.')
    else:
        lines.append(f'{phone} min on phone is too high. Put it face-down during work and meals tomorrow.')

    if goals and goals.lower() != 'nil':
        lines.append(f'Goals set: "{goals[:80]}{'...' if len(goals) > 80 else ''}". Before sleeping, check which ones you actually completed.')
    else:
        lines.append('No goals logged. Tomorrow morning, write down 1-3 specific things you want to finish.')

    if sports and sports.lower() != 'nil':
        lines.append(f'You moved your body ({sports[:50]}). Physical activity directly boosts focus and mood the next day.')
    else:
        lines.append('No physical activity today. Even a 20-min walk tomorrow will improve your energy and sleep quality.')

    if food and food.lower() != 'nil':
        lines.append(f'Food tracked ({food[:50]}). Stay mindful of protein and hydration — they fuel your brain.')
    else:
        lines.append('No food logged. What you eat directly affects your energy. Be more intentional tomorrow.')

    if people and people.lower() != 'nil':
        lines.append(f'You engaged with people ({people[:50]}). Nurture the right relationships — they are part of growth.')
    else:
        lines.append('No interactions logged. Reach out to one person tomorrow — a mentor, friend, or teammate.')

    if not medicines:
        lines.append('Medicines not taken. Set a daily alarm so you never miss.')

    lines.append(random.choice(_CLOSERS_HIGH if phone <= 120 and (sports and sports.lower() != 'nil') else _CLOSERS_MID if phone <= 240 else _CLOSERS_LOW))

    return ' | '.join(lines)


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
        'people_involved': (payload.get('people_involved') or '').strip(),
        'phone_minutes': _safe_int(payload.get('phone_minutes'), 0),
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


@app.put('/api/entries/{date}')
async def update_entry(date: str, request: Request):
    payload = await request.json()
    entries = _read_entries()
    idx = next((i for i, e in enumerate(entries) if e['date'] == date), None)
    if idx is None:
        return JSONResponse({'error': 'Not found'}, status_code=404)
    entry = {
        'date': date,
        'goals': (payload.get('goals') or '').strip(),
        'people_involved': (payload.get('people_involved') or '').strip(),
        'phone_minutes': _safe_int(payload.get('phone_minutes'), 0),
        'food': (payload.get('food') or '').strip(),
        'sports': (payload.get('sports') or '').strip(),
        'medicines_taken': bool(payload.get('medicines_taken')),
    }
    entry['summary'] = _generate_summary(entry)
    entries[idx] = entry
    _write_entries(entries)
    return JSONResponse(entry)


@app.delete('/api/entries/{date}')
def delete_entry(date: str):
    entries = _read_entries()
    new_entries = [e for e in entries if e['date'] != date]
    if len(new_entries) == len(entries):
        return JSONResponse({'error': 'Not found'}, status_code=404)
    _write_entries(new_entries)
    return JSONResponse({'deleted': date})
