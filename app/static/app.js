const form = document.getElementById('entryForm');
const summaryContent = document.getElementById('summaryContent');
const historyList = document.getElementById('historyList');
const loadLastBtn = document.getElementById('loadLast');
const authBar = document.getElementById('authBar');
const loginWall = document.getElementById('loginWall');
const mainContent = document.getElementById('mainContent');
const hasMedicinesCheck = document.getElementById('hasMedicinesCheck');
const medicinesTakenRow = document.getElementById('medicinesTakenRow');
const dateInput = document.getElementById('dateInput');
const futureDateWarn = document.getElementById('futureDateWarn');
const submitBtn = form.querySelector('button[type="submit"]');

let editingDate = null;

// ── Date helpers ─────────────────────────────────────────────────────────────
function todayStr() {
  return new Date().toISOString().slice(0, 10);
}

function isFuture(dateStr) {
  return dateStr > todayStr();
}

function validateDateInput() {
  const val = dateInput.value;
  if (val && isFuture(val)) {
    futureDateWarn.style.display = 'flex';
    submitBtn.disabled = true;
    submitBtn.style.opacity = '0.5';
  } else {
    futureDateWarn.style.display = 'none';
    submitBtn.disabled = false;
    submitBtn.style.opacity = '';
  }
}

dateInput.addEventListener('change', validateDateInput);

// ── Sort entries: date DESC, created_at DESC ─────────────────────────────────────
function sortEntries(entries) {
  return entries.slice().sort((a, b) => {
    if (b.date !== a.date) return b.date > a.date ? 1 : -1;
    return (b.created_at || '') > (a.created_at || '') ? 1 : -1;
  });
}

// ── Auth ──────────────────────────────────────────────────────────────────────
async function initAuth() {
  const res = await fetch('/auth/me');
  const data = await res.json();
  if (!data.authenticated) {
    loginWall.style.display = 'flex';
    mainContent.style.display = 'none';
    authBar.innerHTML = '';
    return false;
  }
  showApp(data.username);
  return true;
}

function showApp(username) {
  loginWall.style.display = 'none';
  mainContent.style.display = 'grid';
  authBar.innerHTML = `
    <div class="user-pill">
      <span class="user-pill-name">👤 ${username}</span>
      <button class="btn-logout" id="logoutBtn">Sign out</button>
    </div>
  `;
  document.getElementById('logoutBtn').addEventListener('click', async () => {
    await fetch('/auth/logout', { method: 'POST' });
    location.reload();
  });
}

// ── Login / Register tabs ─────────────────────────────────────────────────────
document.getElementById('tabLogin').addEventListener('click', () => {
  document.getElementById('loginForm').style.display = 'grid';
  document.getElementById('registerForm').style.display = 'none';
  document.getElementById('tabLogin').classList.add('active');
  document.getElementById('tabRegister').classList.remove('active');
});

document.getElementById('tabRegister').addEventListener('click', () => {
  document.getElementById('registerForm').style.display = 'grid';
  document.getElementById('loginForm').style.display = 'none';
  document.getElementById('tabRegister').classList.add('active');
  document.getElementById('tabLogin').classList.remove('active');
});

document.getElementById('loginForm').addEventListener('submit', async (e) => {
  e.preventDefault();
  const username = document.getElementById('loginUsername').value.trim();
  const pin = document.getElementById('loginPin').value.trim();
  const err = document.getElementById('loginError');
  const res = await fetch('/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, pin })
  });
  const data = await res.json();
  if (!res.ok) {
    err.innerHTML = '⚠️ ' + data.error;
    err.style.display = 'flex';
    return;
  }
  err.style.display = 'none';
  showApp(data.username);
  loadLast();
  loadHistory();
});

document.getElementById('registerForm').addEventListener('submit', async (e) => {
  e.preventDefault();
  const username = document.getElementById('regUsername').value.trim();
  const pin = document.getElementById('regPin').value.trim();
  const err = document.getElementById('registerError');
  const res = await fetch('/auth/register', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, pin })
  });
  const data = await res.json();
  if (!res.ok) {
    err.innerHTML = '⚠️ ' + data.error;
    err.style.display = 'flex';
    return;
  }
  err.style.display = 'none';
  showApp(data.username);
  loadLast();
  loadHistory();
});

// ── Medicines toggle ──────────────────────────────────────────────────────────
hasMedicinesCheck.addEventListener('change', () => {
  medicinesTakenRow.style.display = hasMedicinesCheck.checked ? 'grid' : 'none';
  if (!hasMedicinesCheck.checked) form.elements['medicines_taken'].checked = false;
});

// ── Sports "Other" toggle ─────────────────────────────────────────────────────
document.querySelectorAll('input[name="sports"]').forEach(r => {
  r.addEventListener('change', () => {
    const sportsOther = document.getElementById('sportsOther');
    sportsOther.style.display = document.getElementById('sportsOtherRadio').checked ? 'block' : 'none';
    if (!document.getElementById('sportsOtherRadio').checked) sportsOther.value = '';
  });
});

// ── Summary rendering ─────────────────────────────────────────────────────────
function formatSummary(raw) {
  if (!raw) return '<p class="placeholder">-</p>';
  const parts = raw.split(' | ');
  const feedback = parts.slice(0, -1);
  const closer = parts[parts.length - 1];
  return `
    <ul class="summary-points">${feedback.map(f => `<li>${f}</li>`).join('')}</ul>
    <div class="summary-closer">${closer}</div>
  `;
}

function renderEntry(entry) {
  if (!entry || !entry.date) {
    summaryContent.innerHTML = '<p class="placeholder">No entries yet.</p>';
    return;
  }
  const medicineHtml = entry.has_medicines
    ? `<div><strong>Medicines:</strong> ${entry.medicines_taken ? 'Taken' : 'Not taken'}</div>`
    : '';
  summaryContent.innerHTML = `
    <div><strong>Date:</strong> ${entry.date}</div>
    <div><strong>Goals:</strong> ${entry.goals || '-'}</div>
    <div><strong>People Involved:</strong> ${entry.people_involved || '-'}</div>
    <div><strong>Phone time:</strong> ${entry.phone_minutes || 0} min</div>
    <div><strong>Food:</strong> ${entry.food || '-'}</div>
    <div><strong>Sports:</strong> ${entry.sports || '-'}</div>
    ${medicineHtml}
    <div><strong>Summary:</strong>${formatSummary(entry.summary)}</div>
  `;
}

// ── Chip helpers ──────────────────────────────────────────────────────────────
function getCheckedValues(name) {
  return [...form.querySelectorAll(`input[name="${name}"]:checked`)].map(i => i.value);
}

function setChipValues(name, values) {
  form.querySelectorAll(`input[name="${name}"]`).forEach(i => {
    i.checked = values.includes(i.value);
  });
}

function fillFormForEdit(entry) {
  editingDate = entry.date;
  document.getElementById('dateInput').value = entry.date;
  document.getElementById('dateInput').disabled = true;

  // Goals: split stored string back into chips + other
  const goalOptions = ['Weight loss','Muscle gain','Improve stamina','Healthy lifestyle','Better sleep','Stress reduction'];
  const goalParts = (entry.goals || '').split(',').map(s => s.trim()).filter(Boolean);
  const knownGoals = goalParts.filter(g => goalOptions.includes(g));
  const otherGoal = goalParts.filter(g => !goalOptions.includes(g)).join(', ');
  setChipValues('goals', knownGoals);
  document.getElementById('goalsOther').value = otherGoal;

  form.elements['people_involved'].value = entry.people_involved || '';
  form.elements['phone_minutes'].value = entry.phone_minutes || 0;

  // Food: split stored string back into chips + other
  const foodOptions = ['Fruits','Nuts','Protein bar','Yogurt','Salad','Smoothie'];
  const foodParts = (entry.food || '').split(',').map(s => s.trim()).filter(Boolean);
  const knownFood = foodParts.filter(f => foodOptions.includes(f));
  const otherFood = foodParts.filter(f => !foodOptions.includes(f)).join(', ');
  setChipValues('food', knownFood);
  document.getElementById('foodOther').value = otherFood;

  // Sports: radio
  const sportsOptions = ['Walking','Running','Gym workout','Yoga','Cycling','Stretching','Rest day'];
  const sportsVal = (entry.sports || '').split(',')[0].trim();
  const sportsOtherVal = (entry.sports || '').split(',').slice(1).join(',').trim();
  if (sportsOptions.includes(sportsVal)) {
    const radio = form.querySelector(`input[name="sports"][value="${sportsVal}"]`);
    if (radio) radio.checked = true;
    document.getElementById('sportsOther').style.display = 'none';
  } else {
    document.getElementById('sportsOtherRadio').checked = true;
    document.getElementById('sportsOther').style.display = 'block';
    document.getElementById('sportsOther').value = entry.sports || '';
  }

  form.elements['has_medicines'].checked = !!entry.has_medicines;
  medicinesTakenRow.style.display = entry.has_medicines ? 'grid' : 'none';
  form.elements['medicines_taken'].checked = !!entry.medicines_taken;
  form.querySelector('button[type="submit"]').textContent = 'Update Entry';
  form.scrollIntoView({ behavior: 'smooth' });
}

function resetForm() {
  editingDate = null;
  dateInput.disabled = false;
  dateInput.value = todayStr();
  form.querySelector('button[type="submit"]').textContent = 'Save Entry';
  medicinesTakenRow.style.display = 'none';
  document.getElementById('sportsOther').style.display = 'none';
  futureDateWarn.style.display = 'none';
  submitBtn.disabled = false;
  submitBtn.style.opacity = '';
  form.reset();
  dateInput.value = todayStr(); // reset() clears it, restore today
}

// ── History ───────────────────────────────────────────────────────────────────
const HISTORY_PAGE_SIZE = 2;
let historyShowAll = false;

function buildHistoryItem(entry) {
  const item = document.createElement('div');
  item.className = 'history-item';
  const medicineHtml = entry.has_medicines
    ? `<div><strong>Medicines:</strong> ${entry.medicines_taken ? 'Taken' : 'Not taken'}</div>`
    : '';
  item.innerHTML = `
    <div class="history-item-header">
      <h3>${entry.date}</h3>
      <div class="history-actions">
        <button class="btn-edit" data-date="${entry.date}">Edit</button>
        <button class="btn-delete" data-date="${entry.date}">Delete</button>
      </div>
    </div>
    <div><strong>Goals:</strong> ${entry.goals || '-'}</div>
    <div><strong>People Involved:</strong> ${entry.people_involved || '-'}</div>
    <div><strong>Phone:</strong> ${entry.phone_minutes || 0} min</div>
    <div><strong>Food:</strong> ${entry.food || '-'}</div>
    <div><strong>Sports:</strong> ${entry.sports || '-'}</div>
    ${medicineHtml}
    <div><strong>Summary:</strong> ${entry.summary || '-'}</div>
  `;
  return item;
}

function renderHistory(entries) {
  const sorted = sortEntries(entries);
  historyList.innerHTML = '';
  if (!sorted.length) {
    historyList.innerHTML = '<p class="placeholder">No history yet.</p>';
    return;
  }
  const visible = historyShowAll ? sorted : sorted.slice(0, HISTORY_PAGE_SIZE);
  visible.forEach(entry => historyList.appendChild(buildHistoryItem(entry)));

  if (sorted.length > HISTORY_PAGE_SIZE) {
    const btn = document.createElement('button');
    btn.className = 'btn-view-more';
    btn.textContent = historyShowAll ? 'Show Less ▲' : `View More (${sorted.length - HISTORY_PAGE_SIZE} more) ▼`;
    btn.addEventListener('click', () => { historyShowAll = !historyShowAll; renderHistory(entries); });
    historyList.appendChild(btn);
  }

  historyList.querySelectorAll('.btn-edit').forEach(btn => {
    btn.addEventListener('click', async () => {
      const res = await fetch('/api/entries');
      const all = await res.json();
      const entry = all.find(e => e.date === btn.dataset.date);
      if (entry) fillFormForEdit(entry);
    });
  });

  historyList.querySelectorAll('.btn-delete').forEach(btn => {
    btn.addEventListener('click', async () => {
      if (!confirm(`Delete entry for ${btn.dataset.date}?`)) return;
      await fetch(`/api/entries/${btn.dataset.date}`, { method: 'DELETE' });
      historyShowAll = false;
      await loadHistory();
    });
  });
}

async function loadHistory() {
  const res = await fetch('/api/entries');
  if (res.status === 401) return;
  renderHistory(await res.json()); // already sorted by backend
}

async function loadLast() {
  const res = await fetch('/api/entries/last');
  if (res.status === 401) return;
  renderEntry(await res.json()); // backend returns most recent by date
}

// ── Form submit ───────────────────────────────────────────────────────────────
form.addEventListener('submit', async (e) => {
  e.preventDefault();

  const selectedDate = dateInput.value;
  if (isFuture(selectedDate)) {
    futureDateWarn.style.display = 'flex';
    return;
  }

  const goals = getCheckedValues('goals');
  const goalsOther = document.getElementById('goalsOther').value.trim();
  const food = getCheckedValues('food');
  const foodOther = document.getElementById('foodOther').value.trim();
  const sportsRadio = form.querySelector('input[name="sports"]:checked');
  const sportsOther = document.getElementById('sportsOther').value.trim();
  const people = form.elements['people_involved'].value.trim();

  if (!goals.length && !goalsOther) { alert('Please select at least one goal or enter a custom goal.'); return; }
  if (!food.length && !foodOther) { alert('Please select at least one food item or enter a custom one.'); return; }
  if (!sportsRadio) { alert('Please select a sports/activity option.'); return; }
  if (!people) { alert('People Involved is required. Write "nil" if none.'); return; }

  const data = {
    date: selectedDate,
    goals,
    goals_other: goalsOther,
    people_involved: people,
    phone_minutes: parseInt(form.elements['phone_minutes'].value || '0', 10),
    food,
    food_other: foodOther,
    sports: sportsRadio.value === 'Other' ? 'Other' : sportsRadio.value,
    sports_other: sportsRadio.value === 'Other' ? sportsOther : '',
    has_medicines: form.elements['has_medicines'].checked,
    medicines_taken: form.elements['medicines_taken'].checked,
  };

  const url = editingDate ? `/api/entries/${editingDate}` : '/api/entries';
  const res = await fetch(url, {
    method: editingDate ? 'PUT' : 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  });
  const saved = await res.json();
  if (!res.ok) { alert(saved.error || 'Failed to save entry.'); return; }
  renderEntry(saved);
  resetForm();
  await loadHistory(); // re-fetches sorted list from backend
});

loadLastBtn.addEventListener('click', loadLast);

// ── Boot ──────────────────────────────────────────────────────────────────────
initAuth().then(ok => { if (ok) { loadLast(); loadHistory(); } });
