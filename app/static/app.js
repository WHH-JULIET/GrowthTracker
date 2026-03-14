const form = document.getElementById('entryForm');
const summaryContent = document.getElementById('summaryContent');
const historyList = document.getElementById('historyList');
const loadLastBtn = document.getElementById('loadLast');

function renderEntry(entry) {
  if (!entry || !entry.date) {
    summaryContent.innerHTML = '<p class="placeholder">No entries yet.</p>';
    return;
  }

  summaryContent.innerHTML = `
    <div><strong>Date:</strong> ${entry.date}</div>
    <div><strong>Goals:</strong> ${entry.goals || '-'}</div>
    <div>
      <span class="badge work">Work</span>
      <div>${entry.communication_work || '-'}</div>
    </div>
    <div>
      <span class="badge timepass">Timepass</span>
      <div>${entry.communication_timepass || '-'}</div>
    </div>
    <div><strong>Phone time:</strong> ${entry.phone_minutes || 0} min</div>
    <div><strong>Notifications:</strong> ${entry.notifications || 0}</div>
    <div><strong>Food:</strong> ${entry.food || '-'}</div>
    <div><strong>Sports:</strong> ${entry.sports || '-'}</div>
    <div><strong>Medicines:</strong> ${entry.medicines_taken ? 'Taken' : 'Not taken'}</div>
    <div><strong>AI Summary:</strong> ${entry.summary || '-'}</div>
  `;
}

function renderHistory(entries) {
  historyList.innerHTML = '';
  if (!entries.length) {
    historyList.innerHTML = '<p class="placeholder">No history yet.</p>';
    return;
  }

  entries.slice().reverse().forEach(entry => {
    const item = document.createElement('div');
    item.className = 'history-item';
    item.innerHTML = `
      <h3>${entry.date}</h3>
      <div><strong>Goals:</strong> ${entry.goals || '-'}</div>
      <div><strong>Work:</strong> ${entry.communication_work || '-'}</div>
      <div><strong>Timepass:</strong> ${entry.communication_timepass || '-'}</div>
      <div><strong>Phone:</strong> ${entry.phone_minutes || 0} min, ${entry.notifications || 0} notifications</div>
      <div><strong>Food:</strong> ${entry.food || '-'}</div>
      <div><strong>Sports:</strong> ${entry.sports || '-'}</div>
      <div><strong>Medicines:</strong> ${entry.medicines_taken ? 'Taken' : 'Not taken'}</div>
      <div><strong>Summary:</strong> ${entry.summary || '-'}</div>
    `;
    historyList.appendChild(item);
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
  data.phone_minutes = parseInt(data.phone_minutes || '0', 10);
  data.notifications = parseInt(data.notifications || '0', 10);
  data.medicines_taken = form.elements['medicines_taken'].checked;

  const res = await fetch('/api/entries', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  });
  const entry = await res.json();
  renderEntry(entry);
  await loadHistory();
  form.reset();
});

loadLastBtn.addEventListener('click', async () => {
  await loadLast();
});

loadLast();
loadHistory();
