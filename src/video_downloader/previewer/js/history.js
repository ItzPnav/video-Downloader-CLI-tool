/* ============================================================
   history.js — localStorage-based recent videos history
   ============================================================ */

const HISTORY_KEY = 'video_extractor_preview_history';
const HISTORY_MAX = 10;

function loadHistory() {
  try {
    return JSON.parse(localStorage.getItem(HISTORY_KEY) || '[]');
  } catch {
    return [];
  }
}

function saveHistory(history) {
  try {
    localStorage.setItem(HISTORY_KEY, JSON.stringify(history));
  } catch (e) {
    console.warn('Could not save history:', e);
  }
}

function addToHistory(url) {
  const src = detectSource(url);
  let history = loadHistory().filter(item => item.url !== url);
  history.unshift({ url, source: src, ts: Date.now() });
  if (history.length > HISTORY_MAX) history = history.slice(0, HISTORY_MAX);
  saveHistory(history);
  renderHistory();
}

function removeFromHistory(url) {
  const history = loadHistory().filter(item => item.url !== url);
  saveHistory(history);
  renderHistory();
}

function clearHistory() {
  saveHistory([]);
  renderHistory();
}

function renderHistory() {
  const section = document.getElementById('historySection');
  const list    = document.getElementById('historyList');
  const history = loadHistory();

  if (history.length === 0) {
    section.classList.remove('visible');
    return;
  }

  section.classList.add('visible');
  list.innerHTML = '';

  history.forEach(item => {
    const li = document.createElement('li');
    li.className = 'history-item';
    li.title = item.url;

    li.innerHTML = `
      <span class="history-badge">${sourceLabel(item.source)}</span>
      <span class="history-url">${truncateUrl(item.url)}</span>
      <button class="history-remove" title="Remove" onclick="event.stopPropagation(); removeFromHistory('${escapeAttr(item.url)}')">✕</button>
    `;

    li.addEventListener('click', () => {
      document.getElementById('videoInput').value = item.url;
      loadVideo();
    });

    list.appendChild(li);
  });
}

function escapeAttr(str) {
  return str.replace(/'/g, "\\'").replace(/"/g, '&quot;');
}

document.addEventListener('DOMContentLoaded', renderHistory);
