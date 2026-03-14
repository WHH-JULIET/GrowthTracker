const today = new Date().toISOString().split('T')[0];
document.getElementById('dateInput').min = today;

const form = document.getElementById('entryForm');
const summaryContent = document.getElementById('summaryContent');
const historyList = document.getElementById('historyList');
const loadLastBtn = document.getElementById('loadLast');
let editingDate = null;

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
  summaryContent.innerHTML = `
    <div><strong>Date:</strong> ${entry.date}</div>
    <div><strong>Goals:</strong> ${entry.goals || '-'}</div>
    <div><strong>People Involved:</strong> ${entry.people_involved || '-'}</div>
    <div><strong>Phone time:</strong> ${entry.phone_minutes || 0} min</div>
    <div><strong>Food:</strong> ${entry.food || '-'}</div>
    <div><strong>Sports:</strong> ${entry.sports || '-'}</div>
    <div><strong>Medicines:</strong> ${entry.medicines_taken ? 'Taken' : 'Not taken'}</div>
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
  form.elements['medicines_taken'].checked = !!entry.medicines_taken;
  form.querySelector('button[type="submit"]').textContent = 'Update Entry';
  form.scrollIntoView({ behavior: 'smooth' });
}

function resetForm() {
  editingDate = null;
  document.getElementById('dateInput').disabled = false;
  form.querySelector('button[type="submit"]').textContent = 'Save Entry';
  form.reset();
}

const HISTORY_PAGE_SIZE = 2;
let historyShowAll = false;

function buildHistoryItem(entry) {
  const item = document.createElement('div');
  item.className = 'history-item';
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
    <div><strong>Medicines:</strong> ${entry.medicines_taken ? 'Taken' : 'Not taken'}</div>
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
  const entries = await res.json();
  renderHistory(entries);
}

async function loadLast() {
  const res = await fetch('/api/entries/last');
  const entry = await res.json();
  renderEntry(entry);
}

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
  data.medicines_taken = form.elements['medicines_taken'].checked;

  if (editingDate) {
    const res = await fetch(`/api/entries/${editingDate}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    const entry = await res.json();
    renderEntry(entry);
  } else {
    const res = await fetch('/api/entries', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    const entry = await res.json();
    renderEntry(entry);
  }

  resetForm();
  await loadHistory();
});

loadLastBtn.addEventListener('click', async () => {
  await loadLast();
});

loadLast();
loadHistory();
