const today = new Date().toISOString().split('T')[0];

const form = document.getElementById('entryForm');
const summaryContent = document.getElementById('summaryContent');
const historyList = document.getElementById('historyList');
const loadLastBtn = document.getElementById('loadLast');
const authBar = document.getElementById('authBar');
const loginWall = document.getElementById('loginWall');
const mainContent = document.getElementById('mainContent');
const hasMedicinesCheck = document.getElementById('hasMedicinesCheck');
const medicinesTakenRow = document.getElementById('medicinesTakenRow');

let editingDate = null;

// ── Auth ──────────────────────────────────────────────────────────────────────
async function initAuth() {
  const res = await fetch('/auth/me');
  const data = await res.json();

  if (!data.authenticated) {
    loginWall.style.display = 'flex';
    mainContent.style.display = 'none';
    authBar.innerHTML = `<a href="/auth/login" class="btn-google-small">Sign in</a>`;
    return false;
  }

  loginWall.style.display = 'none';
  mainContent.style.display = 'grid';
  authBar.innerHTML = `
    <div class="user-info">
      ${data.picture ? `<img src="${data.picture}" class="avatar" alt="${data.name}" />` : ''}
      <span>${data.name}</span>
      <a href="/auth/logout" class="btn-logout">Sign out</a>
    </div>
  `;
  return true;
}

// ── Medicines toggle ──────────────────────────────────────────────────────────
hasMedicinesCheck.addEventListener('change', () => {
  medicinesTakenRow.style.display = hasMedicinesCheck.checked ? 'grid' : 'none';
  if (!hasMedicinesCheck.checked) {
    form.elements['medicines_taken'].checked = false;
  }
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
  let medicineHtml = '';
  if (entry.has_medicines) {
    medicineHtml = `<div><strong>Medicines:</strong> ${entry.medicines_taken ? 'Taken' : 'Not taken'}</div>`;
  }
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

function fillFormForEdit(entry) {
  editingDate = entry.date;
  document.getElementById('dateInput').value = entry.date;
  document.getElementById('dateInput').disabled = true;
  form.elements['goals'].value = entry.goals || '';
  form.elements['people_involved'].value = entry.people_involved || '';
  form.elements['phone_minutes'].value = entry.phone_minutes || 0;
  form.elements['food'].value = entry.food || '';
  form.elements['sports'].value = entry.sports || '';
  form.elements['has_medicines'].checked = !!entry.has_medicines;
  medicinesTakenRow.style.display = entry.has_medicines ? 'grid' : 'none';
  form.elements['medicines_taken'].checked = !!entry.medicines_taken;
  form.querySelector('button[type="submit"]').textContent = 'Update Entry';
  form.scrollIntoView({ behavior: 'smooth' });
}

function resetForm() {
  editingDate = null;
  document.getElementById('dateInput').disabled = false;
  form.querySelector('button[type="submit"]').textContent = 'Save Entry';
  medicinesTakenRow.style.display = 'none';
  form.reset();
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
  historyList.innerHTML = '';
  if (!entries.length) {
    historyList.innerHTML = '<p class="placeholder">No history yet.</p>';
    return;
  }

  const reversed = entries.slice().reverse();
  const visible = historyShowAll ? reversed : reversed.slice(0, HISTORY_PAGE_SIZE);
  visible.forEach(entry => historyList.appendChild(buildHistoryItem(entry)));

  if (reversed.length > HISTORY_PAGE_SIZE) {
    const btn = document.createElement('button');
    btn.className = 'btn-view-more';
    btn.textContent = historyShowAll ? 'Show Less ▲' : `View More (${reversed.length - HISTORY_PAGE_SIZE} more) ▼`;
    btn.addEventListener('click', () => {
      historyShowAll = !historyShowAll;
      renderHistory(entries);
    });
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
  const entries = await res.json();
  renderHistory(entries);
}

async function loadLast() {
  const res = await fetch('/api/entries/last');
  if (res.status === 401) return;
  const entry = await res.json();
  renderEntry(entry);
}

// ── Form submit ───────────────────────────────────────────────────────────────
form.addEventListener('submit', async (e) => {
  e.preventDefault();
  const data = Object.fromEntries(new FormData(form).entries());
  const textFields = ['goals', 'people_involved', 'food', 'sports'];
  const empty = textFields.find(f => !data[f] || !data[f].trim());
  if (empty) {
    alert(`"${empty.replace('_', ' ')}" is required. Write "nil" if nothing to fill.`);
    return;
  }
  data.phone_minutes = parseInt(data.phone_minutes || '0', 10);
  data.has_medicines = form.elements['has_medicines'].checked;
  data.medicines_taken = form.elements['medicines_taken'].checked;

  const url = editingDate ? `/api/entries/${editingDate}` : '/api/entries';
  const method = editingDate ? 'PUT' : 'POST';
  const res = await fetch(url, {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  });
  const entry = await res.json();
  renderEntry(entry);
  resetForm();
  await loadHistory();
});

loadLastBtn.addEventListener('click', loadLast);

// ── Boot ──────────────────────────────────────────────────────────────────────
initAuth().then(authenticated => {
  if (authenticated) {
    loadLast();
    loadHistory();
  }
});
