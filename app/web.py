from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from pathlib import Path
from datetime import datetime
import json, os, random, hashlib

BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / 'templates'
STATIC_DIR = BASE_DIR / 'static'

app = FastAPI(title='Growth Tracker')

app.add_middleware(
    SessionMiddleware,
    secret_key=os.environ.get('SESSION_SECRET', 'dev-secret-change-in-prod'),
    session_cookie='gt_session',
    max_age=None,
    https_only=False,
    same_site='lax',
)

app.mount('/static', StaticFiles(directory=STATIC_DIR), name='static')
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


# ── Users store ───────────────────────────────────────────────────────────────
def _users_path() -> Path:
    if os.environ.get('VERCEL'):
        d = Path('/tmp') / 'growthtracker'
    else:
        d = BASE_DIR.parent / 'data'
    d.mkdir(parents=True, exist_ok=True)
    return d / 'users.json'


def _read_users() -> dict:
    p = _users_path()
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding='utf-8'))
    except Exception:
        return {}


def _write_users(users: dict):
    _users_path().write_text(json.dumps(users, indent=2), encoding='utf-8')


def _hash_pin(pin: str) -> str:
    return hashlib.sha256(pin.encode()).hexdigest()


# ── Auth helpers ──────────────────────────────────────────────────────────────
def _current_user(request: Request) -> str:
    user = request.session.get('username')
    if not user:
        raise HTTPException(status_code=401, detail='Not authenticated')
    return user


# ── Data store ────────────────────────────────────────────────────────────────
def _data_path(username: str) -> Path:
    if os.environ.get('VERCEL'):
        d = Path('/tmp') / 'growthtracker' / username
    else:
        d = BASE_DIR.parent / 'data' / username
    d.mkdir(parents=True, exist_ok=True)
    return d / 'growth_data.json'


def _read_entries(username: str):
    p = _data_path(username)
    if not p.exists():
        return []
    try:
        return json.loads(p.read_text(encoding='utf-8'))
    except Exception:
        return []


def _write_entries(username: str, entries):
    _data_path(username).write_text(json.dumps(entries, indent=2), encoding='utf-8')


def _today_str():
    return datetime.now().strftime('%Y-%m-%d')


def _safe_int(value, default=0):
    try:
        return int(value)
    except Exception:
        return default


# ── Summary ───────────────────────────────────────────────────────────────────
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


def _generate_summary(entry: dict) -> str:
    phone = entry.get('phone_minutes', 0)
    goals = (entry.get('goals') or '').strip()
    sports = (entry.get('sports') or '').strip()
    food = (entry.get('food') or '').strip()
    people = (entry.get('people_involved') or '').strip()
    has_medicines = bool(entry.get('has_medicines', False))
    medicines_taken = bool(entry.get('medicines_taken', False))
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
        preview = goals[:80] + ('...' if len(goals) > 80 else '')
        lines.append(f'Goals set: "{preview}". Before sleeping, check which ones you actually completed.')
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

    if has_medicines:
        if medicines_taken:
            lines.append('Medicines taken. Good — consistency with medication is important.')
        else:
            lines.append('No medicine intake was recorded today. If you have a prescription, try to stay consistent.')

    is_high = phone <= 120 and sports and sports.lower() != 'nil'
    is_low = phone > 240
    lines.append(random.choice(_CLOSERS_HIGH if is_high else _CLOSERS_LOW if is_low else _CLOSERS_MID))

    return ' | '.join(lines)


# ── Auth routes ───────────────────────────────────────────────────────────────
@app.post('/auth/register')
async def register(request: Request):
    body = await request.json()
    username = (body.get('username') or '').strip().lower()
    pin = str(body.get('pin') or '').strip()
    if not username or not pin or len(pin) < 4:
        return JSONResponse({'error': 'Username and a 4-digit PIN are required.'}, status_code=400)
    users = _read_users()
    if username in users:
        return JSONResponse({'error': 'Username already taken.'}, status_code=400)
    users[username] = _hash_pin(pin)
    _write_users(users)
    request.session['username'] = username
    return JSONResponse({'ok': True, 'username': username})


@app.post('/auth/login')
async def login(request: Request):
    body = await request.json()
    username = (body.get('username') or '').strip().lower()
    pin = str(body.get('pin') or '').strip()
    users = _read_users()
    if users.get(username) != _hash_pin(pin):
        return JSONResponse({'error': 'Invalid username or PIN.'}, status_code=401)
    request.session['username'] = username
    return JSONResponse({'ok': True, 'username': username})


@app.post('/auth/logout')
def logout(request: Request):
    request.session.clear()
    return JSONResponse({'ok': True})


@app.get('/auth/me')
def me(request: Request):
    username = request.session.get('username')
    if not username:
        return JSONResponse({'authenticated': False})
    return JSONResponse({'authenticated': True, 'username': username})


# ── Page ──────────────────────────────────────────────────────────────────────
@app.get('/', response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse('index.html', {'request': request, 'today': _today_str()})


# ── API (all protected) ───────────────────────────────────────────────────────
@app.get('/api/entries')
def list_entries(request: Request):
    return JSONResponse(_read_entries(_current_user(request)))


@app.get('/api/entries/last')
def last_entry(request: Request):
    entries = _read_entries(_current_user(request))
    return JSONResponse(entries[-1] if entries else {})


@app.post('/api/entries')
async def create_entry(request: Request):
    uid = _current_user(request)
    payload = await request.json()
    entry = {
        'date': payload.get('date') or _today_str(),
        'goals': (payload.get('goals') or '').strip(),
        'people_involved': (payload.get('people_involved') or '').strip(),
        'phone_minutes': _safe_int(payload.get('phone_minutes'), 0),
        'food': (payload.get('food') or '').strip(),
        'sports': (payload.get('sports') or '').strip(),
        'has_medicines': bool(payload.get('has_medicines', False)),
        'medicines_taken': bool(payload.get('medicines_taken', False)),
    }
    entry['summary'] = _generate_summary(entry)
    entries = _read_entries(uid)
    entries.append(entry)
    _write_entries(uid, entries)
    return JSONResponse(entry)


@app.put('/api/entries/{date}')
async def update_entry(date: str, request: Request):
    uid = _current_user(request)
    payload = await request.json()
    entries = _read_entries(uid)
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
        'has_medicines': bool(payload.get('has_medicines', False)),
        'medicines_taken': bool(payload.get('medicines_taken', False)),
    }
    entry['summary'] = _generate_summary(entry)
    entries[idx] = entry
    _write_entries(uid, entries)
    return JSONResponse(entry)


@app.delete('/api/entries/{date}')
def delete_entry(date: str, request: Request):
    uid = _current_user(request)
    entries = _read_entries(uid)
    new_entries = [e for e in entries if e['date'] != date]
    if len(new_entries) == len(entries):
        return JSONResponse({'error': 'Not found'}, status_code=404)
    _write_entries(uid, new_entries)
    return JSONResponse({'deleted': date})
