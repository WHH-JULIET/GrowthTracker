from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from pathlib import Path
from datetime import datetime
import json, os, random, hashlib, base64

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
# On Vercel, /tmp is ephemeral per cold-start, so we persist users in an
# env var USERS_DATA (base64-encoded JSON). Locally we use a JSON file.

def _is_vercel() -> bool:
    return bool(os.environ.get('VERCEL'))


def _users_path() -> Path:
    d = BASE_DIR.parent / 'data'
    d.mkdir(parents=True, exist_ok=True)
    return d / 'users.json'


def _read_users() -> dict:
    if _is_vercel():
        raw = os.environ.get('USERS_DATA', '')
        if not raw:
            return {}
        try:
            return json.loads(base64.b64decode(raw).decode('utf-8'))
        except Exception:
            return {}
    p = _users_path()
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding='utf-8'))
    except Exception:
        return {}


def _write_users(users: dict):
    if _is_vercel():
        # Persist back to env var at runtime (survives within the same process;
        # for true persistence across cold-starts set USERS_DATA in Vercel dashboard)
        encoded = base64.b64encode(json.dumps(users).encode('utf-8')).decode()
        os.environ['USERS_DATA'] = encoded
        return
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
    if _is_vercel():
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


def _sort_entries(entries: list) -> list:
    """Sort entries by date DESC, then created_at DESC."""
    return sorted(entries, key=lambda e: (e.get('date', ''), e.get('created_at', '')), reverse=True)


def _safe_int(value, default=0):
    try:
        return int(value)
    except Exception:
        return default


def _join_field(selected, other: str = None) -> str:
    """Combine a list/string of selected options with an optional free-text 'other'."""
    parts = []
    if isinstance(selected, list):
        parts = [s.strip() for s in selected if s and s.strip()]
    elif selected:
        parts = [selected.strip()]
    if other and other.strip():
        parts.append(other.strip())
    return ', '.join(parts) if parts else ''


# ── Summary ───────────────────────────────────────────────────────────────────
_CLOSERS_TODAY_HIGH = [
    "You're building something real. Keep that energy tomorrow.",
    "Solid day. One more like this and it becomes a streak.",
    "This is what growth looks like. Show up the same way tomorrow.",
]
_CLOSERS_TODAY_MID = [
    "Not perfect, but you showed up. That already puts you ahead of most.",
    "Good foundation. Tomorrow, pick one thing to do better and own it.",
    "Progress isn't always loud. You moved forward today — build on it.",
]
_CLOSERS_TODAY_LOW = [
    "Today wasn't your best — and that's okay. Reset, sleep well, attack tomorrow.",
    "The fact that you're tracking means you care. Use that energy tomorrow.",
    "One rough day doesn't define the week. Tomorrow is a clean slate.",
]
_CLOSERS_PAST_HIGH = [
    "Good consistency on that day. Every logged day builds the bigger picture.",
    "That was a strong day. Use it as a reference point for future days.",
]
_CLOSERS_PAST_MID = [
    "A decent day in the books. Past logs help you spot patterns over time.",
    "Logged and recorded. Reviewing past entries is how you find what works.",
]
_CLOSERS_PAST_LOW = [
    "Not your best day, but you logged it — that honesty is valuable.",
    "Every low day recorded is data. Use it to understand what to change.",
]


def _fmt_date(date_str: str) -> str:
    """Format YYYY-MM-DD as 'Month D' for use in summaries."""
    try:
        return datetime.strptime(date_str, '%Y-%m-%d').strftime('%B %-d')
    except Exception:
        try:
            return datetime.strptime(date_str, '%Y-%m-%d').strftime('%B %d').replace(' 0', ' ')
        except Exception:
            return date_str


def _generate_summary(entry: dict) -> str:
    date_str = entry.get('date') or _today_str()
    today = _today_str()
    is_past = date_str < today
    prefix = f'On {_fmt_date(date_str)}, you' if is_past else 'Today you'
    ref_next = f'the following day' if is_past else 'tomorrow'

    phone = entry.get('phone_minutes', 0)
    goals = (entry.get('goals') or '').strip()
    sports = (entry.get('sports') or '').strip()
    food = (entry.get('food') or '').strip()
    people = (entry.get('people_involved') or '').strip()
    has_medicines = bool(entry.get('has_medicines', False))
    medicines_taken = bool(entry.get('medicines_taken', False))
    lines = []

    # Phone — only comment if user actually entered a value > 0
    if phone > 0:
        if phone <= 60:
            lines.append(f'{prefix} spent only {phone} min on your phone — solid focus.')
        elif phone <= 120:
            lines.append(f'{prefix} spent {phone} min on your phone, which is reasonable.')
        elif phone <= 240:
            lines.append(f'{prefix} spent {phone} min on your phone. Consider setting app limits {ref_next}.')
        else:
            lines.append(f'{prefix} spent {phone} min on your phone — that is quite high. Try putting it face-down during work {ref_next}.')

    # Goals — only comment if something was actually selected
    if goals:
        preview = goals[:80] + ('...' if len(goals) > 80 else '')
        lines.append(f'Goals logged: {preview}. Review which ones were completed before the day ends.')
    
    # Sports — only comment if something was selected
    if sports and sports.lower() not in ('', 'nil'):
        lines.append(f'{prefix} logged physical activity: {sports[:50]}. Staying active directly improves focus and mood.')

    # Food — only comment if something was selected
    if food and food.lower() not in ('', 'nil'):
        lines.append(f'Food recorded: {food[:60]}. Stay mindful of protein and hydration.')

    # People — only comment if something was entered
    if people and people.lower() not in ('', 'nil'):
        lines.append(f'{prefix} interacted with: {people[:50]}. Nurturing the right relationships is part of growth.')

    # Medicines — only comment if user explicitly opted in
    if has_medicines:
        if medicines_taken:
            lines.append('Prescribed medicines were taken. Good — consistency with medication matters.')
        else:
            lines.append('No medicine intake was recorded today. If you have a prescription, try to stay consistent.')

    # If almost nothing was logged, give a neutral minimal summary
    if len(lines) == 0:
        label = f'Your entry for {_fmt_date(date_str)}' if is_past else 'Your entry for today'
        lines.append(f'{label} was recorded successfully. Continue logging your daily activities.')

    # Closer — tone depends on date context and activity level
    is_high = phone <= 120 and bool(sports and sports.lower() not in ('', 'nil'))
    is_low = phone > 240
    if is_past:
        lines.append(random.choice(_CLOSERS_PAST_HIGH if is_high else _CLOSERS_PAST_LOW if is_low else _CLOSERS_PAST_MID))
    else:
        lines.append(random.choice(_CLOSERS_TODAY_HIGH if is_high else _CLOSERS_TODAY_LOW if is_low else _CLOSERS_TODAY_MID))

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
    if not username or not pin:
        return JSONResponse({'error': 'Username and PIN are required.'}, status_code=400)
    users = _read_users()
    if username not in users:
        return JSONResponse({'error': 'User not found. Please register first.'}, status_code=401)
    if users[username] != _hash_pin(pin):
        return JSONResponse({'error': 'Incorrect PIN. Please try again.'}, status_code=401)
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
    return JSONResponse(_sort_entries(_read_entries(_current_user(request))))


@app.get('/api/entries/last')
def last_entry(request: Request):
    entries = _sort_entries(_read_entries(_current_user(request)))
    return JSONResponse(entries[0] if entries else {})


@app.post('/api/entries')
async def create_entry(request: Request):
    uid = _current_user(request)
    payload = await request.json()
    date_val = (payload.get('date') or _today_str()).strip()
    if date_val > _today_str():
        return JSONResponse({'error': 'You cannot log entries for future dates.'}, status_code=400)
    entry = {
        'date': date_val,
        'created_at': datetime.now().isoformat(),
        'goals': _join_field(payload.get('goals'), payload.get('goals_other')),
        'people_involved': (payload.get('people_involved') or '').strip(),
        'phone_minutes': _safe_int(payload.get('phone_minutes'), 0),
        'food': _join_field(payload.get('food'), payload.get('food_other')),
        'sports': _join_field(payload.get('sports'), payload.get('sports_other')),
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
    if date > _today_str():
        return JSONResponse({'error': 'You cannot log entries for future dates.'}, status_code=400)
    payload = await request.json()
    entries = _read_entries(uid)
    idx = next((i for i, e in enumerate(entries) if e['date'] == date), None)
    if idx is None:
        return JSONResponse({'error': 'Not found'}, status_code=404)
    entry = {
        'date': date,
        'created_at': entries[idx].get('created_at', datetime.now().isoformat()),
        'goals': _join_field(payload.get('goals'), payload.get('goals_other')),
        'people_involved': (payload.get('people_involved') or '').strip(),
        'phone_minutes': _safe_int(payload.get('phone_minutes'), 0),
        'food': _join_field(payload.get('food'), payload.get('food_other')),
        'sports': _join_field(payload.get('sports'), payload.get('sports_other')),
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
